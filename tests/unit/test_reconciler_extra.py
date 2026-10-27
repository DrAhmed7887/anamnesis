"""Batch 17 extras: units per intake, two-product texts, claim-side release."""

import json
from decimal import Decimal

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_pair
from anamnesis.providers.claims import parse_claims_json
from anamnesis.schema import AudioTurn, DoseRegimen, IngredientAmount, PackObservation, PatientClaim, Strength
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.templates import TEMPLATES

CAT = load_catalogue()


def mg(inn, amount):
    return IngredientAmount(inn=inn, amount=Decimal(str(amount)), unit="mg")


def st(*parts, per="tablet", release="unknown"):
    return Strength(ingredients=list(parts), per=per, release=release)


def claim(name, strength=None, units=None, intake=None):
    regimen = DoseRegimen(units_per_intake=Decimal(str(units))) if units is not None else None
    return PatientClaim(claim_id="c1", name_text=name, strength=strength, intake_amount=intake,
                        regimen=regimen, status="active", audio_evidence=["t1"])


def pack(label, strength):
    return PackObservation(observation_id="o1", label_text=label, strength=strength,
                           readability="readable", visual_evidence=["r1"])


LIPITOR_20 = pack("Lipitor 20 mg", st(mg("atorvastatin", 20), release="immediate"))
CONCOR_5 = pack("Concor 5 mg", st(mg("bisoprolol", 5), release="immediate"))
BELOC_100 = pack("Beloc-Zok 100 mg", st(mg("metoprolol succinate", 100), release="modified"))


def test_one_unit_with_equal_strengths_still_matches():
    said = claim("Lipitor", strength=st(mg("atorvastatin", 20)), units=1)
    assert reconcile_pair(said, LIPITOR_20, CAT).type is D.MATCH


def test_three_units_alone_flag_a_multiple():
    assert reconcile_pair(claim("Concor", units=3), CONCOR_5, CAT).type is D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH


def test_half_a_capsule_is_a_strength_mismatch():
    capsule = pack("Lipitor 20 mg", st(mg("atorvastatin", 20), per="capsule"))
    assert reconcile_pair(claim("Lipitor", units=0.5), capsule, CAT).type is D.STRENGTH_MISMATCH


def test_units_never_produce_a_match_on_their_own():
    finding = reconcile_pair(claim("Concor", units=2), CONCOR_5, CAT)
    assert finding.type is not D.MATCH and finding.needs_clinician_review


def test_a_dropped_units_word_takes_the_claim_amounts_with_it():
    turns = [AudioTurn(turn_id="t1", start_ms=0, end_ms=2000, transcript="Half or one of the Lipitor 20 mg.")]
    raw = {"claims": [{
        "name_text": "Lipitor", "inn": None, "status": "active", "turn_ids": ["t1"], "intake_amount": None,
        "strength": {"ingredients": [{"inn": "atorvastatin", "amount": "20", "unit": "mg"}],
                     "per": "tablet", "release": "unknown"},
        "regimen": {"units_per_intake": "half or one", "intakes_per_day": None, "as_needed": None},
    }]}
    [found] = parse_claims_json(json.dumps(raw), turns)
    assert found.strength is None and found.intake_amount is None
    assert found.regimen.units_per_intake is None


def test_a_claim_naming_two_products_conflicts_even_with_a_strength():
    said = claim("Lipitor and Concor", strength=st(mg("atorvastatin", 20)))
    assert reconcile_pair(said, LIPITOR_20, CAT).type is D.INSUFFICIENT_INFORMATION


def test_an_unknown_name_is_unresolved_not_conflicted():
    assert CAT.is_ambiguous("mysterycure") is False
    assert reconcile_pair(claim("mysterycure"), CONCOR_5, CAT).type is D.UNRESOLVED_NAME


def test_a_brand_plus_its_ingredient_is_one_product():
    label = pack("Lipitor 20 mg atorvastatin calcium tablets",
                 st(mg("atorvastatin calcium", 20), release="immediate"))
    assert reconcile_pair(claim("Lipitor", strength=st(mg("atorvastatin", 20))), label, CAT).type is D.MATCH


def test_a_claim_release_without_a_release_word_or_brand_is_not_trusted():
    said = claim("metoprolol tablets", strength=st(mg("metoprolol", 100), release="modified"))
    assert reconcile_pair(said, BELOC_100, CAT).type is D.INSUFFICIENT_INFORMATION


def test_a_claim_release_word_trusts_the_explicit_release():
    said = claim("metoprolol sustained", strength=st(mg("metoprolol", 100), release="modified"))
    assert reconcile_pair(said, BELOC_100, CAT).type is D.MATCH


def test_units_apply_when_the_intake_copies_the_tablet_strength():
    said = claim("Lipitor", strength=st(mg("atorvastatin", 20)),
                 intake=mg("atorvastatin", 20), units=0.5)
    assert reconcile_pair(said, LIPITOR_20, CAT).type is D.STRENGTH_MISMATCH


def test_an_arabic_release_word_with_an_attached_article_counts_as_said():
    said = claim("ميتوبرولول الممتد", strength=st(mg("metoprolol", 100), release="modified"))
    assert reconcile_pair(said, BELOC_100, CAT).type is D.MATCH


def test_an_unsaid_release_that_disagrees_still_flags_a_conflict():
    said = claim("metoprolol", strength=st(mg("metoprolol", 100), release="immediate"))
    assert reconcile_pair(said, BELOC_100, CAT).type is D.FORMULATION_MISMATCH


def test_the_match_note_is_narrowed():
    assert TEMPLATES[D.MATCH] == "The compared identity and strength details agree."
