"""Batch 3 contract: hardening from the M1 grill (evidence/grills/m1-core/effect.md). Written by the reviewer; do not edit."""

import itertools
from decimal import Decimal

import pytest
from pydantic import ValidationError

from anamnesis.core import guardrails
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.guardrails import AdviceLeak, assert_no_advice
from anamnesis.core.reconcile import reconcile_all, reconcile_pair
from anamnesis.schema import (
    AudioTurn,
    DoseRegimen,
    Finding,
    IngredientAmount,
    PackObservation,
    PatientClaim,
    Release,
    Strength,
    canonical_inn,
)
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.templates import QUESTION_FOR, TEMPLATES


@pytest.fixture(scope="module")
def cat():
    return load_catalogue()


def amt(inn, mg, unit="mg"):
    return IngredientAmount(inn=inn, amount=Decimal(str(mg)), unit=unit)


def st(*pairs, per="tablet", release="unknown"):
    return Strength(ingredients=[amt(i, a) for i, a in pairs], per=per, release=release)


def claim(name, strength=None, intake=None, inn=None, cid="c1"):
    return PatientClaim(claim_id=cid, name_text=name, inn=inn, strength=strength, intake_amount=intake,
                        status="active", audio_evidence=[f"t_{cid}"])


def pack(label, strength=None, readability="readable", inn=None, oid="o1"):
    return PackObservation(observation_id=oid, label_text=label, strength=strength, inn=inn,
                           readability=readability, visual_evidence=[f"r_{oid}"])


# --- schema hardening (#7, #12, #13) ---------------------------------------------

def test_canonical_inn_trims_casefolds_and_maps_synonyms():
    assert canonical_inn("  Bisoprolol ") == "bisoprolol"
    assert canonical_inn("Acetaminophen") == "paracetamol"


@pytest.mark.parametrize("pairs", [
    [("paracetamol", 500), ("paracetamol", 500)],
    [("Paracetamol", 500), (" paracetamol", 250)],
    [("paracetamol", 500), ("acetaminophen", 500)],
])
def test_strength_rejects_duplicate_canonical_inns(pairs):
    with pytest.raises(ValidationError):
        st(*pairs)


def test_strength_release_defaults_to_unknown():
    s = Strength(ingredients=[amt("x", 1)], per="tablet")
    assert s.release is Release.UNKNOWN
    assert {r.value for r in Release} == {"immediate", "modified", "unknown"}


def test_as_needed_is_unknown_by_default():
    assert DoseRegimen().as_needed is None
    assert DoseRegimen(as_needed=False).as_needed is False


@pytest.mark.parametrize("kw", [{"transcript": ""}, {"transcript": "x", "speaker": ""}])
def test_audio_turn_rejects_empty_text_fields(kw):
    with pytest.raises(ValidationError):
        AudioTurn(turn_id="t1", start_ms=0, end_ms=1, **kw)


# --- the text boundary (#5) -------------------------------------------------------

def base_finding(**over):
    kw = dict(finding_id="f1", type=D.STRENGTH_MISMATCH, claim_id="c1", observation_id="o1",
              audio_evidence=["t1"], visual_evidence=["r1"], needs_clinician_review=True,
              clinician_note=TEMPLATES[D.STRENGTH_MISMATCH],
              patient_question_id=QUESTION_FOR[D.STRENGTH_MISMATCH])
    kw.update(over)
    return Finding(**kw)


def test_finding_accepts_only_the_canonical_text():
    base_finding()
    with pytest.raises(ValidationError):
        base_finding(clinician_note="Continue your current dose.")
    with pytest.raises(ValidationError):
        base_finding(patient_question_id="q_made_up")
    with pytest.raises(ValidationError):
        base_finding(patient_question_id=None)


def test_finding_side_ids_follow_the_evidence():
    with pytest.raises(ValidationError):  # two-sided type without the claim id
        base_finding(claim_id=None)
    t = D.MISSING_MODALITY
    one_sided = dict(type=t, clinician_note=TEMPLATES[t], patient_question_id=QUESTION_FOR[t], visual_evidence=[])
    base_finding(**one_sided, observation_id=None)
    with pytest.raises(ValidationError):  # observation id without visual evidence
        base_finding(**one_sided)


def test_templates_live_in_schema_and_cover_every_type():
    assert guardrails.TEMPLATES is TEMPLATES and guardrails.QUESTION_FOR is QUESTION_FOR
    assert set(TEMPLATES) == set(D) and set(QUESTION_FOR) == set(D)
    assert QUESTION_FOR[D.MATCH] is None
    assert all(QUESTION_FOR[t] in guardrails.PATIENT_QUESTIONS for t in D if t is not D.MATCH)


@pytest.mark.parametrize("text", [
    "Split the tablet.",
    "Continue your current dose.",
    "Keep taking it as before.",
    "It is safe to use two.",
    "Halve the dose tonight.",
])
def test_advice_misses_from_m1_are_now_caught(text):
    with pytest.raises(AdviceLeak):
        assert_no_advice(text)


# --- catalogue (#2, #3, #8) ----------------------------------------------------

def test_catalogue_entries_carry_release_and_splittable(cat):
    by_brand = {e.brand: e for e in cat.entries}
    assert by_brand["Beloc-Zok"].release is Release.MODIFIED
    assert by_brand["Concor"].release is Release.IMMEDIATE
    assert by_brand["Beloc-Zok"].splittable is True
    assert by_brand["Lipitor"].splittable is False
    assert by_brand["Glucophage"].splittable is None


@pytest.mark.parametrize("text,inns", [
    ("Beloc Zok 100", {"metoprolol"}),
    ("beloc-zok 100 mg", {"metoprolol"}),
    ("Panadol Extra", {"paracetamol", "caffeine"}),
])
def test_resolution_treats_hyphens_as_spaces(cat, text, inns):
    assert cat.resolve(text).inns == frozenset(inns)


@pytest.mark.parametrize("text", ["I use Concor and Panadol Extra", "Lipitor, Glucophage"])
def test_text_naming_two_products_is_unresolved(cat, text):
    assert cat.resolve(text) is None


def test_brand_implied_facts_only_from_brand_names(cat):
    assert cat.implied_release("Beloc-Zok 100 mg") is Release.MODIFIED
    assert cat.implied_release("metoprolol 100 mg") is Release.UNKNOWN
    assert cat.splittable("Beloc-Zok") is True
    assert cat.splittable("metoprolol") is None


# --- decision order v2 (#1-#4, #7) ----------------------------------------------

BELOC = pack("Beloc-Zok 100 mg", st(("metoprolol", 100)))

CASES = [
    # 1: nothing comparable is never a match
    ("no_amounts_claim", claim("Concor"), pack("Concor 5 mg", st(("bisoprolol", 5))), D.INSUFFICIENT_INFORMATION),
    ("no_amounts_pack", claim("Concor", st(("bisoprolol", 5))), pack("Concor 5 mg"), D.INSUFFICIENT_INFORMATION),
    # 2: the Beloc-Zok succinate-ER trap
    ("release_unknown_vs_er", claim("metoprolol", st(("metoprolol", 100))), BELOC, D.INSUFFICIENT_INFORMATION),
    ("release_ir_vs_er", claim("metoprolol", st(("metoprolol", 100), release="immediate")), BELOC, D.FORMULATION_MISMATCH),
    ("brand_er_vs_er", claim("Beloc-Zok", st(("metoprolol", 100))), BELOC, D.MATCH),
    # 3: splittability is per product
    ("half_scored_er", claim("metoprolol", intake=amt("metoprolol", 50)), BELOC, D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH),
    ("half_not_splittable", claim("atorvastatin", intake=amt("atorvastatin", 10)),
     pack("Lipitor 20 mg", st(("atorvastatin", 20))), D.STRENGTH_MISMATCH),
    ("half_unknown_splittable", claim("metformin", intake=amt("metformin", 425)),
     pack("Glucophage 850 mg", st(("metformin", 850))), D.INSUFFICIENT_INFORMATION),
    ("half_capsule", claim("amlodipine", intake=amt("amlodipine", 5)),
     pack("Norvasc 10 mg", st(("amlodipine", 10), per="capsule")), D.STRENGTH_MISMATCH),
    ("liquid", claim("paracetamol", intake=amt("paracetamol", 250)),
     pack("Panadol", st(("paracetamol", 120), per="ml")), D.INSUFFICIENT_INFORMATION),
    # 4: equal strengths no longer hide the intake
    ("intake_after_match", claim("Concor", st(("bisoprolol", 5)), intake=amt("bisoprolol", 10)),
     pack("Concor 5 mg", st(("bisoprolol", 5))), D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH),
    # 7: identity from the strength, conflicts, synonyms
    ("extraction_conflict", claim("Concor", st(("amlodipine", 5))), pack("Concor 5 mg", st(("bisoprolol", 5))),
     D.INSUFFICIENT_INFORMATION),
    ("synonym", claim("acetaminophen", st(("acetaminophen", 500))), pack("Panadol 500 mg", st(("paracetamol", 500))),
     D.MATCH),
    ("explicit_inn_hides_combo", claim("Panadol", st(("paracetamol", 500))),
     pack("Panadol Extra", st(("paracetamol", 500), ("caffeine", 65)), inn="paracetamol"), D.INGREDIENT_MISMATCH),
]


@pytest.mark.parametrize("name,c,o,expected", CASES, ids=[c[0] for c in CASES])
def test_decision_order_v2(cat, name, c, o, expected):
    f = reconcile_pair(c, o, cat)
    assert f.type is expected
    assert f.clinician_note == TEMPLATES[expected] and f.patient_question_id == QUESTION_FOR[expected]


# --- pairing (#6) ----------------------------------------------------------------

def triples(findings):
    return {(f.claim_id, f.observation_id, f.type) for f in findings}


def test_pairing_prefers_exact_strength_over_photo_order(cat):
    claims = [claim("Concor", st(("bisoprolol", 5)), cid="c5"), claim("Concor", st(("bisoprolol", 10)), cid="c10")]
    packs = [pack("Concor 10 mg", st(("bisoprolol", 10)), oid="o10"), pack("Concor 5 mg", st(("bisoprolol", 5)), oid="o5")]
    assert triples(reconcile_all(claims, packs, cat)) == {("c5", "o5", D.MATCH), ("c10", "o10", D.MATCH)}


def test_pairing_prefers_exact_identity_over_overlap(cat):
    claims = [claim("Panadol", st(("paracetamol", 500)), cid="cp"),
              claim("Panadol Extra", st(("paracetamol", 500), ("caffeine", 65)), cid="cx")]
    packs = [pack("Panadol Extra", st(("paracetamol", 500), ("caffeine", 65)), oid="ox"),
             pack("Panadol 500 mg", st(("paracetamol", 500)), oid="op")]
    assert triples(reconcile_all(claims, packs, cat)) == {("cp", "op", D.MATCH), ("cx", "ox", D.MATCH)}


def test_findings_do_not_depend_on_input_order(cat):
    claims = [claim("Concor", st(("bisoprolol", 5)), cid="a"), claim("Panadol", st(("paracetamol", 500)), cid="b"),
              claim("metoprolol", intake=amt("metoprolol", 50), cid="c")]
    packs = [pack("Concor 5 mg", st(("bisoprolol", 5)), oid="x"),
             pack("Panadol Extra", st(("paracetamol", 500), ("caffeine", 65)), oid="y"),
             pack("Beloc-Zok 100 mg", st(("metoprolol", 100)), oid="z"),
             pack(None, readability="unreadable", oid="w")]
    expected = triples(reconcile_all(claims, packs, cat))
    for cs in itertools.permutations(claims):
        for ps in itertools.permutations(packs):
            assert triples(reconcile_all(list(cs), list(ps), cat)) == expected


def test_unreadable_pack_never_pairs_even_with_an_inn(cat):
    packs = [pack(None, readability="unreadable", inn="bisoprolol", oid="blurry"),
             pack("Concor 5 mg", st(("bisoprolol", 5)), oid="clear")]
    found = triples(reconcile_all([claim("Concor", st(("bisoprolol", 5)))], packs, cat))
    assert ("c1", "clear", D.MATCH) in found and (None, "blurry", D.UNREADABLE_SOURCE) in found
