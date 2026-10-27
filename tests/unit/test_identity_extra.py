"""Additional regression tests for catalogue-aware ingredient identity."""

from decimal import Decimal

from anamnesis.core.catalogue import Catalogue, CatalogueEntry, load_catalogue
from anamnesis.core.reconcile import _resolve_inn, reconcile_pair
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import IngredientAmount, PackObservation, PatientClaim, Release, Strength


def _amount(inn: str, amount: str = "5") -> IngredientAmount:
    return IngredientAmount(inn=inn, amount=Decimal(amount), unit="mg")


def _claim(name: str, *, inn: str | None = None, strength: Strength | None = None) -> PatientClaim:
    return PatientClaim(
        claim_id="c1",
        name_text=name,
        inn=inn,
        strength=strength,
        status="active",
        audio_evidence=["turn1"],
    )


def _pack(label: str, strength: Strength, *, inn: str | None = None) -> PackObservation:
    return PackObservation(
        observation_id="o1",
        label_text=label,
        inn=inn,
        strength=strength,
        readability="readable",
        visual_evidence=["region1"],
    )


def test_shared_inn_resolver_handles_moieties_brands_and_unknowns() -> None:
    catalogue = load_catalogue()
    assert _resolve_inn("acetaminophen", catalogue) == "paracetamol"
    assert _resolve_inn("Concor", catalogue) == "bisoprolol"
    assert _resolve_inn("unlisted ingredient", catalogue) == "unlisted ingredient"


def test_brand_named_strength_ingredient_matches_canonical_pack_ingredient() -> None:
    catalogue = load_catalogue()
    claim = _claim(
        "Concor",
        strength=Strength(ingredients=[_amount("Concor")], per="tablet"),
    )
    pack = _pack(
        "Concor 5 mg",
        Strength(ingredients=[_amount("bisoprolol")], per="tablet"),
    )
    assert reconcile_pair(claim, pack, catalogue).type is D.MATCH


def test_named_salt_in_pack_scalar_inn_is_checked_before_amounts() -> None:
    catalogue = load_catalogue()
    claim = _claim(
        "metoprolol",
        inn="metoprolol tartrate",
        strength=Strength(ingredients=[_amount("metoprolol", "10")], per="tablet"),
    )
    pack = _pack(
        "metoprolol",
        Strength(ingredients=[_amount("metoprolol", "5")], per="tablet"),
        inn="metoprolol succinate",
    )
    assert reconcile_pair(claim, pack, catalogue).type is D.FORMULATION_MISMATCH


def test_implied_release_conflict_precedes_a_strength_difference() -> None:
    catalogue = load_catalogue()
    claim = _claim(
        "Beloc-Zok",
        strength=Strength(
            ingredients=[_amount("metoprolol", "5")], per="tablet", release=Release.IMMEDIATE
        ),
    )
    pack = _pack(
        "Beloc-Zok 100 mg",
        Strength(
            ingredients=[_amount("metoprolol", "100")], per="tablet", release=Release.MODIFIED
        ),
    )
    assert reconcile_pair(claim, pack, catalogue).type is D.FORMULATION_MISMATCH


def test_inn_only_catalogue_match_chooses_brand_name_deterministically() -> None:
    catalogue = load_catalogue()
    second = CatalogueEntry(
        brand="Atenololix",
        inns=frozenset({"bisoprolol"}),
        countries=("GB",),
        synthetic=True,
        release=Release.IMMEDIATE,
        splittable=True,
    )
    catalogue = Catalogue(catalogue.entries + (second,))
    resolved = catalogue.resolve("bisoprolol", country="GB")
    assert resolved is not None and resolved.brand == "Atenololix"


def test_duplicate_mentions_of_one_brand_remain_unambiguous() -> None:
    assert load_catalogue().resolve("Concor in the morning and Concor at night").brand == "Concor"
