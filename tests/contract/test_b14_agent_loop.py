"""Batch 14 contract: the bounded agent loop, crop-zoom with source provenance, session caps, the report bundle.

Written by the reviewer; do not edit. SPEC §4. Findings covered: M2 F-06 (crop-zoom never re-runs SAM, keeps the
source region id and hash), F-07 (session caps, no outer retry, Arabic regression words), F-09 (one report
artifact), M1 #10 (referential checks), QM3 #2-#4.
"""

import hashlib
import io
import json
from decimal import Decimal

import httpx
import pytest
from PIL import Image
from pydantic import ValidationError

from anamnesis.agent import AgentAction, crop_region, run_intake
from anamnesis.core.catalogue import Catalogue, CatalogueEntry, load_catalogue
from anamnesis.core.guardrails import AdviceLeak, assert_no_advice
from anamnesis.core.reconcile import reconcile_pair
from anamnesis.providers import ProviderTrace, SpendCapExceeded, SpendGuard
from anamnesis.providers.meta import MetaClient, MetaLabelReader
from anamnesis.providers.spark import LabelReading
from anamnesis.providers.spend import SessionCapExceeded, SessionGuard
from anamnesis.schema import (
    AudioTurn,
    ImageRegion,
    IngredientAmount,
    PackObservation,
    PatientClaim,
    Release,
    Strength,
)
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.report import ReconciliationReport


def png(w=200, h=100):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (200, 200, 200)).save(buf, format="PNG")
    return buf.getvalue()


IMAGE = png()
SHA = hashlib.sha256(IMAGE).hexdigest()


def region(obj, x1, y1, x2, y2, c=0.9):
    return ImageRegion(region_id=f"{SHA[:12]}-{obj}", image_sha256=SHA, object_id=obj, x1=x1, y1=y1, x2=x2, y2=y2,
                       frame_w=200, frame_h=100, confidence=c)


def trace(cid, cost="0.01"):
    return ProviderTrace(call_id=cid, model_id="fixture:test", latency_ms=1, input_tokens=0, output_tokens=0,
                         cost_usd=Decimal(cost))


def mg(inn, a):
    return IngredientAmount(inn=inn, amount=Decimal(str(a)), unit="mg")


def st(*parts, release="unknown"):
    return Strength(ingredients=list(parts), per="tablet", release=release)


# --- fakes with the live adapters' interfaces --------------------------------------------------------

class Transcriber:
    def __init__(self):
        self.calls = 0

    def transcribe(self, wav, *, language_bias=None, keywords=None, lang_hint=None):
        self.calls += 1
        return [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=5000, transcript="I take Concor five once a day")], \
            trace("voice-1", "0.0003")


class Extractor:
    def extract(self, turns):
        return [PatientClaim(claim_id="c1", name_text="Concor", intake_amount=mg("bisoprolol", 5), status="active",
                             audio_evidence=["turn-0"])], trace("claims-1")


class Segmenter:
    def __init__(self, by_concept):
        self.by_concept, self.calls = by_concept, []

    def segment(self, image, concept, *, mime):
        self.calls.append((hashlib.sha256(image).hexdigest(), concept))
        return list(self.by_concept.get(concept, [])), trace(f"sam-{len(self.calls)}", "0.0025")


class Reader:
    """Scripted label reader: readings[(region_id, is_zoom)] -> LabelReading.

    Since batch 18 every read is a crop, so a region's second read is its zoom (SPEC §4 steps 4-5).
    """

    def __init__(self, readings):
        self.readings, self.calls = readings, []

    def read(self, image, region, *, mime, cropped=False):
        is_zoom = any(call[0] == region.region_id for call in self.calls)
        self.calls.append((region.region_id, cropped, Image.open(io.BytesIO(image)).size))
        return self.readings[(region.region_id, is_zoom)], trace(f"read-{len(self.calls)}", "0.002")


R0, R1 = region(0, 110, 10, 189, 89), region(1, 10, 10, 89, 89)
BELOC = LabelReading(region_id=R0.region_id, label_text="Beloc-Zok 100 mg", inn="metoprolol",
                     strength=st(mg("metoprolol succinate", 100), release="modified"), readability="readable")
CONCOR = LabelReading(region_id=R1.region_id, label_text="Concor 5 mg", inn="bisoprolol",
                      strength=st(mg("bisoprolol fumarate", 5), release="immediate"), readability="readable")
BLURRY = LabelReading(region_id=R1.region_id, label_text=None, readability="unreadable")


def run(segmenter, reader, audio=b"RIFF....", **kw):
    return run_intake(audio, [(IMAGE, "image/png")], transcriber=Transcriber(), extractor=Extractor(),
                      segmenter=segmenter, reader=reader, catalogue=load_catalogue(), **kw)


# --- the loop ----------------------------------------------------------------------------------------------

def test_concept_fallback_then_crop_zoom_recovers_an_unreadable_label():
    seg = Segmenter({"medicine box": [], "label": [R0, R1]})
    reader = Reader({(R0.region_id, False): BELOC, (R1.region_id, False): BLURRY, (R1.region_id, True): CONCOR})
    report = run(seg, reader)
    assert [c for _, c in seg.calls] == ["medicine box", "label"]
    assert all(sha == SHA for sha, _ in seg.calls)            # SAM only ever sees the source photo (F-06)
    assert all(cropped for _, cropped, _ in reader.calls)      # batch 18: every read is a crop
    assert [c for c in reader.calls if c[0] == R1.region_id] == [  # the crop (80x80 + 10% margin), then its 2x zoom
        (R1.region_id, True, (88, 88)), (R1.region_id, True, (176, 176))]
    obs = {o.visual_evidence[0]: o for o in report.observations}
    assert obs[R1.region_id].label_text == "Concor 5 mg"     # the zoomed reading keeps the source region id
    assert {(f.claim_id, f.type) for f in report.findings} == {("c1", D.MATCH), (None, D.MISSING_MODALITY)}
    assert [s.action for s in report.steps].count(AgentAction.ZOOM_READ) == 1


def test_still_unreadable_after_one_zoom_is_reported_never_guessed():
    seg = Segmenter({"medicine box": [R1]})
    reader = Reader({(R1.region_id, False): BLURRY, (R1.region_id, True): BLURRY})
    report = run(seg, reader)
    assert len(reader.calls) == 2                              # max_grounding_iters = 2
    assert D.UNREADABLE_SOURCE in {f.type for f in report.findings}


def test_only_the_top_regions_are_read():
    many = [region(i, 1 + i * 30, 1, 20 + i * 30, 50, c=0.1 * (i + 1)) for i in range(5)]
    readings = {(r.region_id, False): LabelReading(region_id=r.region_id, label_text="Concor 5 mg",
                                                   readability="readable") for r in many}
    reader = Reader(readings)
    run(Segmenter({"medicine box": many}), reader)
    assert len(reader.calls) == 3


def test_call_budget_stops_the_loop_cleanly():
    seg = Segmenter({"medicine box": [], "label": [R0, R1]})
    reader = Reader({(R0.region_id, False): BELOC, (R1.region_id, False): BLURRY, (R1.region_id, True): CONCOR})
    report = run(seg, reader, max_provider_calls=4)
    assert report.calls == 4
    assert report.steps[-1].action is AgentAction.BUDGET_EXHAUSTED
    ReconciliationReport.model_validate_json(report.model_dump_json())  # still a valid, complete artifact


def test_no_audio_means_visual_only_findings():
    seg = Segmenter({"medicine box": [R0]})
    report = run(seg, Reader({(R0.region_id, False): BELOC}), audio=None)
    assert report.turns == [] and report.claims == []
    assert {f.type for f in report.findings} == {D.MISSING_MODALITY}


def test_report_spend_includes_every_attempt():
    seg = Segmenter({"medicine box": [R0]})
    report = run(seg, Reader({(R0.region_id, False): BELOC}))
    # voice 0.0003 + claims 0.01 + sam 0.0025 + read 0.002
    assert report.spend_usd == Decimal("0.0148") and report.calls == 4


# --- crop provenance -------------------------------------------------------------------------------------------

def test_crop_adds_a_clamped_margin_in_source_pixels():
    assert Image.open(io.BytesIO(crop_region(IMAGE, R1))).size == (88, 88)
    edge = region(2, 0, 0, 49, 49)  # 50x50 at the corner: +2 px right/bottom, clamped left/top
    assert Image.open(io.BytesIO(crop_region(IMAGE, edge))).size == (52, 52)


def test_crop_refuses_an_image_that_is_not_the_region_source():
    with pytest.raises(ValueError):
        crop_region(png(200, 100)[:-1] + b"x", R1)
    other = png(300, 100)
    wrong = ImageRegion(region_id="x-0", image_sha256=hashlib.sha256(other).hexdigest(), object_id=0,
                        x1=0, y1=0, x2=10, y2=10, frame_w=200, frame_h=100)
    with pytest.raises(ValueError):  # bytes match the hash but not the frame size
        crop_region(other, wrong)


def test_label_reader_prompt_differs_for_crops():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        body = json.dumps({"label_text": "Concor 5 mg", "inn": None, "readability": "readable", "country": None,
                           "strength": None})
        return httpx.Response(200, json={"id": "c", "choices": [{"message": {"content": body}}],
                                         "usage": {"prompt_tokens": 1, "completion_tokens": 1}})

    reader = MetaLabelReader(MetaClient(api_key="LLM_t_s", transport=httpx.MockTransport(handler)),
                             SpendGuard_tmp())
    reader.read(IMAGE, R1, mime="image/png")
    reading, _ = reader.read(crop_region(IMAGE, R1), R1, mime="image/png", cropped=True)
    full, crop = (json.dumps(s["messages"]) for s in seen)
    assert "x1=" in full and "x1=" not in crop and "cropped" in crop.lower()
    assert reading.region_id == R1.region_id


def SpendGuard_tmp():
    import tempfile
    from pathlib import Path
    return SpendGuard(Path(tempfile.mkdtemp()) / "l.jsonl", cap_usd=Decimal("5"))


# --- report integrity (M1 #10) ----------------------------------------------------------------------------------

def test_report_rejects_evidence_that_points_nowhere():
    seg = Segmenter({"medicine box": [R0]})
    good = run(seg, Reader({(R0.region_id, False): BELOC}))
    data = json.loads(good.model_dump_json())
    visual = next(i for i, f in enumerate(data["findings"]) if f["visual_evidence"])
    data["findings"][visual]["visual_evidence"] = ["no-such-region"]
    with pytest.raises(ValidationError):
        ReconciliationReport.model_validate(data)
    data = json.loads(good.model_dump_json())
    data["claims"][0]["audio_evidence"] = ["turn-9"]
    with pytest.raises(ValidationError):
        ReconciliationReport.model_validate(data)


def test_report_schema_has_no_reference_cycles():
    schema = json.dumps(ReconciliationReport.model_json_schema())
    assert '"#/$defs/ReconciliationReport"' not in schema


# --- session caps (F-07) --------------------------------------------------------------------------------------------

def test_session_guard_caps_calls_and_dollars_and_still_writes_the_ledger(tmp_path):
    parent = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal("5"))
    s = SessionGuard(parent, max_usd=Decimal("0.02"), max_calls=2)
    s.check(Decimal("0.01"))
    s.charge_prechecked(trace("a", "0.01"))
    with pytest.raises(SessionCapExceeded):
        s.check(Decimal("0.015"))                     # 0.01 + 0.015 > 0.02
    s.charge_prechecked(trace("b", "0.005"))
    with pytest.raises(SessionCapExceeded):
        s.check(Decimal("0.001"))                     # third call > max_calls
    assert issubclass(SessionCapExceeded, SpendCapExceeded)
    assert parent.total_usd == Decimal("0.015") and s.total_usd == Decimal("0.015")


def test_arabic_advice_is_caught_as_a_regression_check():
    for text in ["خذ قرصين الآن", "يجب أن تتوقف عن الدواء", "ضاعف الجرعة"]:
        with pytest.raises(AdviceLeak):
            assert_no_advice(text)


# --- QM3 #2-#4 --------------------------------------------------------------------------------------------------------

CAT = load_catalogue()
BELOC_95 = PackObservation(observation_id="o1", label_text="Beloc-Zok 95 mg",
                           strength=st(mg("metoprolol succinate", 95), release="modified"),
                           readability="readable", visual_evidence=["r1"])


def claim(name, intake=None, strength=None):
    return PatientClaim(claim_id="c1", name_text=name, intake_amount=intake, strength=strength, status="active",
                        audio_evidence=["t1"])


@pytest.mark.parametrize("amount,expected", [(95, D.MATCH), (100, D.MATCH), (47.5, D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH),
                                             (50, D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH)])
def test_qm3_2_literal_or_nominal_eu_strength(amount, expected):
    assert reconcile_pair(claim("Beloc-Zok", intake=mg("metoprolol", amount)), BELOC_95, CAT).type is expected


def test_qm3_3_salt_separated_from_the_moiety_is_found():
    pack = PackObservation(observation_id="o1", label_text="Metoprolol succinate 100 mg", strength=st(mg("metoprolol", 100)),
                           readability="readable", visual_evidence=["r1"])
    c = claim("metoprolol 100 mg tartrate", intake=mg("metoprolol", 100))
    assert reconcile_pair(c, pack, CAT).type is D.FORMULATION_MISMATCH


def test_qm3_3_salt_next_to_a_brand_is_found():
    c = claim("Beloc-Zok succinate", intake=mg("metoprolol", 100))
    pack = PackObservation(observation_id="o1", label_text="Beloc-Zok 100 mg",
                           strength=st(mg("metoprolol tartrate", 100), release="modified"),
                           readability="readable", visual_evidence=["r1"])
    assert reconcile_pair(c, pack, CAT).type is D.FORMULATION_MISMATCH


def test_qm3_4_country_reaches_brand_implied_facts():
    def entry(country, release):
        return CatalogueEntry(brand="Lopresor", inns=frozenset({"metoprolol"}), countries=(country,), synthetic=True,
                              release=release, splittable=None)
    cat = Catalogue((entry("GB", Release.IMMEDIATE), entry("DE", Release.MODIFIED)))
    assert cat.implied_release("Lopresor 100 mg", country="DE") is Release.MODIFIED
    assert cat.implied_release("Lopresor 100 mg", country="GB") is Release.IMMEDIATE
