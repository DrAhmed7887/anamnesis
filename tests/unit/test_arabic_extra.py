"""Additional coverage for Arabic brand matching and salt-basis equivalence."""

from decimal import Decimal

import pytest

from anamnesis.core.catalogue import load_catalogue, normalise
from anamnesis.core.reconcile import reconcile_pair
from anamnesis.schema import (
    SALT_BASIS_EQUIVALENTS,
    IngredientAmount,
    PackObservation,
    PatientClaim,
    Release,
    Strength,
)
from anamnesis.schema import DiscrepancyType as D


def _amount(inn: str, amount: str) -> IngredientAmount:
    return IngredientAmount(inn=inn, amount=Decimal(amount), unit="mg")


def _claim(
    name: str,
    *,
    strength: Strength | None = None,
    intake: IngredientAmount | None = None,
) -> PatientClaim:
    return PatientClaim(
        claim_id="c1",
        name_text=name,
        strength=strength,
        intake_amount=intake,
        status="active",
        audio_evidence=["t1"],
    )


def _pack(amount: str, *, release: Release = Release.MODIFIED, salt: str = "succinate") -> PackObservation:
    return PackObservation(
        observation_id="o1",
        label_text="Beloc-Zok 95 mg",
        strength=Strength(
            ingredients=[_amount(f"metoprolol {salt}", amount)],
            per="tablet",
            release=release,
        ),
        readability="readable",
        visual_evidence=["r1"],
    )


def test_normalise_applies_arabic_character_and_script_rules() -> None:
    assert normalise("أَإِآٱ ى ةـ ١٢٣ الPanadol") == "اااا ي ه 123 ال panadol"


@pytest.mark.parametrize(
    "text,brand",
    [
        ("والكونكور", "Concor"),
        ("فالكونكور", "Concor"),
        ("للكونكور", "Concor"),
        ("بيلوكزوك", "Beloc-Zok"),
        ("بالـبنادول", "Panadol"),
        ("بانادول اكسترا", "Panadol Extra"),
    ],
)
def test_clitics_and_joined_arabic_aliases_resolve_as_brands(text: str, brand: str) -> None:
    entry = load_catalogue().resolve(text)
    assert entry is not None and entry.brand == brand


def test_arabic_aliases_keep_brand_facts_and_do_not_match_partial_names() -> None:
    catalogue = load_catalogue()
    assert catalogue.implied_release("بلوك زوك") is Release.MODIFIED
    assert catalogue.splittable("بلوك زوك") is True
    assert catalogue.resolve("بيلوك") is None


def test_metoprolol_succinate_has_only_curated_nominal_amounts() -> None:
    assert set(SALT_BASIS_EQUIVALENTS.values()) == {
        Decimal("25"), Decimal("50"), Decimal("100"), Decimal("200")
    }
    catalogue = load_catalogue()
    for labelled, nominal in (("23.75", "25"), ("47.5", "50"), ("95", "100"), ("190", "200")):
        claim = _claim("Beloc-Zok", strength=Strength(
            ingredients=[_amount("metoprolol", nominal)], per="tablet", release=Release.MODIFIED
        ))
        assert reconcile_pair(claim, _pack(labelled), catalogue).type is D.MATCH


def test_salt_basis_applies_to_intakes_and_half_tablets() -> None:
    catalogue = load_catalogue()
    full = _claim("Beloc-Zok", intake=_amount("metoprolol", "100"))
    half = _claim("metoprolol", intake=_amount("metoprolol", "50"))
    assert reconcile_pair(full, _pack("95"), catalogue).type is D.MATCH
    assert reconcile_pair(half, _pack("95"), catalogue).type is D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH


def test_explicit_claim_salt_uses_literal_amounts_and_formulation_rules_still_run() -> None:
    catalogue = load_catalogue()
    salted = _claim(
        "Beloc-Zok",
        strength=Strength(
            ingredients=[_amount("metoprolol succinate", "100")], per="tablet", release=Release.MODIFIED
        ),
    )
    assert reconcile_pair(salted, _pack("95"), catalogue).type is D.STRENGTH_MISMATCH

    name_salted = _claim(
        "metoprolol succinate",
        strength=Strength(
            ingredients=[_amount("metoprolol", "100")], per="tablet", release=Release.MODIFIED
        ),
    )
    assert reconcile_pair(name_salted, _pack("95"), catalogue).type is D.STRENGTH_MISMATCH

    release_conflict = _claim(
        "Beloc-Zok",
        strength=Strength(
            ingredients=[_amount("metoprolol", "100")], per="tablet", release=Release.IMMEDIATE
        ),
    )
    assert reconcile_pair(release_conflict, _pack("95"), catalogue).type is D.FORMULATION_MISMATCH


def test_unlisted_succinate_amount_compares_literally() -> None:
    claim = _claim("Beloc-Zok", intake=_amount("metoprolol", "50"))
    assert reconcile_pair(claim, _pack("60"), load_catalogue()).type is D.STRENGTH_MISMATCH
