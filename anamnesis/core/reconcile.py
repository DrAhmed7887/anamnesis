"""Deterministic, evidence-linked comparison of claims and packs."""

import re
from decimal import Decimal

from anamnesis.core.catalogue import Catalogue, normalise
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
    ambiguous = entry is None and catalogue.is_ambiguous(text)
    name_inns = entry.inns if entry else None
    if strength:
        inns = frozenset(_resolve_inn(part.inn, catalogue) for part in strength.ingredients)
        conflict = ambiguous or (name_inns is not None and inns != name_inns)
        if inn and _resolve_inn(inn, catalogue) not in inns:
            conflict = True
        return inns, conflict
    if inn:
        inns = frozenset({_resolve_inn(inn, catalogue)})
        return inns, ambiguous or (name_inns is not None and inns != name_inns)
    if ambiguous:
        return None, True
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


_ACCEPTED_RATIOS = frozenset({Decimal(1), Decimal("0.5"), Decimal(2), Decimal(3), Decimal(4)})


def _strength_basis(stated: Decimal, literal: Decimal, nominal: Decimal | None) -> Decimal:
    """Pack amount for a stated strength: exact, so the literal or the nominal amount, never a multiple."""
    return stated if stated in (literal, nominal) else literal


def _basis_amount(stated: Decimal, literal: Decimal, nominal: Decimal | None) -> Decimal:
    """Pack amount for an intake: the literal one if a dose multiple explains it, else the nominal one."""
    if nominal is None or literal == 0 or stated / literal in _ACCEPTED_RATIOS:
        return literal
    return nominal


def _strength_type(
    claim: Strength,
    pack: Strength,
    catalogue: Catalogue,
    nominal_amounts: dict[str, Decimal] | None = None,
) -> D:
    if claim.per != pack.per:
        return D.STRENGTH_MISMATCH
    stated = {_resolve_inn(part.inn, catalogue): _amount(part) for part in claim.ingredients}
    observed = {}
    for part in pack.ingredients:
        inn = _resolve_inn(part.inn, catalogue)
        literal, unit = _amount(part)
        nominal = (nominal_amounts or {}).get(inn)
        if inn in stated and nominal is not None and unit == "mg":
            literal = _strength_basis(stated[inn][0], literal, nominal)
        observed[inn] = (literal, unit)
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
    observed, observed_unit = _amount(pack.ingredients[0])
    if nominal_amount is not None:
        observed = _basis_amount(stated, observed, nominal_amount)
    intake_inn = _resolve_inn(intake.inn, catalogue)
    pack_inn = _resolve_inn(pack.ingredients[0].inn, catalogue)
    if intake_inn != pack_inn:
        return D.INSUFFICIENT_INFORMATION
    if stated_unit != observed_unit:
        return D.STRENGTH_MISMATCH
    return _dose_ratio_type(stated / observed, pack.per.value, splittable)


def _dose_ratio_type(ratio: Decimal, per: str, splittable: bool | None) -> D:
    """Map an intake-to-unit ratio to a finding (SPEC §3 rule 8)."""
    if ratio == 1:
        return D.MATCH
    if ratio in {Decimal(2), Decimal(3), Decimal(4)}:
        return D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH
    if ratio == Decimal("0.5"):
        if per == "capsule" or splittable is False:
            return D.STRENGTH_MISMATCH
        if splittable is None:
            return D.INSUFFICIENT_INFORMATION
        return D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH
    return D.STRENGTH_MISMATCH


def _units_type(units: Decimal, pack: Strength, splittable: bool | None) -> D:
    """Map tablets-per-intake against one pack unit (SPEC §3 rule 8, batch 17)."""
    if pack.per.value not in {"tablet", "capsule"}:
        return D.INSUFFICIENT_INFORMATION
    return _dose_ratio_type(units, pack.per.value, splittable)


def _claim_has_salt(claim: PatientClaim, inn: str, catalogue: Catalogue) -> bool:
    return bool(_claim_salts(claim, catalogue).get(inn))


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


def _text_salts(text: str, catalogue: Catalogue) -> list[tuple[str, str]]:
    """(moiety, salt) pairs for curated salt aliases and loose salt words in free text."""
    padded = f" {normalise(text)} "
    found = {
        normalise(alias): target
        for alias, target in INN_ALIASES.items()
        if target[1] and f" {normalise(alias)} " in padded
    }
    pairs = {
        (_resolve_inn(moiety, catalogue), salt)
        for alias, (moiety, salt) in found.items()
        if not any(alias != other and f" {alias} " in f" {other} " for other in found)
    }
    pairs.update(_loose_salts(text, padded, catalogue))
    return sorted(pairs)


def _loose_salts(text: str, padded: str, catalogue: Catalogue) -> set[tuple[str, str]]:
    """Curated salt words that sit apart from the moiety, when the text names the moiety or its brand."""
    present = {
        (moiety, normalise(salt))
        for moiety, salt in INN_ALIASES.values()
        if salt and f" {normalise(salt)} " in padded and catalogue.mentions_moiety(text, moiety)
    }
    return {
        (moiety, salt)
        for moiety, salt in present
        if not any(m == moiety and salt != other and f" {salt} " in f" {other} " for m, other in present)
    }


def _side_salts(
    strength: Strength | None,
    intake: IngredientAmount | None,
    inn: str | None,
    text: str,
    catalogue: Catalogue,
) -> dict[str, frozenset[str]]:
    """Known salts per canonical ingredient from strength, intake, scalar inn and free text."""
    parts = list(strength.ingredients) if strength else []
    parts.extend([intake] if intake else [])
    pairs = [(_resolve_inn(part.inn, catalogue), part.salt or salt_of(part.inn)) for part in parts]
    if inn:
        pairs.append((_resolve_inn(inn, catalogue), salt_of(inn)))
    pairs.extend(_text_salts(text, catalogue))
    salts: dict[str, set[str]] = {}
    for moiety, salt in pairs:
        if salt:
            salts.setdefault(moiety, set()).add(salt)
    return {moiety: frozenset(found) for moiety, found in salts.items()}


def _claim_salts(claim: PatientClaim, catalogue: Catalogue) -> dict[str, frozenset[str]]:
    return _side_salts(claim.strength, claim.intake_amount, claim.inn, claim.name_text, catalogue)


def _pack_salts(pack: PackObservation, catalogue: Catalogue) -> dict[str, frozenset[str]]:
    return _side_salts(pack.strength, None, pack.inn, pack.label_text or "", catalogue)


def _salt_conflict(claim: PatientClaim, pack: PackObservation, catalogue: Catalogue) -> bool:
    """One side names two different salts of one ingredient: extraction conflict."""
    sides = (_claim_salts(claim, catalogue), _pack_salts(pack, catalogue))
    return any(len(found) > 1 for side in sides for found in side.values())


def _salts_differ(claim: PatientClaim, pack: PackObservation, catalogue: Catalogue) -> bool:
    stated = _claim_salts(claim, catalogue)
    observed = _pack_salts(pack, catalogue)
    return any(
        stated_salt != observed_salt
        for inn in stated.keys() & observed.keys()
        for stated_salt in stated[inn]
        for observed_salt in observed[inn]
    )


def _release(
    strength: Strength | None, text: str, catalogue: Catalogue, country: str | None = None
) -> Release:
    if strength and strength.release is not Release.UNKNOWN:
        return strength.release
    return catalogue.implied_release(text, country)


_RELEASE_WORDS = frozenset({
    "retard", "depot", "xr", "xl", "sr", "er", "cr", "mr", "prolonged", "extended",
    "modified", "sustained", "controlled", "slow", "immediate", "ممتد", "بطيء",
})

_ARABIC_RELEASE_WORDS = frozenset({"ممتد", "بطيء"})
_RELEASE_CLITICS = r"(?:وال|بال|فال|لل|ال|و|ف|ب|ل)?"


def _says_release(normalised: str) -> bool:
    """A curated release word said as a whole word; Arabic words accept attached clitics."""
    if any(f" {word} " in f" {normalised} " for word in _RELEASE_WORDS - _ARABIC_RELEASE_WORDS):
        return True
    return any(
        re.search(rf"(?<!\w){_RELEASE_CLITICS}{re.escape(word)}(?!\w)", normalised)
        for word in _ARABIC_RELEASE_WORDS
    )


def _claim_release(
    claim: PatientClaim, catalogue: Catalogue, pack_release: Release,
) -> Release:
    """A claim's explicit release counts when the claim says so (SPEC §3, C8).

    An unsaid release that agrees with the pack is not trusted: it would
    manufacture a match, so the brand-implied release is used instead. An
    unsaid release that disagrees with the pack still flags a conflict.
    """
    strength = claim.strength
    if strength and strength.release is not Release.UNKNOWN:
        said = _says_release(normalise(claim.name_text))
        if said or catalogue.matches_brand(claim.name_text) or strength.release is not pack_release:
            return strength.release
    return catalogue.implied_release(claim.name_text)


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


def _units_check(claim: PatientClaim, pack: PackObservation, catalogue: Catalogue) -> D | None:
    """Tablets-per-intake against one pack unit (SPEC §3 rule 8, C1).

    Runs after rule 7 found equal strengths (an early return otherwise) or when
    the claim states no strength. Returns None when it does not apply, or when
    the units agree: units never produce a match and never count for rule 9.
    """
    units = claim.regimen.units_per_intake if claim.regimen else None
    if pack.strength is None or units is None or units == 1:
        return None
    kind = _units_type(units, pack.strength, catalogue.splittable(pack.label_text or "", pack.country))
    return kind if kind is not D.MATCH else None


def _pair_type(claim: PatientClaim, pack: PackObservation, catalogue: Catalogue) -> D:
    if pack.readability.value != "readable":
        return D.UNREADABLE_SOURCE
    claim_inns, claim_conflict = _claim_identity(claim, catalogue)
    pack_inns, pack_conflict = _pack_identity(pack, catalogue)
    if claim_inns is None or pack_inns is None:
        return D.UNRESOLVED_NAME
    if claim_conflict or pack_conflict or _salt_conflict(claim, pack, catalogue):
        return D.INSUFFICIENT_INFORMATION
    if claim_inns != pack_inns:
        return D.INGREDIENT_MISMATCH
    if claim.status.value == "discontinued":
        return D.DISCONTINUED_BUT_PRESENT
    pack_release = _release(pack.strength, pack.label_text or "", catalogue, pack.country)
    claim_release = _claim_release(claim, catalogue, pack_release)
    if _salts_differ(claim, pack, catalogue):
        return D.FORMULATION_MISMATCH
    releases = {claim_release, pack_release}
    if Release.UNKNOWN not in releases and claim_release is not pack_release:
        return D.FORMULATION_MISMATCH
    compared = False
    if claim.strength and pack.strength:
        compared = True
        kind = _claim_strength_type(claim, pack.strength, catalogue)
        if kind is not D.MATCH:
            return kind
    if claim.intake_amount and pack.strength and len(pack.strength.ingredients) > 1:
        return D.INSUFFICIENT_INFORMATION
    if claim.intake_amount and pack.strength:
        compared = True
        pack_part = pack.strength.ingredients[0]
        kind = _intake_type(
            claim.intake_amount,
            pack.strength,
            catalogue.splittable(pack.label_text or "", pack.country),
            catalogue,
            _nominal_pack_amount(claim, pack_part, catalogue),
        )
        if kind is not D.MATCH:
            return kind
    units_kind = _units_check(claim, pack, catalogue)
    if units_kind is not None:
        return units_kind
    if not compared:
        return D.INSUFFICIENT_INFORMATION
    if Release.MODIFIED in releases and Release.UNKNOWN in releases:
        return D.INSUFFICIENT_INFORMATION
    return D.MATCH


def _pair_score(claim: PatientClaim, pack: PackObservation, catalogue: Catalogue) -> int:
    if pack.readability.value != "readable":
        return 0
    claim_inns, claim_conflict = _claim_identity(claim, catalogue)
    pack_inns, pack_conflict = _pack_identity(pack, catalogue)
    if not claim_inns or not pack_inns or not claim_inns & pack_inns:
        return 0
    if claim_inns != pack_inns or claim_conflict or pack_conflict or _salt_conflict(claim, pack, catalogue):
        return 1  # a conflicted candidate never outranks a clean one
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
