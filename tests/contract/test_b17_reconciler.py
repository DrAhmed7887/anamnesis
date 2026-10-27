"""Batch 17 contract: the reconciler's remaining false-agreement paths. Written by the CEO; Muse must not edit it.

Code grill C1 (units per intake), C4 (a text naming two products), C8 (claim-side release); QM M3 round 2 #2 (a
stated strength is exact), #3 (a Latin brand with an Arabic clitic) and #5 (the match wording). SPEC §3 and §2.
Every case marked "was: match" is a false agreement in the code before this batch.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.guardrails import assert_no_advice
from anamnesis.core.reconcile import _strength_type, reconcile_all, reconcile_pair
from anamnesis.providers.claims import parse_claims_json
from anamnesis.schema import AudioTurn, DoseRegimen, IngredientAmount, PackObservation, PatientClaim, Strength
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.templates import TEMPLATES

CAT = load_catalogue()
ROOT = Path(__file__).resolve().parents[2]


def mg(inn, amount):
    return IngredientAmount(inn=inn, amount=Decimal(str(amount)), unit="mg")


def st(*parts, per="tablet", release="unknown"):
    return Strength(ingredients=list(parts), per=per, release=release)


def claim(name, strength=None, units=None, intake=None):
    regimen = DoseRegimen(units_per_intake=Decimal(str(units))) if units is not None else None
    return PatientClaim(claim_id="c1", name_text=name, strength=strength, intake_amount=intake, regimen=regimen,
                        status="active", audio_evidence=["t1"])


def pack(label, strength):
    return PackObservation(observation_id="o1", label_text=label, strength=strength, readability="readable",
                           visual_evidence=["r1"])


LIPITOR_20 = pack("Lipitor 20 mg", st(mg("atorvastatin", 20), release="immediate"))  # catalogue: not splittable
CONCOR_5 = pack("Concor 5 mg", st(mg("bisoprolol", 5), release="immediate"))  # catalogue: splittable
NORVASC_10 = pack("Norvasc 10 mg", st(mg("amlodipine", 10), release="immediate"))  # catalogue: unknown
BELOC_100 = pack("Beloc-Zok 100 mg", st(mg("metoprolol succinate", 100), release="modified"))


# --- C1: tablets per intake count ----------------------------------------------------------------------------------

@pytest.mark.parametrize("units,the_pack,expected", [
    (0.5, LIPITOR_20, D.STRENGTH_MISMATCH),  # half of a tablet that must not be split (was: match)
    (2, CONCOR_5, D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH),  # "two of the Concor 5" (was: match)
    (0.5, CONCOR_5, D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH),  # a scored tablet: possibly fine, ask
    (0.5, NORVASC_10, D.INSUFFICIENT_INFORMATION),  # splittability unknown
    (1.5, CONCOR_5, D.STRENGTH_MISMATCH),
    (1, CONCOR_5, D.MATCH),
])
def test_units_per_intake_count_when_the_claim_states_the_tablet_strength(units, the_pack, expected):
    brand = the_pack.label_text.split()[0]
    said = claim(brand, strength=st(the_pack.strength.ingredients[0]), units=units)
    assert reconcile_pair(said, the_pack, CAT).type is expected


def test_units_alone_flag_a_multiple_but_never_make_a_match():
    assert reconcile_pair(claim("Concor", units=2), CONCOR_5, CAT).type is D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH
    assert reconcile_pair(claim("Concor", units=1), CONCOR_5, CAT).type is D.INSUFFICIENT_INFORMATION


def test_units_against_a_liquid_cannot_be_checked():
    syrup = pack("Panadol syrup", st(mg("paracetamol", 24), per="ml"))
    assert reconcile_pair(claim("Panadol", units=2), syrup, CAT).type is D.INSUFFICIENT_INFORMATION


def test_a_dropped_units_per_intake_takes_the_claim_amounts_with_it():
    turns = [AudioTurn(turn_id="t1", start_ms=0, end_ms=2000, transcript="One or two of the Concor 5 mg.")]
    raw = {"claims": [{
        "name_text": "Concor", "inn": None, "status": "active", "turn_ids": ["t1"], "intake_amount": None,
        "strength": {"ingredients": [{"inn": "bisoprolol", "amount": "5", "unit": "mg"}], "per": "tablet",
                     "release": "unknown"},
        "regimen": {"units_per_intake": "1-2", "intakes_per_day": "1", "as_needed": None},
    }]}
    [found] = parse_claims_json(json.dumps(raw), turns)
    assert found.strength is None and found.intake_amount is None and found.regimen.units_per_intake is None
    finding = reconcile_pair(found, CONCOR_5, CAT)
    assert finding.type is not D.MATCH and finding.needs_clinician_review


# --- C4: a text that names two products is an extraction conflict ---------------------------------------------------

def test_a_label_that_names_two_products_is_an_extraction_conflict():
    mixed = pack("Beloc-Zok 100 mg Concor 5 mg", st(mg("metoprolol", 100)))
    said = claim("metoprolol", strength=st(mg("metoprolol", 100)))
    assert reconcile_pair(said, mixed, CAT).type is D.INSUFFICIENT_INFORMATION  # was: match


def test_a_claim_that_names_two_products_is_an_extraction_conflict():
    said = claim("Concor and Beloc-Zok", strength=st(mg("bisoprolol", 5)))
    assert reconcile_pair(said, CONCOR_5, CAT).type is D.INSUFFICIENT_INFORMATION  # was: match


def test_one_product_named_by_brand_and_ingredient_is_not_a_conflict():
    label = pack("Concor 5 mg Bisoprolol fumarate 30 film-coated tablets", st(mg("bisoprolol fumarate", 5),
                                                                                release="immediate"))
    assert reconcile_pair(claim("Concor", strength=st(mg("bisoprolol", 5))), label, CAT).type is D.MATCH


# --- C8: a claim-side release counts only when the patient said it ----------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("metoprolol", D.INSUFFICIENT_INFORMATION),  # a guessed "modified" is not trusted (was: match)
    ("metoprolol retard", D.MATCH),  # a release word
    ("Beloc-Zok", D.MATCH),  # a brand
    ("ميتوبرولول ممتد", D.MATCH),  # an Arabic release word
])
def test_a_claim_side_release_is_trusted_only_when_the_claim_says_so(name, expected):
    said = claim(name, strength=st(mg("metoprolol", 100), release="modified"))
    assert reconcile_pair(said, BELOC_100, CAT).type is expected


# --- QM M3 round 2 #5, #2, #3 -----------------------------------------------------------------------------------------

def test_the_match_note_says_only_what_was_compared():
    assert TEMPLATES[D.MATCH] == "The compared identity and strength details agree."
    assert_no_advice(TEMPLATES[D.MATCH])


def test_a_stated_tablet_strength_matches_the_nominal_amount_but_never_a_multiple():
    def tablet(amount):
        return st(mg("metoprolol", amount))

    nominal = {"metoprolol": Decimal(100)}
    assert _strength_type(tablet(100), tablet(50), CAT, nominal) is D.MATCH  # the nominal amount
    assert _strength_type(tablet(100), tablet(50), CAT, None) is D.STRENGTH_MISMATCH  # 2 x literal is not a strength
    assert _strength_type(tablet(25), tablet(50), CAT, nominal) is D.STRENGTH_MISMATCH


def test_a_salt_next_to_a_latin_brand_with_an_arabic_clitic_is_found():
    said = claim("الBeloc-Zok succinate", intake=mg("metoprolol", 100))
    tartrate = pack("Beloc-Zok 100 mg", st(mg("metoprolol tartrate", 100), release="modified"))
    assert reconcile_pair(said, tartrate, CAT).type is D.FORMULATION_MISMATCH


# --- the frozen demo path is unchanged -------------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_frozen_demo_findings_are_unchanged(lang):
    report = json.loads((ROOT / f"evidence/live/2026-10-27/report_{lang}.json").read_text(encoding="utf-8"))
    claims = [PatientClaim.model_validate(c) for c in report["claims"]]
    observations = [PackObservation.model_validate(o) for o in report["observations"]]
    found = sorted(f.type.value for f in reconcile_all(claims, observations, CAT))
    assert found == sorted(f["type"] for f in report["findings"])
