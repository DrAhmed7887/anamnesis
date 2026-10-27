"""Edge cases for the curated salt aliases (reviewer-written: Sol hit its rate limit mid-batch)."""

from decimal import Decimal

from anamnesis.core.catalogue import load_catalogue
from anamnesis.schema import INN_ALIASES, IngredientAmount, canonical_inn


def test_every_alias_targets_a_catalogue_moiety() -> None:
    moieties = {inn for entry in load_catalogue().entries for inn in entry.inns}
    assert {target for target, _ in INN_ALIASES.values()} <= moieties


def test_catalogue_resolves_salt_names_and_synonyms() -> None:
    cat = load_catalogue()
    assert cat.resolve("Metformin hydrochloride 850 mg").inns == frozenset({"metformin"})
    assert cat.resolve("acetaminophen 500").inns == frozenset({"paracetamol"})


def test_salt_names_never_imply_a_brand_release() -> None:
    from anamnesis.schema import Release

    assert load_catalogue().implied_release("metoprolol succinate 100 mg") is Release.UNKNOWN


def test_case_and_whitespace_are_ignored() -> None:
    assert canonical_inn("  METOPROLOL Succinate ") == "metoprolol"
    a = IngredientAmount(inn=" Bisoprolol FUMARATE", amount=Decimal(5), unit="mg")
    assert (a.inn, a.salt) == ("bisoprolol", "fumarate")
