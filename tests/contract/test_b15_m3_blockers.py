"""Batch 15 contract: clear the QM M3 HOLD (evidence/grills/m3-agent-loop/effect.md). Written by the reviewer.

Do not edit. #1 blocker: a failed call that was charged must reach the report's spend and call ids.
#2 conflicted candidates can't win pairing. #3 salt words next to joined or clitic brand forms.
#4 a stated tablet STRENGTH equals the literal or the nominal amount; multiples only apply to intakes.
#7 the two batch 14 reviewer behaviours become contract.
"""

import hashlib
import io
from decimal import Decimal

import httpx
import pytest
from PIL import Image

from anamnesis.agent import AgentAction, run_intake
from anamnesis.agent.loop import _zoom
from anamnesis.agent.session import IntakeSession
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all, reconcile_pair
from anamnesis.providers import ProviderError, ProviderTrace, SpendCapExceeded, SpendGuard
from anamnesis.providers.meta import MetaClient, MetaLabelReader, MetaSegmenter
from anamnesis.providers.spark import LabelReading
from anamnesis.schema import AudioTurn, ImageRegion, IngredientAmount, PackObservation, PatientClaim, Strength
from anamnesis.schema import DiscrepancyType as D

CAT = load_catalogue()


def png(w=40, h=40):
    buf = io.BytesIO()
    Image.new("RGB", (w, h)).save(buf, format="PNG")
    return buf.getvalue()


IMAGE = png()
SHA = hashlib.sha256(IMAGE).hexdigest()
REGION = ImageRegion(region_id=f"{SHA[:12]}-0", image_sha256=SHA, object_id=0, x1=0, y1=0, x2=9, y2=9,
                     frame_w=40, frame_h=40)


def mg(inn, a):
    return IngredientAmount(inn=inn, amount=Decimal(str(a)), unit="mg")


def st(*parts, release="unknown"):
    return Strength(ingredients=list(parts), per="tablet", release=release)


# --- #1 (blocker): charged failures reach the caller and the report -----------------------------------

class Script:
    def __init__(self, *steps):
        self.steps = list(steps)

    def __call__(self, request):
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return httpx.Response(step[0], json=step[1])


def client(*steps):
    return MetaClient(api_key="LLM_t_s", transport=httpx.MockTransport(Script(*steps)))


@pytest.fixture
def guard(tmp_path):
    return SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal("5"))


def test_two_charged_timeouts_are_carried_on_the_error(guard):
    seg = MetaSegmenter(client(httpx.ReadTimeout("slow"), httpx.ReadTimeout("slow")), guard)
    with pytest.raises(ProviderError) as e:
        seg.segment(IMAGE, "label", mime="image/png")
    assert e.value.charged_usd == Decimal("0.005") and len(e.value.charged_call_ids) == 2
    assert guard.total_usd == Decimal("0.005")  # the ledger and the error agree


def test_two_paid_invalid_spark_replies_are_carried_on_the_error(guard):
    def chat(cid):
        return {"id": cid, "choices": [{"message": {"content": "not json"}}],
                "usage": {"prompt_tokens": 1000, "completion_tokens": 200}}
    reader = MetaLabelReader(client((200, chat("a")), (200, chat("b"))), guard)
    with pytest.raises(ProviderError) as e:
        reader.read(IMAGE, REGION, mime="image/png")
    assert e.value.charged_call_ids == ["a", "b"]
    assert e.value.charged_usd == 2 * (Decimal("0.00125") + Decimal("0.00085"))


def test_rejected_calls_carry_no_charge(guard):
    seg = MetaSegmenter(client((400, {"error": {"message": "bad"}})), guard)
    with pytest.raises(ProviderError) as e:
        seg.segment(IMAGE, "label", mime="image/png")
    assert e.value.charged_usd == Decimal(0) and e.value.charged_call_ids == []


def test_the_report_counts_spend_of_a_failed_call():
    class Transcriber:
        def transcribe(self, wav, *, language_bias=None, keywords=None, lang_hint=None):
            return [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=10, transcript="Concor five")], \
                ProviderTrace(call_id="v", model_id="fixture:v", latency_ms=0, input_tokens=0, output_tokens=0,
                              cost_usd=Decimal("0.001"))

    class FailingExtractor:
        def extract(self, turns):
            raise ProviderError("spark", "invalid twice", retryable=True, charged_call_ids=["x1", "x2"],
                                charged_usd=Decimal("0.004"))

    class NoRegions:
        def segment(self, image, concept, *, mime):
            return [], ProviderTrace(call_id=f"s-{concept}", model_id="fixture:s", latency_ms=0, input_tokens=0,
                                     output_tokens=0, cost_usd=Decimal("0.0025"))

    report = run_intake(b"RIFF", [(IMAGE, "image/png")], transcriber=Transcriber(), extractor=FailingExtractor(),
                        segmenter=NoRegions(), reader=None, catalogue=CAT)
    # Batch 23: a photo where nothing is found now asks SAM three concepts (medicine box, label, package).
    assert report.spend_usd == Decimal("0.001") + Decimal("0.004") + 3 * Decimal("0.0025")
    failed = next(s for s in report.steps if s.action is AgentAction.EXTRACT_CLAIMS)
    assert failed.call_ids == ["x1", "x2"] and failed.outcome.startswith("error")


# --- #2: a conflicted candidate can't win pairing ------------------------------------------------------------

def test_conflicted_candidate_scores_below_a_clean_one():
    clean = PatientClaim(claim_id="c1", name_text="Concor", intake_amount=mg("bisoprolol", 5), status="active",
                         audio_evidence=["t1"])
    conflicted = PatientClaim(claim_id="c2", name_text="Concor", inn="amlodipine", strength=st(mg("bisoprolol", 5)),
                              status="active", audio_evidence=["t2"])
    pack = PackObservation(observation_id="o1", label_text="Concor 5 mg", strength=st(mg("bisoprolol", 5)),
                           readability="readable", visual_evidence=["r1"])
    found = {(f.claim_id, f.observation_id): f.type for f in reconcile_all([clean, conflicted], [pack], CAT)}
    assert found[("c1", "o1")] is D.MATCH  # was: c2 took the pack with score 3


# --- #3: salt words next to joined or clitic brand forms -------------------------------------------------------

def test_salt_next_to_a_joined_brand_is_found():
    c = PatientClaim(claim_id="c1", name_text="BelocZok succinate", intake_amount=mg("metoprolol", 100),
                     status="active", audio_evidence=["t1"])
    pack = PackObservation(observation_id="o1", label_text="Beloc-Zok 100 mg",
                           strength=st(mg("metoprolol tartrate", 100), release="modified"),
                           readability="readable", visual_evidence=["r1"])
    assert reconcile_pair(c, pack, CAT).type is D.FORMULATION_MISMATCH


def test_salt_next_to_an_arabic_brand_with_a_clitic_is_found():
    c = PatientClaim(claim_id="c1", name_text="الكونكور fumarate", intake_amount=mg("bisoprolol", 5),
                     status="active", audio_evidence=["t1"])
    pack = PackObservation(observation_id="o1", label_text="Concor 5 mg",
                           strength=st(mg("bisoprolol hemifumarate", 5), release="immediate"),
                           readability="readable", visual_evidence=["r1"])
    assert reconcile_pair(c, pack, CAT).type is D.FORMULATION_MISMATCH


# --- #4: a stated tablet strength is exact; multiples are only for intakes ---------------------------------------

BELOC_95 = PackObservation(observation_id="o1", label_text="Beloc-Zok 95 mg",
                           strength=st(mg("metoprolol succinate", 95), release="modified"),
                           readability="readable", visual_evidence=["r1"])


@pytest.mark.parametrize("amount,expected", [(95, D.MATCH), (100, D.MATCH), (47.5, D.STRENGTH_MISMATCH),
                                             (190, D.STRENGTH_MISMATCH), (50, D.STRENGTH_MISMATCH)])
def test_stated_strength_must_equal_literal_or_nominal(amount, expected):
    c = PatientClaim(claim_id="c1", name_text="Beloc-Zok", strength=st(mg("metoprolol", amount), release="modified"),
                     status="active", audio_evidence=["t1"])
    assert reconcile_pair(c, BELOC_95, CAT).type is expected


# --- #7: batch 14 reviewer behaviours, now contract -------------------------------------------------------------

def test_spend_cap_ends_the_session():
    session = IntakeSession(max_provider_calls=12)
    attempts = []

    def refused():
        attempts.append(1)
        raise SpendCapExceeded("cap")

    assert session.call(AgentAction.READ, "r1", refused, str) is None
    assert session.call(AgentAction.READ, "r2", refused, str) is None
    assert attempts == [1] and session.exhausted
    assert session.steps[-1].action is AgentAction.BUDGET_EXHAUSTED


def test_zoom_reading_for_another_region_is_rejected():
    first = LabelReading(region_id=REGION.region_id, readability="unreadable")

    class Drifting:
        def read(self, image, region, *, mime, cropped=False):
            return (LabelReading(region_id="other-9", label_text="Concor", readability="readable"),
                    ProviderTrace(call_id="z", model_id="fixture:x", latency_ms=0, input_tokens=0, output_tokens=0,
                                  cost_usd=Decimal(0)))

    assert _zoom(IntakeSession(5), Drifting(), (IMAGE, "image/png"), REGION, first) is first
