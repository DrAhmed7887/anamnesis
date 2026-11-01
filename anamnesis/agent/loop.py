"""The bounded intake loop: a fixed order of actions, no model picks the next step (SPEC §4)."""

import hashlib
import io

from PIL import Image as PILImage

from anamnesis.agent.crop import crop_region, enlarge_crop
from anamnesis.agent.media import prepare_image
from anamnesis.agent.session import IntakeSession
from anamnesis.core.catalogue import Catalogue
from anamnesis.core.reconcile import _split_inn_parts, reconcile_all
from anamnesis.providers.sam import top_regions
from anamnesis.providers.spark import LabelReading
from anamnesis.schema import ImageRegion, PackObservation, Readability, Release, canonical_inn, salt_of
from anamnesis.schema.report import AgentAction, ReconciliationReport

Image = tuple[bytes, str]
SAM_CONCEPTS = ("medicine box", "label", "package")
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


def _checked_prepared(
    report: ReconciliationReport, images: list[Image], audio: Image | None,
) -> list[Prepared]:
    """The loop's own prepared photos, refusing media the report wasn't made from."""
    prepared = _prepare(images)
    audio_bytes = audio[0] if audio is not None else None
    want = _intake_id(audio_bytes, [photo for photo, _, _ in prepared])
    if want != report.intake_id:
        raise ValueError("media do not match the report")
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


def _named_ingredients(reading: LabelReading) -> frozenset[str] | None:
    """Canonical INNs the reading names, or None when it names nothing (SPEC §4 step 5b)."""
    if reading.strength is not None:
        return frozenset(canonical_inn(part.inn) for part in reading.strength.ingredients)
    if reading.inn is not None:
        return frozenset(canonical_inn(part) for part in _split_inn_parts(reading.inn))
    return None


def _strength_key(strength) -> tuple:
    """Ingredient, amount, unit and per; release is a separate check (SPEC §4 step 5b)."""
    return (
        strength.per.value,
        frozenset(
            (canonical_inn(part.inn), part.amount, part.unit.value) for part in strength.ingredients
        ),
    )


def _salts(reading: LabelReading) -> dict[str, frozenset[str]]:
    """Known salts per canonical ingredient, from amount salts and salts in inns."""
    salts: dict[str, set[str]] = {}
    if reading.strength is not None:
        for part in reading.strength.ingredients:
            found = salts.setdefault(canonical_inn(part.inn), set())
            if part.salt is not None:
                found.add(part.salt)
            inferred = salt_of(part.inn)
            if inferred is not None:
                found.add(inferred)
    if reading.inn is not None:
        for part in _split_inn_parts(reading.inn):
            inferred = salt_of(part)
            if inferred is not None:
                salts.setdefault(canonical_inn(part), set()).add(inferred)
    return {inn: frozenset(found) for inn, found in salts.items() if found}


def _second_read(
    session: IntakeSession, second_reader, image: Image, region: ImageRegion,
    reading: LabelReading,
) -> LabelReading:
    """One second-model re-read of the first read's crop; a readable agreement replaces the first."""
    if second_reader is None or reading.readability not in _NEEDS_ZOOM:
        return reading
    if session.exhausted:  # budget_exhausted is the last step: no crop, no log
        return reading
    try:
        crop = crop_region(image[0], region)
    except ValueError:
        session.note(AgentAction.SECOND_READ, region.region_id, "error: crop failed")
        return reading
    second = session.call(
        AgentAction.SECOND_READ, region.region_id,
        lambda: second_reader.read(crop, region, mime="image/png", cropped=True),
        lambda new: new.readability.value,
    )
    if second is None:
        return reading
    if second.region_id != region.region_id:
        session.note(AgentAction.SECOND_READ, region.region_id, "error: reading for another region")
        return reading
    if second.readability is not Readability.READABLE:
        return reading
    first_names, second_names = _named_ingredients(reading), _named_ingredients(second)
    if first_names is not None and second_names != first_names:
        session.note(AgentAction.SECOND_READ, region.region_id, "conflict: kept the first reading")
        return reading
    if reading.strength is not None:
        if second.strength is None:
            session.note(AgentAction.SECOND_READ, region.region_id, "conflict: kept the first reading")
            return reading
        if _strength_key(reading.strength) != _strength_key(second.strength):
            session.note(AgentAction.SECOND_READ, region.region_id, "conflict: kept the first reading")
            return reading
        if (
            reading.strength.release is not Release.UNKNOWN
            and second.strength.release != reading.strength.release
        ):
            session.note(AgentAction.SECOND_READ, region.region_id, "conflict: kept the first reading")
            return reading
    first_salts, second_salts = _salts(reading), _salts(second)
    for inn, first_set in first_salts.items():
        if second_salts.get(inn, frozenset()) != first_set:
            session.note(AgentAction.SECOND_READ, region.region_id, "conflict: kept the first reading")
            return reading
    return second


def _observation(index: int, reading: LabelReading) -> PackObservation:
    return PackObservation(
        observation_id=f"o{index}", label_text=reading.label_text, inn=reading.inn,
        strength=reading.strength, readability=reading.readability, country=reading.country,
        visual_evidence=[reading.region_id],
    )


def run_intake(
    audio: bytes | None, images: list[Image], *, transcriber, extractor, segmenter, reader,
    catalogue: Catalogue, language_bias: list[str] | None = None, keywords: list[str] | None = None,
    lang_hint: str | None = None, concepts: tuple[str, ...] = SAM_CONCEPTS,
    top_k: int = 3, max_provider_calls: int | None = None, second_reader=None,
) -> ReconciliationReport:
    """Run one patient intake in a fixed order and return the single report artifact."""
    if max_provider_calls is None:
        per_region = 3 * top_k if second_reader is not None else 2 * top_k
        max_provider_calls = 2 + (len(concepts) + per_region) * len(images)
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
    final = []
    for image, region, reading in readings:
        if reading.readability in _NEEDS_ZOOM:
            reading = _zoom(session, reader, image, region, reading)
            reading = _second_read(session, second_reader, image, region, reading)
        final.append(reading)
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


__all__ = ["SAM_CONCEPTS", "run_intake"]
