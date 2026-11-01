"""Extra offline checks for batch 31 follow-up (SPEC §8, "The follow-up by itself")."""

import hashlib
import io
from decimal import Decimal

import pytest
from PIL import Image as PILImage

from anamnesis.agent.loop import _intake_id, _prepare
from anamnesis.brief import render_brief
from anamnesis.core.catalogue import load_catalogue
from anamnesis.providers import ProviderTrace
from anamnesis.providers.spark import LabelReading
from anamnesis.review import follow_up, new_review, requestable
from anamnesis.schema import AudioTurn, Finding, ImageRegion, PatientClaim
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.medication import PackObservation
from anamnesis.schema.report import AgentAction, AgentStep, ReconciliationReport
from anamnesis.schema.review import FollowUpOutcome, RequestKind, RequestStatus, ReviewStatus
from anamnesis.schema.templates import QUESTION_FOR, TEMPLATES

CAT = load_catalogue()
GOT, AGAIN = FollowUpOutcome.ANSWERED, FollowUpOutcome.DUPLICATE


def _png(w, h, colour):
    buf = io.BytesIO()
    PILImage.new("RGB", (w, h), colour).save(buf, "PNG")
    return buf.getvalue()


PHOTO = _png(600, 300, (200, 200, 200))
PHOTO2 = _png(400, 300, (180, 190, 200))
IMAGES = [(PHOTO, "image/png")]
GIVE2 = (PHOTO2, "image/png")
AUDIO = (b"RIFF b31 extra fixture", "audio/wav")
SHA2 = hashlib.sha256(PHOTO2).hexdigest()


def _region(image, box, obj):
    sha = hashlib.sha256(image).hexdigest()
    w, h = PILImage.open(io.BytesIO(image)).size
    return ImageRegion(region_id=f"{sha[:12]}-{obj}", image_sha256=sha, object_id=obj,
                       x1=box[0], y1=box[1], x2=box[2], y2=box[3], frame_w=w, frame_h=h,
                       confidence=0.9)


R0 = _region(PHOTO, (10, 20, 139, 279), 0)
R2 = _region(PHOTO2, (20, 20, 379, 279), 0)
DARK = LabelReading(region_id="x", readability="unreadable")


def _trace(cid):
    return ProviderTrace(call_id=cid, model_id="fixture:test", latency_ms=1, input_tokens=0,
                         output_tokens=0, cost_usd=Decimal("0.001"))


class _Segmenter:
    """Regions per photo sha, but only for the allowed concepts; records every call."""

    def __init__(self, by_sha, concepts=None):
        self.by_sha, self.concepts, self.seen = dict(by_sha), concepts, []

    def segment(self, image, concept, *, mime):
        self.seen.append((hashlib.sha256(image).hexdigest(), concept))
        if self.concepts is not None and concept not in self.concepts:
            return [], _trace(f"s-{len(self.seen)}")
        sha = hashlib.sha256(image).hexdigest()
        return list(self.by_sha.get(sha, [])), _trace(f"s-{len(self.seen)}")


class _Reader:
    def __init__(self, script):
        self.script, self.seen = {key: list(value) for key, value in script.items()}, []

    def read(self, image, region, *, mime, cropped=False):
        self.seen.append(region.region_id)
        reading = self.script[region.region_id].pop(0)
        return reading.model_copy(update={"region_id": region.region_id}), _trace(f"r-{len(self.seen)}")


class _Patient:
    def __init__(self, *answers):
        self.answers, self.asked = list(answers), []

    def __call__(self, request, message):
        self.asked.append((request, message))
        return self.answers.pop(0) if self.answers else None


def _finding(fid, kind, claim_id=None, observation_id=None, audio=(), visual=()):
    return Finding.model_validate({
        "finding_id": fid, "type": kind, "claim_id": claim_id,
        "observation_id": observation_id, "audio_evidence": list(audio),
        "visual_evidence": list(visual),
        "needs_clinician_review": kind is not D.MATCH,
        "clinician_note": TEMPLATES[kind], "patient_question_id": QUESTION_FOR[kind],
    })


def _report():
    """One dark pack for the clinician and one medicine for the follow-up to ask about."""
    prepared = _prepare(IMAGES)
    intake = _intake_id(AUDIO[0], [photo for photo, _, _ in prepared])
    report = ReconciliationReport(
        intake_id=intake,
        turns=[AudioTurn(turn_id="turn-0", start_ms=0, end_ms=1000, transcript="Sortis")],
        claims=[PatientClaim(claim_id="c9", name_text="Sortis", status="active",
                              audio_evidence=["turn-0"])],
        regions=[R0],
        observations=[PackObservation(observation_id="o0", readability="unreadable",
                                      visual_evidence=[R0.region_id])],
        findings=[_finding("f0", D.UNREADABLE_SOURCE, observation_id="o0", visual=[R0.region_id]),
                  _finding("f1", D.MISSING_MODALITY, claim_id="c9", audio=["turn-0"])],
        steps=[AgentStep(n=0, action=AgentAction.RECONCILE, target="all", outcome="done")],
        calls=0, spend_usd=Decimal(0))
    assert requestable(report) == [(RequestKind.UNREADABLE, "o0"),
                                   (RequestKind.NOT_PHOTOGRAPHED, "c9")]
    return report


def _run(report, patient, **kw):
    kw.setdefault("segmenter", _Segmenter({SHA2: [R2]}))
    kw.setdefault("reader", _Reader({R2.region_id: [DARK, DARK]}))
    return follow_up(report, new_review(report), list(IMAGES), AUDIO, reply=patient,
                     catalogue=CAT, **kw)


def test_a_repeat_of_an_answering_photo_is_a_duplicate_and_goes_to_no_model():
    segmenter = _Segmenter({SHA2: [R2]})
    new, review, given, log = _run(_report(), _Patient(GIVE2, GIVE2), max_rounds=2,
                                   segmenter=segmenter)
    assert [(s.round, s.target_id, s.outcome) for s in log] == [(1, "c9", GOT), (2, "c9", AGAIN)]
    assert [s.request_id for s in log] == ["r1", "r2"]
    assert {r.kind for r in review.requests} == {RequestKind.NOT_PHOTOGRAPHED}
    assert {sha for sha, _ in segmenter.seen} == {SHA2} and len(segmenter.seen) == 1
    assert [(r.request_id, r.status, r.photo_index) for r in review.requests] == [
        ("r1", RequestStatus.ANSWERED, 2), ("r2", RequestStatus.OPEN, None)]
    assert review.status is ReviewStatus.AWAITING_PATIENT
    assert given == [*IMAGES, GIVE2]
    assert (RequestKind.NOT_PHOTOGRAPHED, "c9") in requestable(new)


def test_custom_concepts_reach_the_photo_calls():
    seen = {}
    for name, kw in (("default", {}), ("package-only", {"concepts": ("package",)})):
        segmenter = _Segmenter({SHA2: [R2]}, concepts={"package"})
        _, _, _, log = _run(_report(), _Patient(GIVE2), max_rounds=1,
                             segmenter=segmenter, **kw)
        assert [s.outcome for s in log] == [GOT]
        seen[name] = [concept for _, concept in segmenter.seen]
    assert seen == {"default": ["medicine box", "label", "package"], "package-only": ["package"]}


def test_a_refusal_other_than_a_repeated_photo_propagates():
    report = _report()
    before = report.model_dump()
    patient = _Patient((b"xx",))  # a malformed photo: no mime to prepare with
    with pytest.raises(ValueError):
        _run(report, patient, max_rounds=1)
    assert len(patient.asked) == 1
    assert report.model_dump() == before


def test_what_reply_raises_propagates_and_changes_nothing():
    report = _report()
    before = report.model_dump()

    def failing(request, message):
        raise RuntimeError("the channel broke")

    with pytest.raises(RuntimeError, match="the channel broke"):
        _run(report, failing, max_rounds=1)
    assert report.model_dump() == before


def test_the_follow_up_line_sits_inside_the_scope_header():
    new, review, given, log = _run(_report(), _Patient(GIVE2), max_rounds=1)
    assert len(log) == 1
    page = render_brief(new, given, AUDIO, CAT, review=review, follow_up=log)
    assert page.index('id="follow-up"') < page.index("</header>")
