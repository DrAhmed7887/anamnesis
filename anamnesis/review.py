"""Clinician review: request one new photo, then sign off (SPEC §8, batch 20)."""

from anamnesis.agent.loop import _NEEDS_ZOOM, _intake_id, _observation, _prepare, _read_photo, _zoom
from anamnesis.agent.session import IntakeSession
from anamnesis.core.reconcile import reconcile_all
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.report import AgentAction, AgentStep, ReconciliationReport
from anamnesis.schema.review import PhotoRequest, RequestKind, RequestStatus, Review, ReviewStatus
from anamnesis.schema.templates import REQUEST_NOT_PHOTOGRAPHED, REQUEST_UNREADABLE

Image = tuple[bytes, str]


def _pending_status(requests: list[PhotoRequest]) -> ReviewStatus:
    """Draft when no request is open, otherwise waiting on the patient."""
    if any(item.status is RequestStatus.OPEN for item in requests):
        return ReviewStatus.AWAITING_PATIENT
    return ReviewStatus.DRAFT


def new_review(report: ReconciliationReport) -> Review:
    return Review(intake_id=report.intake_id, status=ReviewStatus.DRAFT, requests=[])


def requestable(report: ReconciliationReport) -> list[tuple[RequestKind, str]]:
    claims = {claim.claim_id: claim for claim in report.claims}
    found = []
    for finding in report.findings:
        if finding.type is D.UNREADABLE_SOURCE and finding.observation_id is not None:
            found.append((RequestKind.UNREADABLE, finding.observation_id))
        elif (
            finding.type is D.MISSING_MODALITY
            and finding.claim_id is not None
            and finding.observation_id is None
            and claims.get(finding.claim_id) is not None
            and claims[finding.claim_id].status.value != "discontinued"
        ):
            found.append((RequestKind.NOT_PHOTOGRAPHED, finding.claim_id))
    return found


def request_photo(review: Review, report: ReconciliationReport, target_id: str) -> Review:
    if review.intake_id != report.intake_id:
        raise ValueError("review is for another report")
    if review.status is ReviewStatus.APPROVED:
        raise ValueError("review is approved")
    kinds = [kind for kind, target in requestable(report) if target == target_id]
    if not kinds:
        raise ValueError("target cannot be requested")
    if any(r.status is RequestStatus.OPEN and r.target_id == target_id for r in review.requests):
        raise ValueError("target already requested")
    made = PhotoRequest(
        request_id=f"r{len(review.requests) + 1}", kind=kinds[0], target_id=target_id,
        status=RequestStatus.OPEN, photo_index=None,
    )
    requests = [*review.requests, made]
    return Review(intake_id=review.intake_id, status=_pending_status(requests), requests=requests)


def withdraw(review: Review, request_id: str) -> Review:
    kept = []
    changed = False
    for item in review.requests:
        if item.request_id == request_id:
            if item.status is not RequestStatus.OPEN:
                raise ValueError("only an open request can be withdrawn")
            kept.append(item.model_copy(update={"status": RequestStatus.WITHDRAWN}))
            changed = True
        else:
            kept.append(item)
    if not changed:
        raise ValueError("unknown request")
    return Review(intake_id=review.intake_id, status=_pending_status(kept), requests=kept)


def request_message(report: ReconciliationReport, request: PhotoRequest) -> str:
    if request.kind is RequestKind.UNREADABLE:
        return REQUEST_UNREADABLE
    for claim in report.claims:
        if claim.claim_id == request.target_id:
            for line in claim.name_text.splitlines():
                if line.strip():
                    return REQUEST_NOT_PHOTOGRAPHED.format(name=line.strip())
            return REQUEST_NOT_PHOTOGRAPHED.format(name="")
    raise ValueError("unknown claim")


def add_photo(
    report: ReconciliationReport, review: Review, request_id: str, photo: Image,
    images: list[Image], audio: Image | None, *, segmenter, reader, catalogue,
    concepts: tuple[str, ...] = ("medicine box", "label"), top_k: int = 3,
    max_provider_calls: int = 8,
) -> tuple[ReconciliationReport, Review]:
    if review.intake_id != report.intake_id:
        raise ValueError("review is for another report")
    wanted = [item for item in review.requests if item.request_id == request_id]
    if not wanted or wanted[0].status is not RequestStatus.OPEN:
        raise ValueError("request is not open")
    (asked,) = wanted
    prepared = _prepare(images)
    audio_bytes = audio[0] if audio is not None else None
    if _intake_id(audio_bytes, [item for item, _, _ in prepared]) != report.intake_id:
        raise ValueError("media do not match the report")
    fresh = _prepare([photo])[0]
    if any(fresh[0][0] == item[0][0] for item in prepared):
        raise ValueError("photo was already given")
    session = IntakeSession(max_provider_calls)
    kept, readings = [], []
    if fresh[1] is None:
        if not session.exhausted:
            session.note(AgentAction.SEGMENT, fresh[2][:12], "error: image cannot be decoded")
    else:
        kept, readings = _read_photo(session, segmenter, reader, fresh, concepts, top_k)
    final = [
        _zoom(session, reader, image, region, reading) if reading.readability in _NEEDS_ZOOM else reading
        for image, region, reading in readings
    ]
    fresh_observations = [
        _observation(len(report.observations) + index, reading)
        for index, reading in enumerate(final)
    ]
    superseded = list(report.superseded)
    if asked.kind is RequestKind.UNREADABLE and fresh_observations and asked.target_id not in superseded:
        superseded.append(asked.target_id)
    together = [*report.observations, *fresh_observations]
    kept_observations = [o for o in together if o.observation_id not in superseded]
    findings = reconcile_all(list(report.claims), kept_observations, catalogue)
    if not session.exhausted:
        session.note(AgentAction.RECONCILE, "all", f"{len(findings)} findings")
    base = len(report.steps)
    steps = [*report.steps, *(
        AgentStep(n=base + index, action=step.action, target=step.target, outcome=step.outcome,
                  call_ids=list(step.call_ids))
        for index, step in enumerate(session.steps)
    )]
    fresh_intake = _intake_id(audio_bytes, [item for item, _, _ in prepared] + [fresh[0]])
    regions = {region.region_id: region for region in report.regions}
    regions.update({region.region_id: region for region in kept})
    updated = ReconciliationReport(
        intake_id=fresh_intake, turns=list(report.turns), claims=list(report.claims),
        regions=list(regions.values()), observations=[*report.observations, *fresh_observations],
        findings=findings, steps=steps, calls=report.calls + session.calls,
        spend_usd=report.spend_usd + session.spend_usd, superseded=superseded,
    )
    answered = [
        item.model_copy(update={"status": RequestStatus.ANSWERED, "photo_index": len(images) + 1})
        if item.request_id == request_id else item
        for item in review.requests
    ]
    return updated, Review(intake_id=fresh_intake, status=_pending_status(answered), requests=answered)


def approve(review: Review, report: ReconciliationReport) -> Review:
    if review.intake_id != report.intake_id:
        raise ValueError("review is for another report")
    if any(r.status is RequestStatus.OPEN for r in review.requests):
        raise ValueError("an open request remains")
    return Review(intake_id=review.intake_id, status=ReviewStatus.APPROVED,
                  requests=list(review.requests))
