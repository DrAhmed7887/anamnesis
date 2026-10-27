"""Batch 11 contract: Arabic-script brands (M2 F-04) and salt-basis equivalence (M2 F-05). Written by the reviewer.

Do not edit. The Arabic fixtures are REAL claims Spark extracted from the same synthetic Arabic voice note on three
live runs (27 Oct). Voice spelled the brands differently each time: "Concor"/"كونكور", "BelocZok"/"بلوك زوك",
"Panadol"/"البنادول". Aliases are curated (LASA-safe), never transliterated or embedded.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all, reconcile_pair
from anamnesis.providers.spark import LabelReading
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import IngredientAmount, PackObservation, PatientClaim, Release, Strength

FIX = Path(__file__).parents[1] / "fixtures"


@pytest.fixture(scope="module")
def cat():
    return load_catalogue()


def live_packs():
    packs = []
    for i, item in enumerate(json.loads((FIX / "spark_labels_live_2026-10-27.json").read_text(encoding="utf-8"))):
        r = LabelReading.model_validate(item["reading"])
        packs.append(PackObservation(observation_id=f"o{i}", label_text=r.label_text, inn=r.inn, strength=r.strength,
                                     readability=r.readability, country=r.country, visual_evidence=[r.region_id]))
    return packs


# --- F-04: the three live Arabic runs all reconcile --------------------------------------------

@pytest.mark.parametrize("fixture", ["spark_claims_ar_live_2026-10-27.json", "spark_claims_ar_live_run2.json",
                                     "spark_claims_ar_live_run3.json"])
def test_every_live_arabic_run_reconciles(cat, fixture):
    claims = [PatientClaim.model_validate(c) for c in json.loads((FIX / fixture).read_text(encoding="utf-8"))["claims"]]
    found = {(f.claim_id, f.observation_id): f.type for f in reconcile_all(claims, live_packs(), cat)}
    assert found == {
        ("c1", "o1"): D.MATCH,
        ("c2", "o0"): D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH,
        ("c3", None): D.MISSING_MODALITY,
    }


@pytest.mark.parametrize("text,brand", [
    ("كونكور", "Concor"),
    ("الكونكور", "Concor"),          # attached article
    ("وكونكور", "Concor"),           # attached conjunction
    ("كونـكور", "Concor"),           # tatweel
    ("بلوك زوك", "Beloc-Zok"),       # spelling seen live (no ي)
    ("بيلوك زوك", "Beloc-Zok"),
    ("بيلوكزوك", "Beloc-Zok"),       # joined
    ("البنادول", "Panadol"),
    ("بالبنادول", "Panadol"),
    ("الPanadol", "Panadol"),         # Arabic article attached to a Latin brand
    ("بنادول اكسترا", "Panadol Extra"),
    ("أوجمنتين", "Augmentin"),        # alef with hamza
    ("اوجمنتين", "Augmentin"),
    ("جلوكوفاج", "Glucophage"),
    ("نورفاسك", "Norvasc"),
    ("ليبيتور", "Lipitor"),
])
def test_arabic_aliases_resolve(cat, text, brand):
    e = cat.resolve(text)
    assert e is not None and e.brand == brand


@pytest.mark.parametrize("text", [
    "كوردارون",    # Cordarone (amiodarone): looks and sounds like Concor
    "كوزار",       # Cozaar (losartan)
    "ترامادول",    # Tramadol: rhymes with Panadol
    "نولفادكس",    # Nolvadex (tamoxifen): looks like Norvasc
    "كونكوردا",    # not a whole-word match
    "بيلوك",       # half a brand name is not a brand
])
def test_lookalike_names_never_resolve(cat, text):
    assert cat.resolve(text) is None


def test_arabic_brand_names_carry_brand_facts(cat):
    assert cat.implied_release("بلوك زوك") is Release.MODIFIED
    assert cat.splittable("بلوك زوك") is True
    assert cat.implied_release("كونكور") is Release.IMMEDIATE


def test_two_arabic_brands_in_one_text_are_ambiguous(cat):
    assert cat.resolve("كونكور وبنادول") is None


# --- F-05: metoprolol succinate strengths are labelled on the tartrate-equivalent basis ------------

def mg(inn, a):
    return IngredientAmount(inn=inn, amount=Decimal(str(a)), unit="mg")


BELOC_95 = PackObservation(observation_id="o1", label_text="Beloc-Zok 95 mg",
                           strength=Strength(ingredients=[mg("metoprolol succinate", 95)], per="tablet", release="modified"),
                           readability="readable", visual_evidence=["r1"])


def claim(name, strength=None, intake=None):
    return PatientClaim(claim_id="c1", name_text=name, strength=strength, intake_amount=intake, status="active",
                        audio_evidence=["t1"])


def test_brand_claim_at_the_nominal_dose_matches_the_succinate_pack(cat):
    # "Beloc-Zok 100" is the tartrate-equivalent name of the 95 mg succinate tablet. Was: strength_mismatch.
    assert reconcile_pair(claim("Beloc-Zok", intake=mg("metoprolol", 100)), BELOC_95, cat).type is D.MATCH


def test_half_tablet_uses_the_nominal_basis(cat):
    # 50 mg against 95 mg succinate (= 100 mg nominal) is r = 0.5, not an odd ratio.
    assert reconcile_pair(claim("metoprolol", intake=mg("metoprolol", 50)), BELOC_95, cat).type \
        is D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH


def test_equivalence_never_hides_an_unknown_release(cat):
    s = Strength(ingredients=[mg("metoprolol", 100)], per="tablet")
    assert reconcile_pair(claim("metoprolol", strength=s), BELOC_95, cat).type is D.INSUFFICIENT_INFORMATION


def test_no_equivalence_when_the_claim_names_the_salt(cat):
    s = Strength(ingredients=[mg("metoprolol succinate", 100)], per="tablet", release="modified")
    assert reconcile_pair(claim("Beloc-Zok", strength=s), BELOC_95, cat).type is D.STRENGTH_MISMATCH


def test_strengths_outside_the_curated_table_compare_literally(cat):
    pack = PackObservation(observation_id="o1", label_text="Beloc-Zok 50 mg",
                           strength=Strength(ingredients=[mg("metoprolol succinate", 50)], per="tablet", release="modified"),
                           readability="readable", visual_evidence=["r1"])
    assert reconcile_pair(claim("Beloc-Zok", intake=mg("metoprolol", 50)), pack, cat).type is D.MATCH
