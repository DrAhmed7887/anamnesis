"""Deterministic, evidence-linked comparison of claims and packs."""

import re
from decimal import Decimal

from anamnesis.core.catalogue import Catalogue
from anamnesis.schema import (
    INN_ALIASES,
    SALT_BASIS_EQUIVALENTS,
    Finding,
    IngredientAmount,
    PackObservation,
    PatientClaim,
    Release,
    Strength,
    canonical_inn,
    salt_of,
)
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.templates import QUESTION_FOR, TEMPLATES


def _identity(
    strength: Strength | None, inn: str | None, text: str, catalogue: Catalogue,
    country: str | None = None,
) -> tuple[frozenset[str] | None, bool]:
    entry = catalogue.resolve(text, country)
    name_inns = entry.inns if entry else None
    if strength:
        inns = frozenset(_resolve_inn(part.inn, catalogue) for part in strength.ingredients)
        conflict = name_inns is not None and inns != name_inns
        return inns, conflict
    if inn:
        inns = frozenset({_resolve_inn(inn, catalogue)})
        return inns, name_inns is not None and inns != name_inns
    return name_inns, False


def _resolve_inn(name: str, catalogue: Catalogue) -> str:
    """Resolve curated aliases and single-ingredient product names to a moiety."""
    canonical = canonical_inn(name)
    known_moieties = {inn for entry in catalogue.entries for inn in entry.inns}
    if canonical in known_moieties:
        return canonical
    entry = catalogue.resolve(name)
    if entry is not None and len(entry.inns) == 1:
        return next(iter(entry.inns))
    return canonical


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


def _strength_type(
    claim: Strength,
    pack: Strength,
    catalogue: Catalogue,
    nominal_amounts: dict[str, Decimal] | None = None,
) -> D:
    if claim.per != pack.per:
        return D.STRENGTH_MISMATCH
    stated = {_resolve_inn(part.inn, catalogue): _amount(part) for part in claim.ingredients}
    observed = {
        inn: (nominal_amounts[inn], "mg") if nominal_amounts and inn in nominal_amounts else _amount(part)
        for part in pack.ingredients
        if (inn := _resolve_inn(part.inn, catalogue))
    }
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


def _intake_type(
    intake: IngredientAmount,
    pack: Strength,
    splittable: bool | None,
    catalogue: Catalogue,
    nominal_amount: Decimal | None = None,
) -> D:
    if pack.per.value not in {"tablet", "capsule"}:
        return D.INSUFFICIENT_INFORMATION
    stated, stated_unit = _amount(intake)
    observed, observed_unit = (
        (nominal_amount, "mg")
        if nominal_amount is not None
        else _amount(pack.ingredients[0])
    )
    intake_inn = _resolve_inn(intake.inn, catalogue)
    pack_inn = _resolve_inn(pack.ingredients[0].inn, catalogue)
    if intake_inn != pack_inn:
        return D.INSUFFICIENT_INFORMATION
    if stated_unit != observed_unit:
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


def _claim_has_salt(claim: PatientClaim, inn: str, catalogue: Catalogue) -> bool:
    stated = _salts(
        claim.strength,
        catalogue,
        (claim.intake_amount.inn, claim.intake_amount.salt) if claim.intake_amount else None,
        (claim.inn, salt_of(claim.inn)) if claim.inn else None,
    )
    words = f" {re.sub(r'[^\w\s]|_', ' ', claim.name_text.casefold()).strip()} "
    named_salt = any(
        salt and moiety == inn and f" {alias} " in words
        for alias, (moiety, salt) in INN_ALIASES.items()
    )
    return bool(stated.get(inn)) or named_salt


def _nominal_pack_amount(
    claim: PatientClaim, part: IngredientAmount, catalogue: Catalogue
) -> Decimal | None:
    inn = _resolve_inn(part.inn, catalogue)
    if _claim_has_salt(claim, inn, catalogue):
        return None
    amount, unit = _amount(part)
    if unit != "mg":
        return None
    salt = part.salt or salt_of(part.inn)
    return SALT_BASIS_EQUIVALENTS.get((inn, salt, amount)) if salt else None


def _claim_strength_type(claim: PatientClaim, pack: Strength, catalogue: Catalogue) -> D:
    assert claim.strength is not None
    nominal_amounts = {
        _resolve_inn(part.inn, catalogue): nominal
        for part in pack.ingredients
        if (nominal := _nominal_pack_amount(claim, part, catalogue)) is not None
    }
    return _strength_type(claim.strength, pack, catalogue, nominal_amounts)


def _salts(
    strength: Strength | None,
    catalogue: Catalogue,
    *named_salts: tuple[str, str | None] | None,
) -> dict[str, set[str]]:
    """Known salts per canonical ingredient, including name-derived salt facts."""
    salts: dict[str, set[str]] = {}
    if strength:
        for part in strength.ingredients:
            salt = part.salt or salt_of(part.inn)
            if salt:
                salts.setdefault(_resolve_inn(part.inn, catalogue), set()).add(salt)
    for named in named_salts:
        if named is not None:
            name, salt = named
            if salt:
                salts.setdefault(_resolve_inn(name, catalogue), set()).add(salt)
    return salts


def _salts_differ(claim: PatientClaim, pack: PackObservation, catalogue: Catalogue) -> bool:
    stated = _salts(
        claim.strength,
        catalogue,
        (claim.intake_amount.inn, claim.intake_amount.salt) if claim.intake_amount else None,
        (claim.inn, salt_of(claim.inn)) if claim.inn else None,
    )
    observed = _salts(
        pack.strength,
        catalogue,
        (pack.inn, salt_of(pack.inn)) if pack.inn else None,
    )
    return any(
        stated_salt != observed_salt
        for inn in stated.keys() & observed.keys()
        for stated_salt in stated[inn]
        for observed_salt in observed[inn]
    )


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
    claim_release = _release(claim.strength, claim.name_text, catalogue)
    pack_release = _release(pack.strength, pack.label_text or "", catalogue)
    if _salts_differ(claim, pack, catalogue):
        return D.FORMULATION_MISMATCH
    if (
        claim_release is not Release.UNKNOWN
        and pack_release is not Release.UNKNOWN
        and claim_release is not pack_release
    ):
        return D.FORMULATION_MISMATCH
    compared = False
    if claim.strength and pack.strength:
        compared = True
        kind = _claim_strength_type(claim, pack.strength, catalogue)
        if kind is not D.MATCH:
            return kind
    if claim.intake_amount and pack.strength and len(pack.strength.ingredients) == 1:
        compared = True
        pack_part = pack.strength.ingredients[0]
        kind = _intake_type(
            claim.intake_amount,
            pack.strength,
            catalogue.splittable(pack.label_text or ""),
            catalogue,
            _nominal_pack_amount(claim, pack_part, catalogue),
        )
        if kind is not D.MATCH:
            return kind
    if not compared:
        return D.INSUFFICIENT_INFORMATION
    if Release.MODIFIED in {claim_release, pack_release} and Release.UNKNOWN in {
        claim_release,
        pack_release,
    }:
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
    if (
        claim.strength
        and pack.strength
        and _claim_strength_type(claim, pack.strength, catalogue) is D.MATCH
    ):
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
