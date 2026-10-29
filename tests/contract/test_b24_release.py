"""Batch 24: Glucophage and Augmentin imply no release, and the Spanish and German release words (SPEC §3,
"Catalogue resolution" and "Claim-side release is trusted only when the claim says so")."""

from decimal import Decimal

import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_pair
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import IngredientAmount, PackObservation, PatientClaim, Release, Strength


@pytest.fixture(scope="module")
def cat():
    return load_catalogue()


def mg(inn, a):
    return IngredientAmount(inn=inn, amount=Decimal(str(a)), unit="mg")


def pack(label, *parts, release="unknown"):
    return PackObservation(observation_id="o1", label_text=label, readability="readable", visual_evidence=["r_o1"],
                           strength=Strength(ingredients=list(parts), per="tablet", release=release))


def claim(name, *parts, release="unknown"):
    return PatientClaim(claim_id="c1", name_text=name, status="active", audio_evidence=["t_c1"],
                        strength=Strength(ingredients=list(parts), per="tablet", release=release))


@pytest.mark.parametrize("brand", ["Glucophage", "Augmentin"])
def test_the_brand_implies_no_release(cat, brand):
    assert cat.implied_release(brand) is Release.UNKNOWN


def test_glucophage_against_an_xr_pack_is_insufficient_not_a_conflict(cat):
    found = reconcile_pair(claim("Glucophage 500 mg", mg("metformin", 500)),
                           pack("Glucophage XR 500 mg", mg("metformin", 500), release="modified"), cat)
    assert found.type is D.INSUFFICIENT_INFORMATION


@pytest.mark.parametrize("name", [
    "metformina liberación prolongada 500 mg",
    "Metformin Retardtabletten 500 mg",
])
def test_a_spanish_or_german_release_word_makes_the_claims_release_count(cat, name):
    found = reconcile_pair(claim(name, mg("metformin", 500), release="modified"),
                           pack("Metformin 500 mg prolonged release", mg("metformin", 500), release="modified"), cat)
    assert found.type is D.MATCH


def test_without_a_release_word_an_agreeing_release_is_still_not_trusted(cat):
    found = reconcile_pair(claim("metformina 500 mg", mg("metformin", 500), release="modified"),
                           pack("Metformin 500 mg prolonged release", mg("metformin", 500), release="modified"), cat)
    assert found.type is D.INSUFFICIENT_INFORMATION
