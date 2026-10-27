"""Extra offline checks for batch 20 clinician review (SPEC §8)."""

import hashlib
import io
from decimal import Decimal

import pytest
from PIL import Image as PILImage
from pydantic import ValidationError

from anamnesis.agent.loop import _intake_id, _prepare
from anamnesis.brief import coverage_lines, render_brief
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.guardrails import assert_no_advice
from anamnesis.providers import ProviderTrace
from anamnesis.providers.spark import LabelReading
from anamnesis.review import (
    add_photo,
    approve,
    new_review,
    request_message,
    request_photo,
    requestable,
    withdraw,
)
from anamnesis.schema import AudioTurn, Finding, ImageRegion, PatientClaim
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.medication import PackObservation
from anamnesis.schema.report import AgentAction, AgentStep, ReconciliationReport
from anamnesis.schema.review import PhotoRequest, RequestKind, RequestStatus, Review, ReviewStatus
from anamnesis.schema.templates import (
    COVERAGE_REQUESTS,
    QUESTION_FOR,
    REQUEST_NOT_PHOTOGRAPHED,
    REQUEST_UNREADABLE,
    REVIEW_APPROVED,
    REVIEW_DRAFT,
    REVIEW_REPLACED,
    REVIEW_REQUESTED,
    REVIEW_WAITING,
    TEMPLATES,
)

CAT = load_catalogue()


def _png(colour=(200, 200, 200)):
    buf = io.BytesIO()
    PILImage.new("RGB", (64, 32), colour).save(buf, "PNG")
    return buf.getvalue()


PHOTO = _png()
PHOTO2 = _png((10, 20, 30))
IMAGES = [(PHOTO, "image/png")]
AUDIO = (b"RIFF fixture", "audio/wav")


def _region(image, obj=0):
    sha = hashlib.sha256(image).hexdigest()
    w, h = PILImage.open(io.BytesIO(image)).size
    return ImageRegion(region_id=f"{sha[:12]}-{obj}", image_sha256=sha, object_id=obj,
                       x1=1, y1=1, x2=10, y2=10, frame_w=w, frame_h=h, confidence=0.9)


R0 = _region(PHOTO)
R2 = _region(PHOTO2)


def _finding(fid, kind, claim_id=None, observation_id=None, audio=(), visual=()):
    return {
        "finding_id": fid, "type": kind, "claim_id": claim_id,
        "observation_id": observation_id, "audio_evidence": list(audio),
        "visual_evidence": list(visual),
        "needs_clinician_review": kind is not D.MATCH,
        "clinician_note": TEMPLATES[kind], "patient_question_id": QUESTION_FOR[kind],
    }


def _report(images=IMAGES, audio=AUDIO, multi=False):
    prepared = _prepare(images)
    audio_bytes = audio[0] if audio is not None else None
    intake = _intake_id(audio_bytes, [photo for photo, _, _ in prepared])
    claims = [PatientClaim(claim_id="c1", name_text="  \nConcor 5 mg\nsecond line",
                           status="active", audio_evidence=["turn-0"])]
    observations = [PackObservation(observation_id="o0", readability="unreadable",
                                    visual_evidence=[R0.region_id])]
    findings = [_finding("f0", D.UNREADABLE_SOURCE, observation_id="o0", visual=[R0.region_id])]
    if multi:
        claims.append(PatientClaim(claim_id="c2", name_text="Aspirin", status="active",
                                   audio_evidence=["turn-0"]))
        findings.append(_finding("f1", D.MISSING_MODALITY, claim_id="c2", audio=["turn-0"]))
    return ReconciliationReport(
        intake_id=intake,
        turns=[AudioTurn(turn_id="turn-0", start_ms=0, end_ms=1000, transcript="Concor")],
        claims=claims, regions=[R0], observations=observations, findings=findings,
        steps=[AgentStep(n=0, action=AgentAction.RECONCILE, target="all", outcome="done")],
        calls=0, spend_usd=Decimal(0))


def _trace(cid):
    return ProviderTrace(call_id=cid, model_id="fixture:test", latency_ms=1, input_tokens=0,
                         output_tokens=0, cost_usd=Decimal("0.001"))


class _Segmenter:
    def __init__(self, by_sha):
        self.by_sha, self.seen = dict(by_sha), []

    def segment(self, image, concept, *, mime):
        self.seen.append(hashlib.sha256(image).hexdigest())
        return list(self.by_sha.get(hashlib.sha256(image).hexdigest(), [])), _trace("s")


class _Reader:
    def __init__(self, script):
        self.script, self.seen = {k: list(v) for k, v in script.items()}, []

    def read(self, image, region, *, mime, cropped=False):
        self.seen.append(region.region_id)
        reading = self.script[region.region_id].pop(0)
        return reading.model_copy(update={"region_id": region.region_id}), _trace("r")


def test_review_models_reject_bad_ids_and_extra_fields():
    with pytest.raises(ValidationError):
        Review(intake_id="xyz", status=ReviewStatus.DRAFT, requests=[])
    with pytest.raises(ValidationError):
        Review(intake_id="A" * 64, status=ReviewStatus.DRAFT, requests=[])
    good = _report()
    with pytest.raises(ValidationError):
        Review(intake_id=good.intake_id, status=ReviewStatus.DRAFT, requests=[], extra=1)
    with pytest.raises(ValidationError):
        PhotoRequest(request_id="r1", kind=RequestKind.UNREADABLE, target_id="o0",
                     status=RequestStatus.ANSWERED, photo_index=0)


def test_quiet_reviews_are_valid_without_open_requests():
    intake = "b" * 64
    done = PhotoRequest(request_id="r1", kind=RequestKind.UNREADABLE, target_id="o0",
                        status=RequestStatus.ANSWERED, photo_index=2)
    back = PhotoRequest(request_id="r2", kind=RequestKind.NOT_PHOTOGRAPHED, target_id="c2",
                        status=RequestStatus.WITHDRAWN)
    assert Review(intake_id=intake, status=ReviewStatus.DRAFT, requests=[done, back]).status is \
        ReviewStatus.DRAFT
    assert Review(intake_id=intake, status=ReviewStatus.APPROVED, requests=[done]).status is \
        ReviewStatus.APPROVED


def test_nothing_is_requestable_without_unreadable_or_claim_only_findings():
    report = _report().model_copy(update={
        "findings": [Finding.model_validate(_finding(
            "f0", D.MATCH, claim_id="c1", observation_id="o0", audio=["turn-0"],
            visual=[R0.region_id]))]})
    assert requestable(report) == []


def test_request_message_uses_the_first_non_blank_line_verbatim():
    report = _report()
    asked = PhotoRequest(request_id="r1", kind=RequestKind.NOT_PHOTOGRAPHED, target_id="c1",
                         status=RequestStatus.OPEN)
    assert request_message(report, asked) == REQUEST_NOT_PHOTOGRAPHED.format(name="Concor 5 mg")


def test_review_calls_never_change_their_inputs():
    report, review = _report(), new_review(_report())
    waiting = request_photo(review, report, "o0")
    before = (report.model_dump(), review.model_dump(), waiting.model_dump())
    withdraw(waiting, "r1")
    approve(new_review(report), report)
    assert (report.model_dump(), review.model_dump(), waiting.model_dump()) == before


def test_add_photo_refusals_call_no_model_and_change_nothing():
    report = _report()
    waiting = request_photo(new_review(report), report, "o0")
    segmenter = _Segmenter({hashlib.sha256(PHOTO2).hexdigest(): [R2]})
    reader = _Reader({R2.region_id: [LabelReading(region_id="x", readability="unreadable")]})
    before = (report.model_dump(), waiting.model_dump())
    with pytest.raises(ValueError):
        add_photo(report, waiting, "r9", (PHOTO2, "image/png"), IMAGES, AUDIO,
                  segmenter=segmenter, reader=reader, catalogue=CAT)
    assert segmenter.seen == [] and reader.seen == []
    assert (report.model_dump(), waiting.model_dump()) == before


def test_add_photo_answers_and_binds_the_new_media():
    report = _report()
    waiting = request_photo(new_review(report), report, "o0")
    sha2 = hashlib.sha256(PHOTO2).hexdigest()
    reading = LabelReading(region_id="x", label_text="Concor 5 mg", readability="readable")
    after, answered = add_photo(report, waiting, "r1", (PHOTO2, "image/png"), IMAGES, AUDIO,
                                segmenter=_Segmenter({sha2: [R2]}),
                                reader=_Reader({R2.region_id: [reading]}), catalogue=CAT)
    assert answered.requests[0].photo_index == 2
    assert answered.intake_id == after.intake_id != report.intake_id
    assert [s.n for s in after.steps] == list(range(len(after.steps)))
    render_brief(after, IMAGES + [(PHOTO2, "image/png")], AUDIO, CAT, review=answered)
    with pytest.raises(ValueError):
        render_brief(after, IMAGES, AUDIO, CAT, review=answered)


def test_approved_reviews_and_withdrawn_counts_on_the_brief():
    report = _report(multi=True)
    both = request_photo(request_photo(new_review(report), report, "o0"), report, "c2")
    page = render_brief(report, IMAGES, AUDIO, CAT, review=both)
    assert REVIEW_WAITING.format(n=2) in page and REVIEW_REQUESTED in page
    assert COVERAGE_REQUESTS.format(n=2, m=0) in page
    signed = approve(withdraw(withdraw(both, "r1"), "r2"), report)
    page = render_brief(report, IMAGES, AUDIO, CAT, review=signed)
    assert REVIEW_APPROVED in page and "Photos requested" not in page


def test_replaced_regions_are_marked_and_coverage_keeps_its_shape():
    report = _report()
    waiting = request_photo(new_review(report), report, "o0")
    sha2 = hashlib.sha256(PHOTO2).hexdigest()
    reading = LabelReading(region_id="x", label_text="Concor 5 mg", readability="readable")
    after, answered = add_photo(report, waiting, "r1", (PHOTO2, "image/png"), IMAGES, AUDIO,
                                segmenter=_Segmenter({sha2: [R2]}),
                                reader=_Reader({R2.region_id: [reading]}), catalogue=CAT)
    assert after.superseded == ["o0"]
    page = render_brief(after, IMAGES + [(PHOTO2, "image/png")], AUDIO, CAT, review=answered)
    assert page.count(REVIEW_REPLACED) == 1
    assert REVIEW_DRAFT in render_brief(after, IMAGES + [(PHOTO2, "image/png")], AUDIO, CAT)
    lines = coverage_lines(after, IMAGES + [(PHOTO2, "image/png")], AUDIO)
    assert lines[0] == "Photos received: 2."


def test_all_new_fixed_text_gives_no_advice():
    for text in (REVIEW_DRAFT, REVIEW_APPROVED, REVIEW_REQUESTED, REVIEW_REPLACED,
                 REVIEW_WAITING.format(n=3), COVERAGE_REQUESTS.format(n=2, m=1),
                 REQUEST_UNREADABLE, REQUEST_NOT_PHOTOGRAPHED.format(name="Concor")):
        assert_no_advice(text)
