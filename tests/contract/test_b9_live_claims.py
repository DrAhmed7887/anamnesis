"""Batch 9 contract: the first live claim extraction (27 Oct) must reconcile correctly. Written by the reviewer; do not edit.

Live Spark copied the BRAND into intake_amount.inn ("concor"), which the reconciler compared with "bisoprolol" and
reported as a false strength_mismatch. Voice Transcribe wrote the brand as one word ("BelocZok"), which the catalogue
could not resolve. Both fixtures are real outputs: tests/fixtures/spark_claims_{en,ar}_live_2026-10-27.json.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all, reconcile_pair
from anamnesis.providers.spark import LabelReading
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import IngredientAmount, PackObservation, PatientClaim, Strength

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


def live_claims(lang):
    data = json.loads((FIX / f"spark_claims_{lang}_live_2026-10-27.json").read_text(encoding="utf-8"))
    return [PatientClaim.model_validate(c) for c in data["claims"]]


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_live_extracted_claims_reconcile_correctly(cat, lang):
    found = {(f.claim_id, f.observation_id): f.type for f in reconcile_all(live_claims(lang), live_packs(), cat)}
    assert found == {
        ("c1", "o1"): D.MATCH,                               # "Concor five milligrams once a day" vs Concor 5 mg
        ("c2", "o0"): D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH,   # 50 mg twice a day vs Beloc-Zok 100 mg (scored)
        ("c3", None): D.MISSING_MODALITY,                    # Panadol: stopped, no pack in the photo
    }


@pytest.mark.parametrize("text", ["BelocZok", "beloczok 50 mg", "Beloc Zok", "Beloc-Zok"])
def test_brands_resolve_with_spaces_or_hyphens_removed(cat, text):
    assert cat.resolve(text).inns == frozenset({"metoprolol"})


@pytest.mark.parametrize("text", ["Belo", "Zok", "beloczokx"])
def test_joined_brand_matching_stays_whole_word(cat, text):
    assert cat.resolve(text) is None


def mg(inn, a):
    return IngredientAmount(inn=inn, amount=Decimal(str(a)), unit="mg")


CONCOR_PACK = PackObservation(observation_id="o1", label_text="Concor 5 mg",
                              strength=Strength(ingredients=[mg("bisoprolol fumarate", 5)], per="tablet"),
                              readability="readable", visual_evidence=["r1"])


def test_brand_name_in_intake_resolves_through_the_catalogue(cat):
    claim = PatientClaim(claim_id="c1", name_text="Concor", intake_amount=mg("Concor", 5), status="active",
                         audio_evidence=["t1"])
    assert reconcile_pair(claim, CONCOR_PACK, cat).type is D.MATCH


def test_intake_naming_another_drug_is_an_extraction_conflict_not_a_strength_alarm(cat):
    claim = PatientClaim(claim_id="c1", name_text="Concor", intake_amount=mg("Lipitor", 5), status="active",
                         audio_evidence=["t1"])
    assert reconcile_pair(claim, CONCOR_PACK, cat).type is D.INSUFFICIENT_INFORMATION


def test_unknown_intake_name_is_an_extraction_conflict(cat):
    claim = PatientClaim(claim_id="c1", name_text="Concor", intake_amount=mg("Xyzzol", 5), status="active",
                         audio_evidence=["t1"])
    assert reconcile_pair(claim, CONCOR_PACK, cat).type is D.INSUFFICIENT_INFORMATION
