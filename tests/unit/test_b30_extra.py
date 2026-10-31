"""Extra checks for batch 30: combined `inn` names its ingredient set."""

from decimal import Decimal

import pytest

from anamnesis.agent.loop import _named_ingredients, _salts
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import (
    _resolve_inn_part,
    _split_inn_parts,
    claim_identity_conflict,
    pack_identity_conflict,
    reconcile_pair,
)
from anamnesis.providers.spark import LabelReading
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import IngredientAmount, PackObservation, PatientClaim, Strength

CAT = load_catalogue()


def part(inn: str, amount: str) -> IngredientAmount:
    return IngredientAmount(inn=inn, amount=Decimal(amount), unit="mg")


def strength(*parts: IngredientAmount) -> Strength:
    return Strength(ingredients=list(parts), per="tablet")


def claim(
    name: str, inn: str | None = None, pack_strength: Strength | None = None
) -> PatientClaim:
    return PatientClaim(
        claim_id="c1",
        name_text=name,
        inn=inn,
        strength=pack_strength,
        status="active",
        audio_evidence=["turn-0"],
    )


def pack(label: str, inn: str | None = None, pack_strength: Strength | None = None) -> PackObservation:
    return PackObservation(
        observation_id="o0",
        label_text=label,
        inn=inn,
        strength=pack_strength,
        readability="readable",
        visual_evidence=["r-0"],
    )


AUGMENTIN = strength(part("amoxicillin", "875"), part("clavulanic acid", "125"))
PANADOL_EXTRA = strength(part("paracetamol", "500"), part("caffeine", "65"))


@pytest.mark.parametrize(
    "inn",
    [
        "amoxicillin و clavulanic acid",
        "clavulanic acid و amoxicillin",
        "amoxicillin AND clavulanic acid",
        "amoxicillin And clavulanic acid",
        "amoxicillin+clavulanic acid",
        "amoxicillin&clavulanic acid",
        "amoxicillin,clavulanic acid",
    ],
)
def test_combined_inn_delimiters_name_their_set(inn: str) -> None:
    observation = pack("Augmentin 875 mg/125 mg", inn, AUGMENTIN)
    assert not pack_identity_conflict(observation, CAT)
    assert reconcile_pair(claim("Augmentin", None, AUGMENTIN), observation, CAT).type is D.MATCH


def test_each_part_resolves_like_any_inn() -> None:
    french = pack("Augmentin 875 mg/125 mg", "amoxicilline/acide clavulanique", AUGMENTIN)
    assert not pack_identity_conflict(french, CAT)
    alias = pack("Panadol Extra", "acetaminophen/caffeine", PANADOL_EXTRA)
    assert not pack_identity_conflict(alias, CAT)
    assert (
        reconcile_pair(claim("Panadol Extra", None, PANADOL_EXTRA), alias, CAT).type is D.MATCH
    )


def test_combined_inn_matches_any_combination_pack() -> None:
    observation = pack("Panadol Extra", "caffeine + paracetamol", PANADOL_EXTRA)
    assert not pack_identity_conflict(observation, CAT)
    assert (
        reconcile_pair(claim("Panadol Extra", None, PANADOL_EXTRA), observation, CAT).type
        is D.MATCH
    )


def test_single_inn_among_combination_strength_is_not_a_conflict() -> None:
    assert not pack_identity_conflict(pack("Augmentin 875 mg/125 mg", "amoxicillin", AUGMENTIN), CAT)
    assert pack_identity_conflict(pack("Augmentin 875 mg/125 mg", "paracetamol", AUGMENTIN), CAT)


@pytest.mark.parametrize("inn", ["candesartan", "دواء"])
def test_and_or_waw_inside_a_word_does_not_split(inn: str) -> None:
    one = strength(part(inn, "8"))
    assert not pack_identity_conflict(pack(inn, inn, one), CAT)
    assert pack_identity_conflict(pack("Concor 5 mg", inn, strength(part("bisoprolol", "5"))), CAT)


def test_combined_inn_without_strength_mismatch_is_a_conflict() -> None:
    assert pack_identity_conflict(pack("Augmentin", "amoxicillin/sulbactam"), CAT)
    assert claim_identity_conflict(claim("Augmentin", "amoxicillin/sulbactam"), CAT)
    assert not claim_identity_conflict(claim("Augmentin", "amoxicillin/clavulanic acid"), CAT)


def test_split_keeps_digit_commas_and_attached_waw() -> None:
    assert _split_inn_parts("2,4-dichlorobenzyl alcohol") == ["2,4-dichlorobenzyl alcohol"]
    assert _split_inn_parts("وارفارين") == ["وارفارين"]
    assert _split_inn_parts("metoprolol وcaffeine") == ["metoprolol وcaffeine"]
    assert _split_inn_parts("metoprolol و caffeine") == ["metoprolol", "caffeine"]
    assert _split_inn_parts("metoprolol, caffeine") == ["metoprolol", "caffeine"]
    assert _split_inn_parts("metoprolol/") == ["metoprolol"]


def test_each_part_of_a_combined_inn_contributes_its_salt() -> None:
    one = strength(part("metoprolol", "100"))
    observation = pack("Metoprolol 100 mg", "metoprolol tartrate/metoprolol succinate", one)
    assert not pack_identity_conflict(observation, CAT)
    assert reconcile_pair(claim("Metoprolol", None, one), observation, CAT).type is D.INSUFFICIENT_INFORMATION


def test_a_salt_inside_a_combined_inn_counts_across_sides() -> None:
    one = strength(part("metoprolol", "100"))
    observation = pack("Metoprolol 100 mg", "metoprolol succinate", one)
    stated = claim("Metoprolol", "metoprolol tartrate/metoprolol", one)
    assert not claim_identity_conflict(stated, CAT)
    assert reconcile_pair(stated, observation, CAT).type is D.FORMULATION_MISMATCH


def test_a_stray_separator_leaves_the_stripped_part() -> None:
    one = strength(part("metoprolol", "100"))
    assert not pack_identity_conflict(pack("Metoprolol 100 mg", "metoprolol/", one), CAT)
    assert not pack_identity_conflict(pack("Metoprolol", "metoprolol/"), CAT)


def test_the_second_read_splits_a_combined_inn() -> None:
    reading = LabelReading(
        region_id="r", label_text="Metoprolol", inn="metoprolol tartrate/caffeine",
        readability="readable",
    )
    assert _named_ingredients(reading) == frozenset({"metoprolol", "caffeine"})
    assert _salts(reading) == {"metoprolol": frozenset({"tartrate"})}


def test_covers_needs_one_name_over_the_whole_part() -> None:
    assert CAT.covers("Concor")
    assert CAT.covers("bisoprolol")
    assert not CAT.covers("Concor plus caffeine")
    assert not CAT.covers("bisoprolol with caffeine")


def test_an_inn_part_resolves_through_the_catalogue_only_when_covered() -> None:
    assert _resolve_inn_part("Concor", CAT) == "bisoprolol"
    assert _resolve_inn_part("Concor plus caffeine", CAT) == "concor plus caffeine"


def test_a_part_with_words_beyond_one_catalogue_name_is_its_own_ingredient() -> None:
    one = strength(part("bisoprolol", "5"))
    assert pack_identity_conflict(pack("Concor 5 mg", "Concor plus caffeine", one), CAT)
    assert pack_identity_conflict(pack("Concor 5 mg", "bisoprolol/Concor plus caffeine", one), CAT)


def test_a_whole_catalogue_name_as_an_inn_part_still_resolves() -> None:
    one = strength(part("bisoprolol", "5"))
    assert not pack_identity_conflict(pack("Concor 5 mg", "Concor", one), CAT)
    combo = pack("Panadol Extra", "Panadol/caffeine", PANADOL_EXTRA)
    assert not pack_identity_conflict(combo, CAT)
    assert reconcile_pair(claim("Panadol Extra", None, PANADOL_EXTRA), combo, CAT).type is D.MATCH


def test_more_than_eight_parts_are_read_whole() -> None:
    names = [f"ingredient{i}" for i in range(9)]
    assert _split_inn_parts("/".join(names[:8])) == names[:8]
    assert _split_inn_parts("/".join(names)) == ["/".join(names)]
    eight = strength(*(part(name, "1") for name in names[:8]))
    assert not pack_identity_conflict(pack("x", "/".join(names[:8]), eight), CAT)
    nine = strength(*(part(name, "1") for name in names))
    assert pack_identity_conflict(pack("x", "/".join(names), nine), CAT)
