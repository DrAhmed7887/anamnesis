"""Regression coverage for live brand-name claim extraction errors."""

from decimal import Decimal

import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_pair
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import IngredientAmount, PackObservation, PatientClaim, Strength


@pytest.mark.parametrize("text", ["BelocZok", "beloczok 100 mg", "Beloc Zok", "Beloc-Zok"])
def test_joined_brand_name_resolves_as_a_whole_word(text: str) -> None:
    entry = load_catalogue().resolve(text)
    assert entry is not None and entry.inns == frozenset({"metoprolol"})


@pytest.mark.parametrize("text", ["beloczokx", "Belo", "Zok"])
def test_joined_brand_name_keeps_whole_word_boundaries(text: str) -> None:
    assert load_catalogue().resolve(text) is None


def _amount(inn: str) -> IngredientAmount:
    return IngredientAmount(inn=inn, amount=Decimal("5"), unit="mg")


def _claim(intake_inn: str) -> PatientClaim:
    return PatientClaim(
        claim_id="c1",
        name_text="Concor",
        intake_amount=_amount(intake_inn),
        status="active",
        audio_evidence=["t1"],
    )


def _pack() -> PackObservation:
    return PackObservation(
        observation_id="o1",
        label_text="Concor 5 mg",
        strength=Strength(ingredients=[_amount("bisoprolol")], per="tablet"),
        readability="readable",
        visual_evidence=["r1"],
    )


def test_brand_in_intake_resolves_to_the_pack_ingredient() -> None:
    assert reconcile_pair(_claim("Concor"), _pack(), load_catalogue()).type is D.MATCH


@pytest.mark.parametrize("intake_inn", ["Lipitor", "Xyzzol"])
def test_mismatched_or_unresolved_intake_ingredient_is_extraction_conflict(intake_inn: str) -> None:
    assert reconcile_pair(_claim(intake_inn), _pack(), load_catalogue()).type is D.INSUFFICIENT_INFORMATION
