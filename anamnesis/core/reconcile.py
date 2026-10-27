"""Deterministic, evidence-linked comparison of claims and packs."""

from decimal import Decimal

from anamnesis.core.catalogue import Catalogue
from anamnesis.schema import (
    DiscrepancyType as D,
)
from anamnesis.schema import (
    Finding,
    IngredientAmount,
    PackObservation,
    PatientClaim,
    Release,
    Strength,
    canonical_inn,
)
from anamnesis.schema.templates import QUESTION_FOR, TEMPLATES


def _identity(
    strength: Strength | None, inn: str | None, text: str, catalogue: Catalogue,
    country: str | None = None,
) -> tuple[frozenset[str] | None, bool]:
    entry = catalogue.resolve(text, country)
    if strength:
        inns = frozenset(canonical_inn(part.inn) for part in strength.ingredients)
        return inns, entry is not None and inns != entry.inns
    if inn:
        return frozenset({canonical_inn(inn)}), False
    return (entry.inns if entry else None), False


def _claim_identity(claim: PatientClaim, catalogue: Catalogue) -> tuple[frozenset[str] | None, bool]:
    return _identity(claim.strength, claim.inn, claim.name_text, catalogue)


def _pack_identity(pack: PackObservation, catalogue: Catalogue) -> tuple[frozenset[str] | None, bool]:
    return _identity(pack.strength, pack.inn, pack.label_text or "", catalogue, pack.country)


def _amount(ingredient: IngredientAmount) -> tuple[Decimal, str]:
    amount = ingredient.amount
    unit = ingredient.unit.value
    if unit == "g":
        return amount * Decimal(1000), "mg"
    if unit == "mcg":
        return amount * Decimal("0.001"), "mg"
    return amount, unit


def _strength_type(claim: Strength, pack: Strength) -> D:
    if claim.per != pack.per:
        return D.STRENGTH_MISMATCH
    stated = {canonical_inn(part.inn): _amount(part) for part in claim.ingredients}
    observed = {canonical_inn(part.inn): _amount(part) for part in pack.ingredients}
    if stated == observed:
        return D.MATCH
    if stated.keys() != observed.keys():
        return D.STRENGTH_MISMATCH
    if any(stated[inn][1] != observed[inn][1] for inn in stated):
        return D.STRENGTH_MISMATCH
    if len(stated) > 1:
        ratios = {stated[inn][0] / observed[inn][0] for inn in stated}
        if len(ratios) > 1:
            return D.RATIO_MISMATCH
    return D.STRENGTH_MISMATCH


def _intake_type(intake: IngredientAmount, pack: Strength, splittable: bool | None) -> D:
    if pack.per.value not in {"tablet", "capsule"}:
        return D.INSUFFICIENT_INFORMATION
    stated, stated_unit = _amount(intake)
    observed, observed_unit = _amount(pack.ingredients[0])
    if stated_unit != observed_unit or canonical_inn(intake.inn) != canonical_inn(pack.ingredients[0].inn):
        return D.STRENGTH_MISMATCH
    ratio = stated / observed
    if ratio == 1:
        return D.MATCH
    if ratio in {Decimal(2), Decimal(3), Decimal(4)}:
        return D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH
    if ratio == Decimal("0.5"):
        if pack.per.value == "capsule" or splittable is False:
            return D.STRENGTH_MISMATCH
        if splittable is None:
            return D.INSUFFICIENT_INFORMATION
        return D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH
    return D.STRENGTH_MISMATCH


def _release(strength: Strength | None, text: str, catalogue: Catalogue) -> Release:
    if strength and strength.release is not Release.UNKNOWN:
        return strength.release
    return catalogue.implied_release(text)


def _finding(kind: D, claim: PatientClaim | None, pack: PackObservation | None) -> Finding:
    return Finding(
        finding_id=f"{claim.claim_id if claim else '-'}:{pack.observation_id if pack else '-'}",
        type=kind,
        claim_id=claim.claim_id if claim else None,
        observation_id=pack.observation_id if pack else None,
        audio_evidence=list(claim.audio_evidence) if claim else [],
        visual_evidence=list(pack.visual_evidence) if pack else [],
        needs_clinician_review=kind is not D.MATCH,
        clinician_note=TEMPLATES[kind],
        patient_question_id=QUESTION_FOR[kind],
    )


def reconcile_pair(claim: PatientClaim, observation: PackObservation, catalogue: Catalogue) -> Finding:
    """Apply the first matching SPEC §3 rule to a claim and a pack."""
    return _finding(_pair_type(claim, observation, catalogue), claim, observation)


def _pair_type(claim: PatientClaim, pack: PackObservation, catalogue: Catalogue) -> D:
    if pack.readability.value != "readable":
        return D.UNREADABLE_SOURCE
    claim_inns, claim_conflict = _claim_identity(claim, catalogue)
    pack_inns, pack_conflict = _pack_identity(pack, catalogue)
    if claim_inns is None or pack_inns is None:
        return D.UNRESOLVED_NAME
    if claim_conflict or pack_conflict:
        return D.INSUFFICIENT_INFORMATION
    if claim_inns != pack_inns:
        return D.INGREDIENT_MISMATCH
    if claim.status.value == "discontinued":
        return D.DISCONTINUED_BUT_PRESENT
    compared = False
    if claim.strength and pack.strength:
        compared = True
        kind = _strength_type(claim.strength, pack.strength)
        if kind is not D.MATCH:
            return kind
    if claim.intake_amount and pack.strength and len(pack.strength.ingredients) == 1:
        compared = True
        kind = _intake_type(claim.intake_amount, pack.strength, catalogue.splittable(pack.label_text or ""))
        if kind is not D.MATCH:
            return kind
    if not compared:
        return D.INSUFFICIENT_INFORMATION
    claim_release = _release(claim.strength, claim.name_text, catalogue)
    pack_release = _release(pack.strength, pack.label_text or "", catalogue)
    if claim_release is not Release.UNKNOWN and pack_release is not Release.UNKNOWN:
        if claim_release is not pack_release:
            return D.FORMULATION_MISMATCH
    elif Release.MODIFIED in {claim_release, pack_release}:
        return D.INSUFFICIENT_INFORMATION
    return D.MATCH


def _pair_score(claim: PatientClaim, pack: PackObservation, catalogue: Catalogue) -> int:
    if pack.readability.value != "readable":
        return 0
    claim_inns, _ = _claim_identity(claim, catalogue)
    pack_inns, _ = _pack_identity(pack, catalogue)
    if not claim_inns or not pack_inns or not claim_inns & pack_inns:
        return 0
    if claim_inns != pack_inns:
        return 1
    if claim.strength and pack.strength and _strength_type(claim.strength, pack.strength) is D.MATCH:
        return 3
    return 2


def reconcile_all(
    claims: list[PatientClaim], observations: list[PackObservation], catalogue: Catalogue
) -> list[Finding]:
    """Pair readable, overlapping products by score with stable ID tie breaks."""
    candidates = [
        (-score, claim.claim_id, pack.observation_id, ci, pi)
        for ci, claim in enumerate(claims)
        for pi, pack in enumerate(observations)
        if (score := _pair_score(claim, pack, catalogue))
    ]
    paired_claims: set[int] = set()
    paired_packs: set[int] = set()
    findings: list[Finding] = []
    for _, _, _, ci, pi in sorted(candidates):
        if ci not in paired_claims and pi not in paired_packs:
            paired_claims.add(ci)
            paired_packs.add(pi)
            findings.append(reconcile_pair(claims[ci], observations[pi], catalogue))
    for ci, claim in enumerate(claims):
        if ci not in paired_claims:
            kind = D.UNRESOLVED_NAME if _claim_identity(claim, catalogue)[0] is None else D.MISSING_MODALITY
            findings.append(_finding(kind, claim, None))
    for pi, pack in enumerate(observations):
        if pi in paired_packs:
            continue
        if pack.readability.value != "readable":
            kind = D.UNREADABLE_SOURCE
        elif _pack_identity(pack, catalogue)[0] is None:
            kind = D.UNRESOLVED_NAME
        else:
            kind = D.MISSING_MODALITY
        findings.append(_finding(kind, None, pack))
    return sorted(findings, key=lambda finding: finding.finding_id)
