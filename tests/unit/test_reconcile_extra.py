"""Edge cases for the deterministic reconciliation rules."""

from decimal import Decimal

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all, reconcile_pair
from anamnesis.schema import (
    DiscrepancyType as D,
)
from anamnesis.schema import IngredientAmount, PackObservation, PatientClaim, Strength


def amount(inn: str, value: str, unit: str = "mg") -> IngredientAmount:
    return IngredientAmount(inn=inn, amount=Decimal(value), unit=unit)


def claim(name: str, *ingredients: IngredientAmount, status: str = "active") -> PatientClaim:
    strength = Strength(ingredients=list(ingredients), per="tablet") if ingredients else None
    return PatientClaim(
        claim_id="c", name_text=name, strength=strength, status=status, audio_evidence=["turn"]
    )


def pack(label: str | None, *ingredients: IngredientAmount, readability: str = "readable") -> PackObservation:
    strength = Strength(ingredients=list(ingredients), per="tablet") if ingredients else None
    return PackObservation(
        observation_id="o", label_text=label, strength=strength, readability=readability,
        visual_evidence=["region"],
    )


def test_unreadable_precedes_unresolved_and_discontinued() -> None:
    result = reconcile_pair(
        claim("unknown", status="discontinued"), pack(None, readability="partial"), load_catalogue()
    )
    assert result.type is D.UNREADABLE_SOURCE


def test_catalogue_matches_only_whole_words_and_longest_brand() -> None:
    catalogue = load_catalogue()
    assert catalogue.resolve("SuperConcor") is None
    assert catalogue.resolve("Panadol Extra® 500/65").inns == frozenset({"paracetamol", "caffeine"})


def test_combination_ratio_is_independent_of_order_and_uses_exact_decimals() -> None:
    catalogue = load_catalogue()
    c = claim("Augmentin", amount("amoxicillin", "0.875", "g"), amount("clavulanic acid", "125"))
    o = pack("Augmentin", amount("clavulanic acid", "125"), amount("amoxicillin", "875"))
    assert reconcile_pair(c, o, catalogue).type is D.MATCH
    other = pack("Augmentin", amount("clavulanic acid", "125"), amount("amoxicillin", "500"))
    assert reconcile_pair(c, other, catalogue).type is D.RATIO_MISMATCH


def test_unresolved_one_sided_claim_copies_evidence() -> None:
    result = reconcile_all([claim("unknown")], [], load_catalogue())[0]
    assert result.type is D.UNRESOLVED_NAME
    assert result.finding_id == "c:-"
    assert result.audio_evidence == ["turn"]
    assert result.visual_evidence == []


def test_country_outside_catalogue_still_resolves() -> None:
    # Reviewer fix: an Egyptian pack must not become unresolved just because EG isn't listed.
    entry = load_catalogue().resolve("Concor 5 mg", country="EG")
    assert entry is not None and entry.inns == frozenset({"bisoprolol"})
