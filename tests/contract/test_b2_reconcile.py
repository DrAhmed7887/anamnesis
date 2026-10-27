"""Batch 2 contract: catalogue, reconciler, guardrails (SPEC.md §3). Written by the reviewer; do not edit."""

from decimal import Decimal

import pytest
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.guardrails import PATIENT_QUESTIONS, TEMPLATES, AdviceLeak, assert_no_advice
from anamnesis.core.reconcile import reconcile_all, reconcile_pair

from anamnesis.schema import (
    DiscrepancyType as D,
)
from anamnesis.schema import (
    DoseRegimen,
    IngredientAmount,
    PackObservation,
    PatientClaim,
    Strength,
)


@pytest.fixture(scope="module")
def cat():
    return load_catalogue()


def amt(inn, mg, unit="mg"):
    return IngredientAmount(inn=inn, amount=Decimal(str(mg)), unit=unit)


def st(*pairs, unit="mg"):
    return Strength(ingredients=[amt(i, a, unit) for i, a in pairs], per="tablet")


def claim(name, strength=None, intake=None, status="active", inn=None, regimen=None, cid="c1"):
    return PatientClaim(claim_id=cid, name_text=name, inn=inn, strength=strength, intake_amount=intake,
                        regimen=regimen, status=status, audio_evidence=[f"t_{cid}"])


def pack(label, strength=None, readability="readable", country=None, oid="o1"):
    return PackObservation(observation_id=oid, label_text=label, strength=strength,
                           readability=readability, country=country, visual_evidence=[f"r_{oid}"])


# --- catalogue ---------------------------------------------------------------

def test_catalogue_is_small_synthetic_and_marked(cat):
    assert 8 <= len(cat.entries) <= 12
    assert all(e.synthetic for e in cat.entries)


@pytest.mark.parametrize("text,inns", [
    ("Concor", {"bisoprolol"}),
    ("CONCOR® 5 mg", {"bisoprolol"}),
    ("bisoprolol", {"bisoprolol"}),
    ("Panadol 500 mg", {"paracetamol"}),
    ("Panadol Extra 500 mg/65 mg", {"paracetamol", "caffeine"}),  # longest name wins
    ("Augmentin 875/125", {"amoxicillin", "clavulanic acid"}),
    ("Glucophage 850 mg", {"metformin"}),
])
def test_catalogue_resolves_brand_and_inn(cat, text, inns):
    assert cat.resolve(text).inns == frozenset(inns)


def test_catalogue_returns_none_for_unknown(cat):
    assert cat.resolve("Xyzzol 20 mg") is None


# --- the 10 adversarial cases (evidence/grills/m0-plan/effect.md #3) ---------

CASES = [
    # 1-2 clean matches
    ("clean_brand", claim("Concor", st(("bisoprolol", 5))), pack("Concor 5 mg", st(("bisoprolol", 5)), country="DE"),
     D.MATCH),
    ("clean_brand_2", claim("Glucophage", st(("metformin", 850))), pack("Glucophage 850 mg", st(("metformin", 850))),
     D.MATCH),
    # 3-4 strength mismatches (4: double strength is still a strength claim, not an intake)
    ("strength_25_vs_100", claim("metoprolol", st(("metoprolol", 25))), pack("Beloc-Zok 100 mg", st(("metoprolol", 100))),
     D.STRENGTH_MISMATCH),
    ("strength_5_vs_10", claim("amlodipine", st(("amlodipine", 5))), pack("Norvasc 10 mg", st(("amlodipine", 10))),
     D.STRENGTH_MISMATCH),
    # 5 dose vs frequency: 50 mg twice daily from a 100 mg pack = possibly half tablets
    ("intake_half", claim("metoprolol", intake=amt("metoprolol", 50), regimen=DoseRegimen(intakes_per_day=Decimal(2))),
     pack("Beloc-Zok 100 mg", st(("metoprolol", 100))), D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH),
    # 6 combination trap
    ("combo_trap", claim("Panadol", st(("paracetamol", 500))),
     pack("Panadol Extra", st(("paracetamol", 500), ("caffeine", 65))), D.INGREDIENT_MISMATCH),
    # 7 brand alias: INN spoken, brand on the pack
    ("brand_alias", claim("bisoprolol", st(("bisoprolol", 5))), pack("Concor 5 mg", st(("bisoprolol", 5))), D.MATCH),
    # 8 ratio trap
    ("ratio_trap", claim("Augmentin", st(("amoxicillin", 875), ("clavulanic acid", 125))),
     pack("Augmentin 500/125", st(("amoxicillin", 500), ("clavulanic acid", 125))), D.RATIO_MISMATCH),
    # 9 unreadable label: abstain, never guess
    ("unreadable", claim("Concor", st(("bisoprolol", 5))), pack(None, readability="unreadable"), D.UNREADABLE_SOURCE),
    # 10 negation: "I stopped Concor" but the box is in the photo
    ("negation", claim("Concor", status="discontinued"), pack("Concor 5 mg", st(("bisoprolol", 5))),
     D.DISCONTINUED_BUT_PRESENT),
]


@pytest.mark.parametrize("name,c,o,expected", CASES, ids=[c[0] for c in CASES])
def test_adversarial_case(cat, name, c, o, expected):
    f = reconcile_pair(c, o, cat)
    assert f.type is expected
    assert f.audio_evidence == c.audio_evidence and f.visual_evidence == o.visual_evidence
    assert f.claim_id == c.claim_id and f.observation_id == o.observation_id
    assert f.needs_clinician_review is (expected is not D.MATCH)
    assert f.clinician_note == TEMPLATES[expected]


def test_partial_label_is_also_unreadable(cat):
    f = reconcile_pair(claim("Concor"), pack("Con…", readability="partial"), cat)
    assert f.type is D.UNREADABLE_SOURCE


def test_unknown_name_is_unresolved(cat):
    f = reconcile_pair(claim("Xyzzol"), pack("Concor 5 mg", st(("bisoprolol", 5))), cat)
    assert f.type is D.UNRESOLVED_NAME


def test_units_are_normalized(cat):
    c = claim("metformin", st(("metformin", 1), unit="g"))
    assert reconcile_pair(c, pack("Glucophage 1000 mg", st(("metformin", 1000))), cat).type is D.MATCH


def test_intake_equal_to_strength_is_match_and_odd_ratio_is_mismatch(cat):
    o = pack("Beloc-Zok 100 mg", st(("metoprolol", 100)))
    assert reconcile_pair(claim("metoprolol", intake=amt("metoprolol", 100)), o, cat).type is D.MATCH
    odd = reconcile_pair(claim("metoprolol", intake=amt("metoprolol", 30)), o, cat)
    assert odd.type is D.STRENGTH_MISMATCH


def test_same_ratio_scaled_is_strength_not_ratio_mismatch(cat):
    c = claim("Augmentin", st(("amoxicillin", 1000), ("clavulanic acid", 250)))
    o = pack("Augmentin 500/125", st(("amoxicillin", 500), ("clavulanic acid", 125)))
    assert reconcile_pair(c, o, cat).type is D.STRENGTH_MISMATCH


def test_reconcile_pair_is_deterministic(cat):
    c, o = CASES[2][1], CASES[2][2]
    assert reconcile_pair(c, o, cat) == reconcile_pair(c, o, cat)


# --- whole intake ------------------------------------------------------------

def test_reconcile_all_pairs_by_ingredient_and_flags_leftovers(cat):
    claims = [claim("Concor", st(("bisoprolol", 5)), cid="c1"), claim("Panadol", cid="c2")]
    packs = [pack("Glucophage 850 mg", st(("metformin", 850)), oid="o1"),
             pack("Concor 5 mg", st(("bisoprolol", 5)), oid="o2")]
    findings = {(f.claim_id, f.observation_id): f for f in reconcile_all(claims, packs, cat)}
    assert findings[("c1", "o2")].type is D.MATCH
    only_audio = findings[("c2", None)]
    assert only_audio.type is D.MISSING_MODALITY and only_audio.visual_evidence == []
    only_photo = findings[(None, "o1")]
    assert only_photo.type is D.MISSING_MODALITY and only_photo.audio_evidence == []
    assert len(findings) == 3


def test_reconcile_all_keeps_unreadable_photo_as_its_own_finding(cat):
    findings = reconcile_all([], [pack(None, readability="unreadable", oid="o9")], cat)
    assert [f.type for f in findings] == [D.UNREADABLE_SOURCE]


# --- guardrails ----------------------------------------------------------------

def test_every_type_has_a_safe_template_and_non_match_types_have_a_question():
    assert set(TEMPLATES) == set(D)
    for text in TEMPLATES.values():
        assert_no_advice(text)
    for text in PATIENT_QUESTIONS.values():
        assert_no_advice(text)


def test_findings_point_to_known_questions(cat):
    for _, c, o, expected in CASES:
        f = reconcile_pair(c, o, cat)
        if expected is D.MATCH:
            assert f.patient_question_id is None
        else:
            assert f.patient_question_id in PATIENT_QUESTIONS


@pytest.mark.parametrize("text", [
    "You should take two tablets a day.",
    "Increase your dose to 100 mg.",
    "Stop taking Concor.",
    "Please double the dose tonight.",
    "Debe tomar media tableta.",
    "Nehmen Sie zwei Tabletten.",
])
def test_advice_is_caught(text):
    with pytest.raises(AdviceLeak):
        assert_no_advice(text)
