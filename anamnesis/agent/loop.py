"""The bounded intake loop: a fixed order of actions, no model picks the next step (SPEC §4)."""

import hashlib
import io

from PIL import Image as PILImage

from anamnesis.agent.crop import crop_region, enlarge_crop
from anamnesis.agent.media import prepare_image
from anamnesis.agent.session import IntakeSession
from anamnesis.core.catalogue import Catalogue
from anamnesis.core.reconcile import reconcile_all
from anamnesis.providers.sam import top_regions
from anamnesis.providers.spark import LabelReading
from anamnesis.schema import ImageRegion, PackObservation, Readability
from anamnesis.schema.report import AgentAction, ReconciliationReport

Image = tuple[bytes, str]
_NEEDS_ZOOM = {Readability.UNREADABLE, Readability.PARTIAL}


def _intake_id(audio: bytes | None, images: list[Image]) -> str:
    digest = hashlib.sha256()
    digest.update(hashlib.sha256(audio).digest() if audio is not None else b"-")
    for data, mime in images:
        digest.update(hashlib.sha256(data).digest() + mime.encode())
    return digest.hexdigest()


Prepared = tuple[Image, tuple[int, int] | None, str]  # photo, size (None if undecodable), its sha256


def _prepare(images: list[Image]) -> list[Prepared]:
    """Each photo prepared, sized and hashed once; an undecodable one keeps its original bytes."""
    prepared = []
    for data, mime in images:
        try:
            photo = prepare_image(data, mime)
            with PILImage.open(io.BytesIO(photo[0])) as decoded:
                size = decoded.size
        except (ValueError, OSError):
            photo, size = (data, mime), None
        prepared.append((photo, size, hashlib.sha256(photo[0]).hexdigest()))
    return prepared


def _segment(
    session: IntakeSession, segmenter, image: Image, sha: str, concepts: tuple[str, ...],
) -> list[ImageRegion]:
    """First concept that returns at least one region wins; SAM only ever sees the source photo."""
    data, mime = image
    for concept in concepts:
        regions = session.call(
            AgentAction.SEGMENT, f"{sha[:12]}:{concept}",
            lambda concept=concept: segmenter.segment(data, concept, mime=mime),
            lambda found: f"{len(found)} regions",
        )
        if regions:
            return regions
    return []


def _read_photo(
    session: IntakeSession, segmenter, reader, prepared: Prepared, concepts: tuple[str, ...], top_k: int,
) -> tuple[list[ImageRegion], list[tuple[Image, ImageRegion, LabelReading]]]:
    """Segment one photo, keep the regions that belong to it, read the best ones, log the rest as dropped."""
    image, size, sha = prepared
    found = _segment(session, segmenter, image, sha, concepts)
    kept = [r for r in found if r.image_sha256 == sha and (r.frame_w, r.frame_h) == size]
    for region in found:
        if region not in kept:  # logged before the reads, so it can't be lost to the budget
            session.note(AgentAction.READ, region.region_id, "error: region does not match the photo")
    readings = []
    for region in top_regions(kept, top_k):
        if session.exhausted:  # budget_exhausted is the last step: no crop, no log
            continue
        try:
            crop = crop_region(image[0], region)
        except ValueError:
            session.note(AgentAction.READ, region.region_id, "error: crop failed")
            continue
        reading = session.call(
            AgentAction.READ, region.region_id,
            lambda crop=crop, region=region: reader.read(crop, region, mime="image/png", cropped=True),
            lambda new: new.readability.value,
        )
        if reading is not None:
            readings.append((image, region, reading))
    return kept, readings


def _zoom(
    session: IntakeSession, reader, image: Image, region: ImageRegion, reading: LabelReading,
) -> LabelReading:
    """One crop-zoom re-read of the source region; keeps the source region id."""
    if session.exhausted:  # budget_exhausted is the last step: no crop, no log
        return reading
    try:
        crop = crop_region(image[0], region)
    except ValueError:
        session.note(AgentAction.ZOOM_READ, region.region_id, "error: crop failed")
        return reading
    enlarged = enlarge_crop(crop)
    if enlarged is None:  # already at the size cap: no zoom, no step, no call
        return reading
    zoomed = session.call(
        AgentAction.ZOOM_READ, region.region_id,
        lambda: reader.read(enlarged, region, mime="image/png", cropped=True),
        lambda new: new.readability.value,
    )
    if zoomed is None:
        return reading
    if zoomed.region_id != region.region_id:  # provenance: a zoom answers for its source region only
        session.note(AgentAction.ZOOM_READ, region.region_id, "error: reading for another region")
        return reading
    return zoomed


def _observation(index: int, reading: LabelReading) -> PackObservation:
    return PackObservation(
        observation_id=f"o{index}", label_text=reading.label_text, inn=reading.inn,
        strength=reading.strength, readability=reading.readability, country=reading.country,
        visual_evidence=[reading.region_id],
    )


def run_intake(
    audio: bytes | None, images: list[Image], *, transcriber, extractor, segmenter, reader,
    catalogue: Catalogue, language_bias: list[str] | None = None, keywords: list[str] | None = None,
    lang_hint: str | None = None, concepts: tuple[str, ...] = ("medicine box", "label"),
    top_k: int = 3, max_provider_calls: int = 12,
) -> ReconciliationReport:
    """Run one patient intake in a fixed order and return the single report artifact."""
    session = IntakeSession(max_provider_calls)
    turns = []
    if audio is not None:
        turns = session.call(
            AgentAction.TRANSCRIBE, "audio",
            lambda: transcriber.transcribe(
                audio, language_bias=language_bias, keywords=keywords, lang_hint=lang_hint),
            lambda found: f"{len(found)} turns",
        ) or []
    claims = []
    if turns:
        claims = session.call(
            AgentAction.EXTRACT_CLAIMS, "turns", lambda: extractor.extract(turns),
            lambda found: f"{len(found)} claims",
        ) or []
    regions: dict[str, ImageRegion] = {}
    readings: list[tuple[Image, ImageRegion, LabelReading]] = []
    photos = _prepare(images)
    for prepared in photos:
        if prepared[1] is None:
            if not session.exhausted:
                session.note(AgentAction.SEGMENT, prepared[2][:12], "error: image cannot be decoded")
            continue
        kept, read = _read_photo(session, segmenter, reader, prepared, concepts, top_k)
        regions.update({region.region_id: region for region in kept})
        readings += read
    final = [
        _zoom(session, reader, image, region, reading) if reading.readability in _NEEDS_ZOOM else reading
        for image, region, reading in readings
    ]
    observations = [_observation(index, reading) for index, reading in enumerate(final)]
    findings = reconcile_all(claims, observations, catalogue)
    if not session.exhausted:
        session.note(AgentAction.RECONCILE, "all", f"{len(findings)} findings")
    return ReconciliationReport(
        intake_id=_intake_id(audio, [photo for photo, _, _ in photos]), turns=turns, claims=claims,
        regions=list(regions.values()),
        observations=observations, findings=findings, steps=session.steps, calls=session.calls,
        spend_usd=session.spend_usd,
    )


__all__ = ["run_intake"]
