"""Batch 28 gaps the contract leaves: check order, canonical names, units, crops, re-photo, runs line."""

import hashlib
import importlib.util
import json
from decimal import Decimal
from pathlib import Path

from anamnesis.agent import run_intake
from anamnesis.core.catalogue import load_catalogue
from anamnesis.providers import ProviderTrace
from anamnesis.providers.meta import MetaClient
from anamnesis.providers.openweight import PRESETS, OpenWeightClient
from anamnesis.providers.spend import SpendGuard
from anamnesis.review import add_photo, new_review, request_photo
from anamnesis.schema import AudioTurn
from anamnesis.schema.report import AgentAction
from tests.contract.test_b19_brief import (
    AUDIO,
    PHOTO,
    RC,
    Extractor,
    Reader,
    Segmenter,
    Transcriber,
    claim,
    mg,
    png,
    reading,
    region_on,
    st,
)

ROOT = Path(__file__).resolve().parents[2]
CAT = load_catalogue()
TURNS = [AudioTurn(turn_id="turn-c1", start_ms=0, end_ms=3000, transcript="I take Concor 5 mg once a day.")]
CONCOR = claim("c1", "Concor", intake=mg("bisoprolol", 5), per_day="1")
PARTIAL = reading(label="Con", readability="partial")
CONCOR_5 = reading(label="Concor 5 mg\nBisoprolol fumarate", strength=st(mg("bisoprolol", 5)))


class SecondReader(Reader):
    def read(self, image, region, *, mime, cropped=False):
        self.seen.setdefault(region.region_id, image)
        answer = self.script[region.region_id].pop(0)
        return answer.model_copy(update={"region_id": region.region_id}), ProviderTrace(
            call_id="second", model_id="fixture:second", latency_ms=1, input_tokens=0,
            output_tokens=0, cost_usd=Decimal("0.002"))


class ElsewhereReader(SecondReader):
    def read(self, image, region, *, mime, cropped=False):
        found, trace = super().read(image, region, mime=mime, cropped=cropped)
        return found.model_copy(update={"region_id": "elsewhere-0"}), trace


def run(reads, second=None, regions=(RC,), claims=(CONCOR,), **kw):
    by_sha = {RC.image_sha256: list(regions)}
    report = run_intake(AUDIO[0], [(PHOTO, "image/png")], transcriber=Transcriber(TURNS),
                        extractor=Extractor(list(claims)), segmenter=Segmenter(by_sha),
                        reader=Reader(reads), catalogue=CAT, second_reader=second, **kw)
    return report


def steps_for(report, region):
    return [(step.action, step.outcome) for step in report.steps if step.target == region.region_id]


def test_a_second_reading_for_another_region_is_refused_before_the_readable_check():
    second = ElsewhereReader({RC.region_id: [reading(label="Co", readability="unreadable")]})
    report = run({RC.region_id: [PARTIAL, PARTIAL]}, second)
    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "error: reading for another region")
    assert report.observations[0].readability.value == "partial"


def test_a_partial_second_with_other_ingredients_is_not_a_conflict():
    first = reading(label="Concor", readability="partial").model_copy(update={"inn": "bisoprolol"})
    other = reading(label="Panadol 500 mg", strength=st(mg("paracetamol", 500)), readability="partial")
    report = run({RC.region_id: [first, first]}, SecondReader({RC.region_id: [other]}))
    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "partial")
    assert report.observations[0].readability.value == "partial"
    assert report.observations[0].inn == "bisoprolol"


def test_a_curated_alias_agrees_through_the_canonical_inn():
    first = reading(label="Pan", readability="partial").model_copy(update={"inn": "acetaminophen"})
    panadol = reading(label="Panadol 500 mg\nParacetamol", strength=st(mg("paracetamol", 500)))
    report = run({RC.region_id: [first, first]}, SecondReader({RC.region_id: [panadol]}))
    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "readable")
    assert report.observations[0].readability.value == "readable"


def test_a_unit_difference_keeps_the_first():
    first = reading(label="Concor 5", strength=st(mg("bisoprolol", 5)), readability="partial")
    other_unit = reading(label="Concor 5 mcg", strength=st(mg("bisoprolol", 5, "mcg")))
    report = run({RC.region_id: [first, first]}, SecondReader({RC.region_id: [other_unit]}))
    assert report.observations[0].readability.value == "partial"
    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "conflict: kept the first reading")


def test_an_unknown_release_can_be_completed_by_the_second_reading():
    first = reading(label="Concor 5", strength=st(mg("bisoprolol", 5)), readability="partial")
    immediate = reading(label="Concor 5 mg", strength=st(mg("bisoprolol", 5), release="immediate"))
    report = run({RC.region_id: [first, first]}, SecondReader({RC.region_id: [immediate]}))
    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "readable")
    assert report.observations[0].readability.value == "readable"


def test_two_known_releases_must_match():
    first = reading(label="Concor 5", strength=st(mg("bisoprolol", 5), release="immediate"),
                    readability="partial")
    modified = reading(label="Concor 5 mg", strength=st(mg("bisoprolol", 5), release="modified"))
    report = run({RC.region_id: [first, first]}, SecondReader({RC.region_id: [modified]}))
    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "conflict: kept the first reading")
    assert report.observations[0].readability.value == "partial"


def test_a_failed_second_crop_keeps_the_first(monkeypatch):
    import anamnesis.agent.loop as loop

    real_cut = loop.crop_region
    calls = []

    def third_cut_fails(image, region, margin=0.10):
        calls.append(region.region_id)
        if len(calls) == 3:
            raise ValueError("crop failed")
        return real_cut(image, region, margin)

    monkeypatch.setattr(loop, "crop_region", third_cut_fails)
    report = run({RC.region_id: [PARTIAL, PARTIAL]}, SecondReader({RC.region_id: [CONCOR_5]}))
    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "error: crop failed")
    assert report.observations[0].readability.value == "partial"


def test_a_re_photo_conflict_keeps_the_first_but_still_supersedes():
    report = run({RC.region_id: [PARTIAL, PARTIAL]})
    review = request_photo(new_review(report), report, "o0")
    retake = png(600, 300, colour=(190, 190, 190))
    region = region_on(retake, (10, 20, 139, 279), 0, 0.95)
    first = reading(label="Concor 5", strength=st(mg("bisoprolol", 5)), readability="partial")
    panadol = reading(label="Panadol 500 mg\nParacetamol", strength=st(mg("paracetamol", 500)))
    updated, _ = add_photo(report, review, "r1", (retake, "image/png"), [(PHOTO, "image/png")], AUDIO,
                           segmenter=Segmenter({hashlib.sha256(retake).hexdigest(): [region]}),
                           reader=Reader({region.region_id: [first, first]}), catalogue=CAT,
                           second_reader=SecondReader({region.region_id: [panadol]}))
    assert updated.superseded == ["o0"]
    assert updated.observations[-1].readability.value == "partial"
    assert [(s.action, s.outcome) for s in updated.steps if s.target == region.region_id][-1] == (
        AgentAction.SECOND_READ, "conflict: kept the first reading")


def _intake_live():
    spec = importlib.util.spec_from_file_location("intake_live_b28_extra", ROOT / "scripts/intake_live.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runs_lines_record_the_second_reader(monkeypatch, tmp_path):
    il = _intake_live()
    real = run({RC.region_id: [CONCOR_5]})
    monkeypatch.setattr(il, "run_intake", lambda *args, **kwargs: real)
    monkeypatch.setattr(il, "render_brief", lambda *args, **kwargs: "<p>brief</p>")
    reports, briefs = tmp_path / "reports", tmp_path / "briefs"
    reports.mkdir()
    briefs.mkdir()

    def line_for(**clients):
        run_ = il.Run(SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal(1)), MetaClient("k"),
                      load_catalogue(), Decimal("0.25"), 3, reports, briefs, **clients)
        il.intake(run_, "x", b"audio", [(b"img", "image/png")], "en")
        return json.loads((reports / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])

    assert line_for()["second_reader"] is None
    fireworks = OpenWeightClient("k", base_url=PRESETS["fireworks"]["base_url"], provider="fireworks")
    assert line_for(second_client=fireworks)["second_reader"] == "fireworks"
