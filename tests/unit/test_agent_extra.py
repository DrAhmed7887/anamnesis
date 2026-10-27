"""Extra batch 14 checks: loop edge cases, session guard, loose salts."""

import hashlib
import io
from decimal import Decimal

import pytest
from PIL import Image

from anamnesis.agent import AgentAction, crop_region, run_intake
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_pair
from anamnesis.providers import ProviderError, ProviderTrace, SpendGuard
from anamnesis.providers.spend import SessionCapExceeded, SessionGuard
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import ImageRegion, IngredientAmount, PackObservation, PatientClaim, Strength

CAT = load_catalogue()


def _png(w=100, h=100):
    buf = io.BytesIO()
    Image.new("RGB", (w, h)).save(buf, format="PNG")
    return buf.getvalue()


IMG = _png()
SHA = hashlib.sha256(IMG).hexdigest()
REGION = ImageRegion(region_id=f"{SHA[:12]}-0", image_sha256=SHA, object_id=0, x1=10, y1=10, x2=49, y2=49,
                     frame_w=100, frame_h=100, confidence=0.9)


def _trace(cid):
    return ProviderTrace(call_id=cid, model_id="fixture:t", latency_ms=1, input_tokens=0, output_tokens=0,
                         cost_usd=Decimal("0.001"), prior_call_ids=["p"], prior_cost_usd=Decimal("0.002"))


class FailingSegmenter:
    def segment(self, image, concept, *, mime):
        raise ProviderError("sam", "secret model prose")


def test_provider_error_becomes_a_step_without_prose():
    report = run_intake(None, [(IMG, "image/png")], transcriber=None, extractor=None,
                        segmenter=FailingSegmenter(), reader=None, catalogue=CAT)
    outcomes = [s.outcome for s in report.steps if s.action is AgentAction.SEGMENT]
    assert len(outcomes) == 2 and all("secret" not in o for o in outcomes)
    assert report.calls == 2 and report.findings == []


def test_budget_of_zero_skips_every_call_but_still_reports():
    report = run_intake(b"RIFF", [(IMG, "image/png")], transcriber=None, extractor=None, segmenter=None,
                        reader=None, catalogue=CAT, max_provider_calls=0)
    assert report.calls == 0 and [s.action for s in report.steps] == [AgentAction.BUDGET_EXHAUSTED]


def test_intake_id_is_deterministic():
    a = run_intake(None, [], transcriber=None, extractor=None, segmenter=None, reader=None, catalogue=CAT)
    b = run_intake(None, [], transcriber=None, extractor=None, segmenter=None, reader=None, catalogue=CAT)
    c = run_intake(b"x", [], transcriber=None, extractor=None, segmenter=None, reader=None, catalogue=CAT,
                   max_provider_calls=0)
    assert a.intake_id == b.intake_id != c.intake_id


def test_crop_rejects_undecodable_bytes_with_matching_hash():
    junk = b"not an image"
    region = REGION.model_copy(update={"image_sha256": hashlib.sha256(junk).hexdigest()})
    with pytest.raises(ValueError):
        crop_region(junk, region)


def test_crop_is_png_of_the_expected_size():
    assert Image.open(io.BytesIO(crop_region(IMG, REGION))).size == (44, 44)


def test_session_guard_charge_reaches_parent_and_enforces_session_cap(tmp_path):
    parent = SpendGuard(tmp_path / "l.jsonl", cap_usd=Decimal("5"))
    guard = SessionGuard(parent, max_usd=Decimal("1"), max_calls=1)
    guard.charge(_trace("a"))
    assert parent.total_usd == guard.total_usd == Decimal("0.001")
    with pytest.raises(SessionCapExceeded):
        guard.check(Decimal("0"))
    guard.charge_estimate("m", Decimal("0.5"), "uncertain")
    assert parent.total_usd == Decimal("0.501")


def test_session_guard_still_applies_the_parent_cap(tmp_path):
    parent = SpendGuard(tmp_path / "l.jsonl", cap_usd=Decimal("0.01"))
    with pytest.raises(Exception, match="spend cap"):
        SessionGuard(parent, max_usd=Decimal("1"), max_calls=5).check(Decimal("0.02"))


def _pack(label, strength):
    return PackObservation(observation_id="o1", label_text=label, strength=strength, readability="readable",
                           visual_evidence=["r1"])


def test_salt_word_without_the_moiety_is_not_a_salt_fact():
    claim = PatientClaim(claim_id="c1", name_text="Concor tartrate", status="active", audio_evidence=["t1"],
                         intake_amount=IngredientAmount(inn="bisoprolol", amount=Decimal(5), unit="mg"))
    pack = _pack("Concor 5 mg", Strength(ingredients=[IngredientAmount(inn="bisoprolol", amount=Decimal(5),
                                                                     unit="mg")], per="tablet"))
    assert reconcile_pair(claim, pack, CAT).type is not D.FORMULATION_MISMATCH


def test_reviewer_spend_cap_ends_the_session_instead_of_retrying_every_call() -> None:
    # Reviewer fix (batch 14): a money cap is a stop, like the call budget, not one error per remaining call.
    from decimal import Decimal as _D

    from anamnesis.agent.session import IntakeSession
    from anamnesis.providers.spend import SpendCapExceeded
    from anamnesis.schema.report import AgentAction

    session = IntakeSession(max_provider_calls=12)
    attempts = []

    def refused():
        attempts.append(1)
        raise SpendCapExceeded("cap")

    assert session.call(AgentAction.READ, "r1", refused, str) is None
    assert session.call(AgentAction.READ, "r2", refused, str) is None
    assert attempts == [1] and session.exhausted
    assert session.steps[-1].action is AgentAction.BUDGET_EXHAUSTED
    assert session.spend_usd == _D(0)


def test_reviewer_zoom_reading_with_a_foreign_region_id_is_rejected() -> None:
    import hashlib
    import io

    from PIL import Image as PILImage

    from anamnesis.agent.loop import _zoom
    from anamnesis.agent.session import IntakeSession
    from anamnesis.providers import ProviderTrace
    from anamnesis.providers.spark import LabelReading
    from anamnesis.schema import ImageRegion

    buf = io.BytesIO()
    PILImage.new("RGB", (40, 40)).save(buf, format="PNG")
    data = buf.getvalue()
    region = ImageRegion(region_id="src-0", image_sha256=hashlib.sha256(data).hexdigest(), object_id=0,
                         x1=0, y1=0, x2=9, y2=9, frame_w=40, frame_h=40)
    first = LabelReading(region_id="src-0", readability="unreadable")

    class Drifting:
        def read(self, image, region, *, mime, cropped=False):
            return (LabelReading(region_id="other-9", label_text="Concor", readability="readable"),
                    ProviderTrace(call_id="z", model_id="fixture:x", latency_ms=0, input_tokens=0,
                                  output_tokens=0, cost_usd=0))

    kept = _zoom(IntakeSession(5), Drifting(), (data, "image/png"), region, first)
    assert kept is first
