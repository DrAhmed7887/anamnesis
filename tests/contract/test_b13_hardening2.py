"""Batch 13 (B12b) contract: the QM M2 blockers and the remaining accepted QM findings. Written by the reviewer.

Do not edit. QM2 #1 (combination-pack intakes reported as a silent match), QM2 #2 (salts only in spoken/printed
text, and salt contradictions within one side), QM2 #3 (strength vs scalar inn on one side), QM2 #5 (country
preference), QM2 #8 (more Arabic pins). See evidence/grills/m2-post-b9/effect.md.
"""

from decimal import Decimal

import pytest

from anamnesis.core.catalogue import Catalogue, CatalogueEntry, load_catalogue
from anamnesis.core.reconcile import reconcile_pair
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import IngredientAmount, PackObservation, PatientClaim, Release, Strength


@pytest.fixture(scope="module")
def cat():
    return load_catalogue()


def mg(inn, a):
    return IngredientAmount(inn=inn, amount=Decimal(str(a)), unit="mg")


def st(*parts, release="unknown"):
    return Strength(ingredients=list(parts), per="tablet", release=release)


def pack(label, strength=None, inn=None, oid="o1"):
    return PackObservation(observation_id=oid, label_text=label, strength=strength, inn=inn, readability="readable",
                           visual_evidence=[f"r_{oid}"])


def claim(name, strength=None, intake=None, inn=None):
    return PatientClaim(claim_id="c1", name_text=name, strength=strength, intake_amount=intake, inn=inn,
                        status="active", audio_evidence=["t1"])


AUGMENTIN = pack("Augmentin 875/125", st(mg("amoxicillin", 875), mg("clavulanic acid", 125)))


# --- QM2 #1: an intake can't be checked against a combination pack ------------------------------

def test_intake_against_a_combination_pack_is_never_a_silent_match(cat):
    # Was: match. The strengths agree, but the disagreeing intake was never compared.
    c = claim("Augmentin", st(mg("amoxicillin", 875), mg("clavulanic acid", 125)), intake=mg("amoxicillin", 1750))
    assert reconcile_pair(c, AUGMENTIN, cat).type is D.INSUFFICIENT_INFORMATION


def test_intake_only_claim_against_a_combination_pack(cat):
    assert reconcile_pair(claim("Augmentin", intake=mg("amoxicillin", 875)), AUGMENTIN, cat).type \
        is D.INSUFFICIENT_INFORMATION


def test_combination_strengths_without_intake_still_match(cat):
    c = claim("Augmentin", st(mg("amoxicillin", 875), mg("clavulanic acid", 125)))
    assert reconcile_pair(c, AUGMENTIN, cat).type is D.MATCH


# --- QM2 #2: salts in the spoken or printed text, and contradictions within one side -----------------

SUCCINATE_TEXT_ONLY = pack("Metoprolol succinate 100 mg", st(mg("metoprolol", 100)))  # salt only in the label text


def test_salt_spoken_only_in_the_name_is_compared(cat):
    c = claim("metoprolol tartrate", intake=mg("metoprolol", 100))  # salt only in what was said
    assert reconcile_pair(c, SUCCINATE_TEXT_ONLY, cat).type is D.FORMULATION_MISMATCH


def test_salt_printed_only_in_the_label_text_is_compared(cat):
    c = claim("metoprolol", intake=mg("metoprolol tartrate", 100))
    assert reconcile_pair(c, SUCCINATE_TEXT_ONLY, cat).type is D.FORMULATION_MISMATCH


def test_salt_words_in_text_are_found_after_normalisation(cat):
    c = claim("METOPROLOL-Tartrate", intake=mg("metoprolol", 100))
    assert reconcile_pair(c, SUCCINATE_TEXT_ONLY, cat).type is D.FORMULATION_MISMATCH


def test_salt_contradiction_within_the_claim_is_a_conflict_even_if_the_pack_names_none(cat):
    c = claim("metoprolol tartrate", intake=mg("metoprolol succinate", 100))
    assert reconcile_pair(c, pack("Metoprolol 100 mg", st(mg("metoprolol", 100))), cat).type \
        is D.INSUFFICIENT_INFORMATION


def test_salt_contradiction_within_the_pack_is_a_conflict(cat):
    p = pack("Metoprolol succinate 100 mg", st(mg("metoprolol tartrate", 100)))
    assert reconcile_pair(claim("metoprolol", intake=mg("metoprolol", 100)), p, cat).type \
        is D.INSUFFICIENT_INFORMATION


# --- QM2 #3: strength and scalar inn must agree on one side ----------------------------------------

def test_claim_strength_and_scalar_inn_contradiction_is_a_conflict(cat):
    c = claim("metoprolol", st(mg("metoprolol", 100)), inn="bisoprolol")
    assert reconcile_pair(c, pack("Beloc-Zok 100 mg", st(mg("metoprolol", 100), release="modified")), cat).type \
        is D.INSUFFICIENT_INFORMATION


def test_pack_strength_and_scalar_inn_contradiction_is_a_conflict(cat):
    p = pack("Concor 5 mg", st(mg("bisoprolol", 5)), inn="amlodipine")
    assert reconcile_pair(claim("Concor", intake=mg("bisoprolol", 5)), p, cat).type is D.INSUFFICIENT_INFORMATION


def test_scalar_inn_naming_the_salt_form_of_the_same_moiety_is_not_a_conflict(cat):
    p = pack("Concor 5 mg", st(mg("bisoprolol", 5)), inn="Bisoprolol fumarate")
    assert reconcile_pair(claim("Concor", intake=mg("bisoprolol", 5)), p, cat).type is D.MATCH


# --- QM2 #5: the country preference is real ----------------------------------------------------------

@pytest.fixture(scope="module")
def by_country():
    def entry(brand, country):
        return CatalogueEntry(brand=brand, inns=frozenset({"metoprolol"}), countries=(country,), synthetic=True,
                              release=Release.IMMEDIATE, splittable=None)
    return Catalogue((entry("Lopresor", "GB"), entry("Metohexal", "DE")))


@pytest.mark.parametrize("country,brand", [("GB", "Lopresor"), ("DE", "Metohexal"), ("de", "Metohexal")])
def test_country_picks_among_entries_sharing_an_ingredient(by_country, country, brand):
    assert by_country.resolve("metoprolol 100 mg", country=country).brand == brand


def test_without_a_country_the_choice_is_deterministic(by_country):
    assert by_country.resolve("metoprolol 100 mg").brand == by_country.resolve("metoprolol 100 mg").brand


# --- QM2 #8: more Arabic pins -----------------------------------------------------------------------------

@pytest.mark.parametrize("text,brand", [("وبيلوكزوك", "Beloc-Zok"), ("بالكونكور", "Concor"), ("أوجمنتين", "Augmentin"),
                                        ("إوجمنتين", "Augmentin"), ("وبانادول اكسترا", "Panadol Extra")])
def test_arabic_clitics_and_joined_forms(cat, text, brand):
    assert cat.resolve(text).brand == brand


def test_alef_variants_reconcile_across_claim_and_pack(cat):
    c = claim("اوجمنتين", st(mg("amoxicillin", 875), mg("clavulanic acid", 125)))
    p = pack("أوجمنتين 875/125", st(mg("amoxicillin", 875), mg("clavulanic acid", 125)))
    assert reconcile_pair(c, p, cat).type is D.MATCH
