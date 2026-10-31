"""Batch 28 contract: a second label reader for a pack the first reader still can't read after its zoom (SPEC §4
step 5b, §8 and "The second reader (batch 28)"). Without one, nothing changes. Written by the CEO; Muse must not
edit it."""

import hashlib
import importlib.util
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from anamnesis.agent import crop_region, run_intake
from anamnesis.core.catalogue import load_catalogue
from anamnesis.providers import ProviderError, ProviderTrace, SpendGuard
from anamnesis.providers.meta import MetaClient, MetaLabelReader
from anamnesis.providers.openweight import PRESETS, OpenWeightClient, OpenWeightLabelReader
from anamnesis.review import add_photo, new_review, request_photo, requestable
from anamnesis.schema import AudioTurn
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.report import AgentAction
from tests.contract.test_b19_brief import (
    AUDIO,
    PHOTO,
    RB,
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
    """The second reader's fake: a script per region, the bytes it saw, and its own model id."""

    def read(self, image, region, *, mime, cropped=False):
        self.seen.setdefault(region.region_id, image)
        self.cropped = [*getattr(self, "cropped", []), cropped]
        answer = self.script[region.region_id].pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer.model_copy(update={"region_id": region.region_id}), ProviderTrace(
            call_id="second", model_id="fixture:second", latency_ms=1, input_tokens=0, output_tokens=0,
            cost_usd=Decimal("0.002"))


class ElsewhereReader(SecondReader):
    def read(self, image, region, *, mime, cropped=False):
        found, trace = super().read(image, region, mime=mime, cropped=cropped)
        return found.model_copy(update={"region_id": "elsewhere-0"}), trace


def run(reads, second=None, regions=(RC,), claims=(CONCOR,), **kw):
    first = Reader(reads)
    report = run_intake(AUDIO[0], [(PHOTO, "image/png")], transcriber=Transcriber(TURNS),
                        extractor=Extractor(list(claims)), segmenter=Segmenter({RC.image_sha256: list(regions)}),
                        reader=first, catalogue=CAT, second_reader=second, **kw)
    return report, first


def steps_for(report, region):
    return [(step.action, step.outcome) for step in report.steps if step.target == region.region_id]


# --- the step --------------------------------------------------------------------------------------------------------

def test_a_pack_still_unread_after_the_zoom_gets_one_second_read_that_replaces_it():
    second = SecondReader({RC.region_id: [CONCOR_5]})
    report, _ = run({RC.region_id: [PARTIAL, PARTIAL]}, second)
    assert steps_for(report, RC) == [(AgentAction.READ, "partial"), (AgentAction.ZOOM_READ, "partial"),
                                     (AgentAction.SECOND_READ, "readable")]
    (observation,) = report.observations
    assert (observation.readability.value, observation.label_text) == ("readable", CONCOR_5.label_text)
    assert observation.visual_evidence == [RC.region_id]
    assert [finding.type for finding in report.findings] == [D.MATCH]
    second_step = [step for step in report.steps if step.action is AgentAction.SECOND_READ][0]
    assert second_step.model_id == "fixture:second" and second_step.cost_usd == Decimal("0.002")


def test_the_second_read_sees_the_first_reads_pixels():
    second = SecondReader({RC.region_id: [CONCOR_5]})
    _, first = run({RC.region_id: [PARTIAL, PARTIAL]}, second)
    assert second.seen[RC.region_id] == first.seen[RC.region_id] == crop_region(PHOTO, RC)
    assert second.cropped == [True]


def test_an_unreadable_first_reading_gets_a_second_read_too():
    unreadable = reading(readability="unreadable")
    report, _ = run({RC.region_id: [unreadable, unreadable]}, SecondReader({RC.region_id: [CONCOR_5]}))
    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "readable")
    assert report.observations[0].readability.value == "readable"


def test_a_pack_too_big_to_zoom_gets_its_second_read_in_the_zooms_place():
    big = png(2400, 400)
    region = region_on(big, (100, 20, 2300, 380), 0, 0.95)
    first = Reader({region.region_id: [PARTIAL]})
    report = run_intake(AUDIO[0], [(big, "image/png")], transcriber=Transcriber(TURNS),
                        extractor=Extractor([CONCOR]), segmenter=Segmenter({region.image_sha256: [region]}),
                        reader=first, catalogue=CAT, second_reader=SecondReader({region.region_id: [CONCOR_5]}))
    assert steps_for(report, region) == [(AgentAction.READ, "partial"), (AgentAction.SECOND_READ, "readable")]


@pytest.mark.parametrize("reads", [[CONCOR_5], [PARTIAL, CONCOR_5]])
def test_a_pack_the_first_reader_reads_gets_no_second_read(reads):
    second = SecondReader({RC.region_id: []})  # any call would fail: the script is empty
    report, _ = run({RC.region_id: list(reads)}, second)
    assert AgentAction.SECOND_READ not in {step.action for step in report.steps}
    assert [finding.type for finding in report.findings] == [D.MATCH]


def test_a_second_reading_that_still_abstains_keeps_the_first_and_the_re_photo():
    second = SecondReader({RC.region_id: [reading(label="Co", readability="unreadable")]})
    report, _ = run({RC.region_id: [PARTIAL, PARTIAL]}, second)
    assert report.observations[0].readability.value == "partial"
    assert D.UNREADABLE_SOURCE in {finding.type for finding in report.findings}
    assert ("unreadable", "o0") in [(kind.value, target) for kind, target in requestable(report)]


def test_a_second_reading_with_other_ingredients_keeps_the_first():
    first = reading(label="Concor", readability="partial").model_copy(update={"inn": "bisoprolol"})
    panadol = reading(label="Panadol 500 mg\nParacetamol", strength=st(mg("paracetamol", 500)))
    report, _ = run({RC.region_id: [first, first]}, SecondReader({RC.region_id: [panadol]}))
    assert report.observations[0].readability.value == "partial"
    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "conflict: kept the first reading")


def test_a_second_reading_with_another_strength_keeps_the_first():
    first = reading(label="Concor 5", strength=st(mg("bisoprolol", 5)), readability="partial")
    ten = reading(label="Concor 10 mg\nBisoprolol fumarate", strength=st(mg("bisoprolol", 10)))
    report, _ = run({RC.region_id: [first, first]}, SecondReader({RC.region_id: [ten]}))
    assert report.observations[0].readability.value == "partial"
    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "conflict: kept the first reading")


def test_a_second_reading_for_another_region_is_refused():
    report, _ = run({RC.region_id: [PARTIAL, PARTIAL]}, ElsewhereReader({RC.region_id: [CONCOR_5]}))
    assert report.observations[0].readability.value == "partial"
    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "error: reading for another region")


def test_a_second_reader_error_keeps_the_first_and_is_one_call():
    second = SecondReader({RC.region_id: [ProviderError("fireworks", "timeout")]})
    report, _ = run({RC.region_id: [PARTIAL, PARTIAL]}, second)
    assert report.observations[0].readability.value == "partial"
    action, outcome = steps_for(report, RC)[-1]
    assert action is AgentAction.SECOND_READ and outcome.startswith("error: fireworks")
    assert report.calls == 2 + 1 + 3  # voice, claims, one segment, and three reads of one region


def test_steps_still_add_up_to_the_spend():
    report, _ = run({RC.region_id: [PARTIAL, PARTIAL]}, SecondReader({RC.region_id: [CONCOR_5]}))
    assert sum(step.cost_usd for step in report.steps) == report.spend_usd


def test_each_region_is_zoomed_then_second_read_before_the_next():
    reads = {RC.region_id: [PARTIAL, PARTIAL], RB.region_id: [PARTIAL, PARTIAL]}
    second = SecondReader({RC.region_id: [CONCOR_5], RB.region_id: [PARTIAL]})
    report, _ = run(reads, second, regions=(RC, RB))
    late = [(step.action, step.target) for step in report.steps
            if step.action in (AgentAction.ZOOM_READ, AgentAction.SECOND_READ)]
    assert late == [(AgentAction.ZOOM_READ, RC.region_id), (AgentAction.SECOND_READ, RC.region_id),
                    (AgentAction.ZOOM_READ, RB.region_id), (AgentAction.SECOND_READ, RB.region_id)]


# --- without a second reader, nothing changes -----------------------------------------------------------------

def test_without_a_second_reader_the_report_is_unchanged():
    reads = {RC.region_id: [PARTIAL, PARTIAL]}
    without, _ = run(dict(reads))
    first = Reader({key: list(value) for key, value in reads.items()})
    plain = run_intake(AUDIO[0], [(PHOTO, "image/png")], transcriber=Transcriber(TURNS),
                       extractor=Extractor([CONCOR]), segmenter=Segmenter({RC.image_sha256: [RC]}),
                       reader=first, catalogue=CAT)
    assert without.model_dump() == plain.model_dump()
    assert AgentAction.SECOND_READ not in {step.action for step in plain.steps}


# --- the budget -----------------------------------------------------------------------------------------------------

def test_the_default_budget_has_room_for_a_second_read_of_every_region():
    regions = [region_on(PHOTO, (10 + 150 * i, 20, 139 + 150 * i, 279), i, 0.9 - i / 10) for i in range(3)]
    reads = {region.region_id: [PARTIAL, PARTIAL] for region in regions}
    second = SecondReader({region.region_id: [PARTIAL] for region in regions})
    report, _ = run(reads, second, regions=regions)
    assert AgentAction.BUDGET_EXHAUSTED not in {step.action for step in report.steps}
    assert sum(step.action is AgentAction.SECOND_READ for step in report.steps) == 3


def test_an_explicit_budget_still_stops_the_loop():
    report, _ = run({RC.region_id: [PARTIAL, PARTIAL]}, SecondReader({RC.region_id: [CONCOR_5]}),
                    max_provider_calls=5)
    assert report.steps[-1].action is AgentAction.BUDGET_EXHAUSTED
    assert AgentAction.SECOND_READ not in {step.action for step in report.steps}


# --- the clinician's re-photo reads the same way ------------------------------------------------------------------

def test_a_re_photo_gets_the_same_second_read():
    report, _ = run({RC.region_id: [PARTIAL, PARTIAL]})
    review = request_photo(new_review(report), report, "o0")
    retake = png(600, 300, colour=(190, 190, 190))
    region = region_on(retake, (10, 20, 139, 279), 0, 0.95)
    updated, _ = add_photo(report, review, "r1", (retake, "image/png"), [(PHOTO, "image/png")], AUDIO,
                           segmenter=Segmenter({hashlib.sha256(retake).hexdigest(): [region]}),
                           reader=Reader({region.region_id: [PARTIAL, PARTIAL]}), catalogue=CAT,
                           second_reader=SecondReader({region.region_id: [CONCOR_5]}))
    assert updated.superseded == ["o0"]
    assert updated.observations[-1].readability.value == "readable"
    assert [finding.type for finding in updated.findings] == [D.MATCH]


# --- the live script ---------------------------------------------------------------------------------------------

def _intake_live():
    spec = importlib.util.spec_from_file_location("intake_live_b28", ROOT / "scripts/intake_live.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Built(Exception):
    pass


def _providers(monkeypatch, tmp_path, **clients):
    il = _intake_live()

    def capture(*_args, **kwargs):
        raise _Built(kwargs)

    monkeypatch.setattr(il, "run_intake", capture)
    run_ = il.Run(SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal(1)), MetaClient("k"), load_catalogue(),
                  Decimal("0.25"), 3, tmp_path, tmp_path, **clients)
    with pytest.raises(_Built) as built:
        il.intake(run_, "x", b"", [(b"", "image/png")], "en")
    return built.value.args[0]


def test_without_the_flag_there_is_no_second_reader(monkeypatch, tmp_path):
    kwargs = _providers(monkeypatch, tmp_path)
    assert kwargs.get("second_reader") is None and isinstance(kwargs["reader"], MetaLabelReader)
    assert kwargs["max_provider_calls"] == 2 + (3 + 2 * 3) * 1


def test_the_second_reader_is_spark_open_on_fireworks_at_low_effort(monkeypatch, tmp_path):
    client = OpenWeightClient("k", base_url=PRESETS["fireworks"]["base_url"], provider="fireworks")
    kwargs = _providers(monkeypatch, tmp_path, second_client=client)
    second = kwargs["second_reader"]
    assert isinstance(kwargs["reader"], MetaLabelReader) and isinstance(second, OpenWeightLabelReader)
    assert (second.model, second.price_key, second.json_mode, second.reasoning_effort) == (
        PRESETS["fireworks"]["model"], "muse-spark-open@fireworks", False, "low")
    assert second.guard is kwargs["reader"].guard  # one per-intake dollar cap bounds both readers
    assert kwargs["max_provider_calls"] == 2 + (3 + 3 * 3) * 1


def _refused(monkeypatch, argv):
    il = _intake_live()

    def no_call(*_args, **_kwargs):
        raise AssertionError("a key was read or a client built before the guard")

    monkeypatch.setattr(il, "keychain", no_call)
    monkeypatch.setattr(il, "MetaClient", no_call)
    monkeypatch.setattr(il, "OpenWeightClient", no_call)
    monkeypatch.setattr(sys, "argv", ["intake_live.py", *argv])
    with pytest.raises(SystemExit) as stopped:
        il.main()
    return str(stopped.value.code)


VOICE = str(ROOT / "evidence/raw/media/public/voice/U1.wav")
COMMONS = str(ROOT / "evidence/raw/media/public/commons/concor_nanolek_02.jpg")


def test_the_second_reader_needs_a_staged_case(monkeypatch):
    assert "--case" in _refused(monkeypatch, ["--second-reader", "fireworks"])


@pytest.mark.parametrize("reader", ["fireworks", "baseten"])
def test_the_second_reader_needs_spark_as_the_first(monkeypatch, reader):
    message = _refused(monkeypatch, ["--case", "U1", "--voice", VOICE, "--photo", COMMONS, "--reader", reader,
                                     "--second-reader", "fireworks"])
    assert "--reader spark" in message


@pytest.mark.parametrize("photo", ["/tmp/p1.jpg", str(ROOT / "evidence/raw/media/real/p1.jpg"),
                                   str(ROOT / "evidence/raw/media/public/commons/../../real/p1.jpg")])
def test_the_second_reader_refuses_any_photo_but_the_public_ones(monkeypatch, photo):
    message = _refused(monkeypatch, ["--case", "U1", "--voice", VOICE, "--second-reader", "fireworks",
                                     "--photo", COMMONS, "--photo", photo])
    assert "may go to Fireworks" in message
