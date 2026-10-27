"""Deterministic, evidence-linked comparison of claims and packs."""

from decimal import Decimal

from anamnesis.core.catalogue import Catalogue
from anamnesis.core.guardrails import QUESTION_FOR, TEMPLATES
from anamnesis.schema import (
    DiscrepancyType as D,
)
from anamnesis.schema import (
    Finding,
    IngredientAmount,
    PackObservation,
    PatientClaim,
    Strength,
)


def _claim_inns(claim: PatientClaim, catalogue: Catalogue) -> frozenset[str] | None:
    if claim.inn:
        return frozenset({claim.inn.casefold()})
    entry = catalogue.resolve(claim.name_text)
    return frozenset(inn.casefold() for inn in entry.inns) if entry else None


def _pack_inns(pack: PackObservation, catalogue: Catalogue) -> frozenset[str] | None:
    if pack.inn:
        return frozenset({pack.inn.casefold()})
    entry = catalogue.resolve(pack.label_text or "", pack.country)
    return frozenset(inn.casefold() for inn in entry.inns) if entry else None


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
    stated = {part.inn.casefold(): _amount(part) for part in claim.ingredients}
    observed = {part.inn.casefold(): _amount(part) for part in pack.ingredients}
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


def _intake_type(intake: IngredientAmount, pack: Strength) -> D:
    stated, stated_unit = _amount(intake)
    observed, observed_unit = _amount(pack.ingredients[0])
    if stated_unit != observed_unit or intake.inn.casefold() != pack.ingredients[0].inn.casefold():
        return D.STRENGTH_MISMATCH
    ratio = stated / observed
    if ratio == 1:
        return D.MATCH
    if ratio in {Decimal("0.5"), Decimal(2), Decimal(3), Decimal(4)}:
        return D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH
    return D.STRENGTH_MISMATCH


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
    if observation.readability.value != "readable":
        kind = D.UNREADABLE_SOURCE
    else:
        claim_inns = _claim_inns(claim, catalogue)
        pack_inns = _pack_inns(observation, catalogue)
        if claim_inns is None or pack_inns is None:
            kind = D.UNRESOLVED_NAME
        elif claim_inns != pack_inns:
            kind = D.INGREDIENT_MISMATCH
        elif claim.status.value == "discontinued":
            kind = D.DISCONTINUED_BUT_PRESENT
        elif claim.strength and observation.strength:
            kind = _strength_type(claim.strength, observation.strength)
        elif (
            claim.strength is None
            and claim.intake_amount
            and observation.strength
            and len(observation.strength.ingredients) == 1
        ):
            kind = _intake_type(claim.intake_amount, observation.strength)
        else:
            kind = D.MATCH
    return _finding(kind, claim, observation)


def reconcile_all(
    claims: list[PatientClaim], observations: list[PackObservation], catalogue: Catalogue
) -> list[Finding]:
    """Pair by first overlapping INN set, then report each leftover source."""
    findings: list[Finding] = []
    unpaired = set(range(len(observations)))
    for claim in claims:
        claim_inns = _claim_inns(claim, catalogue)
        match = None
        for index, pack in enumerate(observations):
            if index not in unpaired or not claim_inns:
                continue
            pack_inns = _pack_inns(pack, catalogue)
            if pack_inns and claim_inns & pack_inns:
                match = index
                break
        if match is None:
            kind = D.UNRESOLVED_NAME if claim_inns is None else D.MISSING_MODALITY
            findings.append(_finding(kind, claim, None))
        else:
            unpaired.remove(match)
            findings.append(reconcile_pair(claim, observations[match], catalogue))
    for index, pack in enumerate(observations):
        if index not in unpaired:
            continue
        if pack.readability.value != "readable":
            kind = D.UNREADABLE_SOURCE
        elif _pack_inns(pack, catalogue) is None:
            kind = D.UNRESOLVED_NAME
        else:
            kind = D.MISSING_MODALITY
        findings.append(_finding(kind, None, pack))
    return findings
