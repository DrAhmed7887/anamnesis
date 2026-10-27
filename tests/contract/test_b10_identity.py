"""Batch 10 contract: identity and salt fixes from the M2 grill (evidence/grills/m2-post-b9/effect.md).

Written by the reviewer; do not edit. Every case below was reproduced on `main` before this batch:
F-01A gave a silent `match`, F-03a an extraction conflict, F-03b a cross-drug pairing, F-02 `None`, F-08 the wrong product.
"""

from decimal import Decimal

import pytest

from anamnesis.core.catalogue import Catalogue, CatalogueEntry, load_catalogue
from anamnesis.core.reconcile import reconcile_all, reconcile_pair
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import IngredientAmount, PackObservation, PatientClaim, Release, Strength


@pytest.fixture(scope="module")
def cat():
    return load_catalogue()


def mg(inn, a):
    return IngredientAmount(inn=inn, amount=Decimal(str(a)), unit="mg")


def pack(label, *parts, release="unknown", oid="o1"):
    strength = Strength(ingredients=list(parts), per="tablet", release=release) if parts else None
    return PackObservation(observation_id=oid, label_text=label, strength=strength, readability="readable",
                           visual_evidence=[f"r_{oid}"])


def claim(name, inn=None, strength=None, intake=None, cid="c1"):
    return PatientClaim(claim_id=cid, name_text=name, inn=inn, strength=strength, intake_amount=intake,
                        status="active", audio_evidence=[f"t_{cid}"])


BELOC = pack("Beloc-Zok 100 mg", mg("metoprolol succinate", 100), release="modified")


# --- F-01: a known salt or release conflict is never hidden ----------------------------------

def test_f01a_salt_on_the_intake_is_compared(cat):
    # Was: match, with no review.
    c = claim("metoprolol tartrate", intake=mg("metoprolol tartrate", 100))
    assert reconcile_pair(c, pack("Metoprolol succinate 100 mg", mg("metoprolol succinate", 100)), cat).type \
        is D.FORMULATION_MISMATCH


def test_f01a_salt_on_the_scalar_inn_is_compared(cat):
    c = claim("metoprolol", inn="metoprolol tartrate", intake=mg("metoprolol", 100))
    assert reconcile_pair(c, pack("Metoprolol succinate 100 mg", mg("metoprolol succinate", 100)), cat).type \
        is D.FORMULATION_MISMATCH


def test_f01b_known_conflicts_outrank_amount_comparisons(cat):
    # Was: intake_differs (half a Beloc-Zok) while the salt conflict stayed hidden.
    tartrate_half = claim("metoprolol tartrate", intake=mg("metoprolol tartrate", 50))
    assert reconcile_pair(tartrate_half, BELOC, cat).type is D.FORMULATION_MISMATCH
    ir_half = claim("metoprolol", intake=mg("metoprolol", 50),
                    strength=Strength(ingredients=[mg("metoprolol", 100)], per="tablet", release="immediate"))
    assert reconcile_pair(ir_half, BELOC, cat).type is D.FORMULATION_MISMATCH


def test_no_salt_named_by_the_patient_is_not_a_conflict(cat):
    assert reconcile_pair(claim("metoprolol", intake=mg("metoprolol", 50)), BELOC, cat).type \
        is D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH


# --- F-03: one resolver for every ingredient field -------------------------------------------------

CONCOR = pack("Concor 5 mg", mg("bisoprolol fumarate", 5), oid="o2")


def test_f03a_brand_in_a_strength_ingredient_resolves(cat):
    c = claim("Concor", strength=Strength(ingredients=[mg("concor", 5)], per="tablet"))
    assert reconcile_pair(c, CONCOR, cat).type is D.MATCH
    found = {(f.claim_id, f.observation_id): f.type for f in reconcile_all([c], [CONCOR], cat)}
    assert found == {("c1", "o2"): D.MATCH}  # was: unpaired, two missing_modality findings


def test_f03b_scalar_inn_that_contradicts_the_spoken_name_is_a_conflict(cat):
    c = claim("Concor", inn="metoprolol", intake=mg("metoprolol", 100))
    assert reconcile_pair(c, BELOC, cat).type is D.INSUFFICIENT_INFORMATION


def test_scalar_brand_inn_resolves_like_any_other_field(cat):
    assert reconcile_pair(claim("Concor", inn="Concor", intake=mg("Concor", 5)), CONCOR, cat).type is D.MATCH


# --- F-02: a second brand for the same ingredient must not break resolution ------------------------

@pytest.fixture(scope="module")
def two_brands(cat):
    lopresor = CatalogueEntry(brand="Lopresor", inns=frozenset({"metoprolol"}), countries=("GB",), synthetic=True,
                              release=Release.IMMEDIATE, splittable=True)
    return Catalogue(cat.entries + (lopresor,))


def test_f02_brand_on_the_label_wins_over_its_own_ingredient(two_brands):
    e = two_brands.resolve("Beloc-Zok 100 mg\nMetoprolol succinate\nProlonged-release tablets")
    assert e is not None and e.brand == "Beloc-Zok"
    assert two_brands.implied_release("Beloc-Zok 100 mg\nMetoprolol succinate") is Release.MODIFIED


def test_f02_ingredient_only_text_still_resolves_but_implies_nothing(two_brands):
    e = two_brands.resolve("metoprolol 100 mg")
    assert e is not None and e.inns == frozenset({"metoprolol"})
    assert two_brands.implied_release("metoprolol 100 mg") is Release.UNKNOWN
    assert two_brands.splittable("metoprolol") is None


def test_f02_two_different_brands_are_still_ambiguous(two_brands):
    assert two_brands.resolve("Beloc-Zok or Lopresor") is None


# --- F-08: containment by character span, not by substring -------------------------------------

@pytest.mark.parametrize("text", ["I take Panadol in the morning and Panadol Extra at night",
                                  "Panadol Extra, and plain Panadol"])
def test_f08_two_separate_mentions_are_ambiguous(cat, text):
    assert cat.resolve(text) is None


@pytest.mark.parametrize("text,brand", [("Panadol Extra 500 mg", "Panadol Extra"), ("Panadol 500 mg", "Panadol")])
def test_f08_a_longer_name_still_wins_inside_its_own_span(cat, text, brand):
    assert cat.resolve(text).brand == brand
