"""The bounded intake loop: a fixed order of actions, no model picks the next step (SPEC §4)."""

import hashlib

from anamnesis.agent.crop import crop_region
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


def _segment(session: IntakeSession, segmenter, image: Image, concepts: tuple[str, ...]) -> list[ImageRegion]:
    """First concept that returns at least one region wins; SAM only ever sees the source photo."""
    data, mime = image
    for concept in concepts:
        regions = session.call(
            AgentAction.SEGMENT, f"{hashlib.sha256(data).hexdigest()[:12]}:{concept}",
            lambda concept=concept: segmenter.segment(data, concept, mime=mime),
            lambda found: f"{len(found)} regions",
        )
        if regions:
            return regions
    return []


def _zoom(
    session: IntakeSession, reader, image: Image, region: ImageRegion, reading: LabelReading,
) -> LabelReading:
    """One crop-zoom re-read of the source region; keeps the source region id."""
    try:
        crop = crop_region(image[0], region)
    except ValueError:
        session.note(AgentAction.ZOOM_READ, region.region_id, "error: crop failed")
        return reading
    zoomed = session.call(
        AgentAction.ZOOM_READ, region.region_id,
        lambda: reader.read(crop, region, mime="image/png", cropped=True),
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
    for image in images:
        found = _segment(session, segmenter, image, concepts)
        regions.update({region.region_id: region for region in found})
        for region in top_regions(found, top_k):
            reading = session.call(
                AgentAction.READ, region.region_id,
                lambda image=image, region=region: reader.read(image[0], region, mime=image[1]),
                lambda new: new.readability.value,
            )
            if reading is not None:
                readings.append((image, region, reading))
    final = [
        _zoom(session, reader, image, region, reading) if reading.readability in _NEEDS_ZOOM else reading
        for image, region, reading in readings
    ]
    observations = [_observation(index, reading) for index, reading in enumerate(final)]
    findings = reconcile_all(claims, observations, catalogue)
    if not session.exhausted:
        session.note(AgentAction.RECONCILE, "all", f"{len(findings)} findings")
    return ReconciliationReport(
        intake_id=_intake_id(audio, images), turns=turns, claims=claims, regions=list(regions.values()),
        observations=observations, findings=findings, steps=session.steps, calls=session.calls,
        spend_usd=session.spend_usd,
    )


__all__ = ["run_intake"]
