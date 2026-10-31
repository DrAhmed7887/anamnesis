"""Batch 24 round 2: the supervisor's round 1 review (evidence/batches/24/supervisor.md), pinned (SPEC §2, round 2)."""

import json
import unicodedata
from decimal import Decimal

import pytest

from anamnesis.core.catalogue import load_catalogue, normalise
from anamnesis.core.reconcile import reconcile_all
from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.stated import stated_amounts
from anamnesis.schema import AudioTurn, IngredientAmount, PackObservation, PatientClaim, Strength
from anamnesis.schema import DiscrepancyType as D

CAT = load_catalogue()


def parse(said, **fields):
    turn = AudioTurn(turn_id="turn-0", start_ms=0, end_ms=1000, transcript=said, speaker=None, lang_hint="en")
    claim = {"name_text": "Panadol", "inn": None, "strength": None, "intake_amount": None, "regimen": None,
             "status": "active", "turn_ids": ["turn-0"], **fields}
    return parse_claims_json(json.dumps({"claims": [claim]}, ensure_ascii=False), [turn])[0]


def line(inn, amount):
    return {"inn": inn, "amount": amount, "unit": "mg"}


def strength(*lines):
    return {"ingredients": list(lines), "per": "tablet", "release": "unknown"}


def pack(label, *parts, release="unknown"):
    return PackObservation(observation_id="o1", label_text=label, readability="readable", visual_evidence=["r_o1"],
                           strength=Strength(ingredients=[IngredientAmount(inn=inn, amount=Decimal(amount), unit="mg")
                                                          for inn, amount in parts], per="tablet", release=release))


def finding(claim, observation):
    [found] = reconcile_all([claim], [observation], CAT)
    return found.type


# --- #1: a junk line relabelled to the brand never reaches match ----------------------------------------------

def test_an_unsaid_second_ingredient_drops_the_strength():
    claim = parse("I take Panadol, 500 mg with 65 mg, two tablets in the morning.",
                  strength=strength(line("caffeine", "65"), line("paracetamol", "500")))
    assert claim.strength is None and claim.intake_amount is None
    assert finding(claim, pack("Panadol 500 mg tablets", ("paracetamol", "500"))) is D.INSUFFICIENT_INFORMATION


@pytest.mark.parametrize(("lines", "packed"), [
    ((line("bisoprolol", "5"), line("", "10")), "10"),
    ((line("bisoprolol", "10"), line("string", "5")), "5"),
])
def test_a_junk_line_never_matches_whichever_comes_first(lines, packed):
    claim = parse("Concor. I used to take ten milligrams, now five milligrams.", name_text="Concor",
                  strength=strength(*lines))
    assert finding(claim, pack(f"Concor {packed} mg", ("bisoprolol", packed))) is D.INSUFFICIENT_INFORMATION


def test_two_lines_for_one_ingredient_are_a_conflict_in_the_reconciler_too():
    claim = PatientClaim(claim_id="c1", name_text="Panadol", status="active", audio_evidence=["t1"],
                         strength=Strength(ingredients=[IngredientAmount(inn="Panadol", amount=Decimal(65), unit="mg"),
                                                        IngredientAmount(inn="paracetamol", amount=Decimal(500),
                                                                         unit="mg")],
                                           per="tablet", release="unknown"))
    assert finding(claim, pack("Panadol 500 mg", ("paracetamol", "500"))) is D.INSUFFICIENT_INFORMATION


# --- #2: "mil" is a thousand only in Spanish -----------------------------------------------------------------

@pytest.mark.parametrize("text", ["Panadol, I take five mil twice a day.", "a mil syringe", "ten mil of syrup"])
def test_english_mil_states_no_thousand(text):
    assert not {Decimal(1000), Decimal(5000), Decimal(10000)} & stated_amounts(text)


@pytest.mark.parametrize(("text", "value"), [("dos mil miligramos", "2000"), ("mil doscientos miligramos", "1200"),
                                             ("mil miligramos", "1000")])
def test_spanish_mil_is_still_a_thousand(text, value):
    assert Decimal(value) in stated_amounts(text)


def test_a_thousand_from_english_mil_never_reaches_match():
    claim = parse("Panadol, I take five mil twice a day.", intake_amount=line("paracetamol", "1000"))
    assert claim.intake_amount is None
    assert finding(claim, pack("Panadol 1000 mg", ("paracetamol", "1000"))) is D.INSUFFICIENT_INFORMATION


# --- #3: a salt said inside a German compound is grounded ------------------------------------------------------

def test_a_salt_said_in_a_german_compound_is_kept():
    claim = parse("Ich nehme Beloc-Zok, das ist Metoprololtartrat, 50 mg am Morgen.", name_text="Beloc-Zok",
                  inn="metoprolol tartrate", intake_amount=line("metoprolol", "50"))
    assert normalise(claim.inn) == "metoprolol tartrate"
    succinate = pack("Beloc-Zok 50 mg Metoprololsuccinat Retardtabletten", ("metoprolol succinate", "50"),
                     release="modified")
    assert finding(claim, succinate) is D.FORMULATION_MISMATCH


# --- #4-#6: halves, the decimal words, German zero and decomposed accents ---------------------------------------

@pytest.mark.parametrize(("text", "value"), [
    ("zwei halbe Tabletten", "2.5"),           # two half tablets: a German half joins nothing
    ("two media reports said five", "2.5"),
    ("she was in a coma two years ago", "0.2"),  # "coma" is a decimal point only after a number
])
def test_these_never_state_the_value(text, value):
    assert Decimal(value) not in stated_amounts(text)


@pytest.mark.parametrize(("text", "value"), [
    ("uno y medio comprimidos", "1.5"), ("dos coma cinco miligramos", "2.5"), ("zwei Komma null fünf Milligramm", "2.05"),
    (unicodedata.normalize("NFD", "veintitrés miligramos"), "23"),
    (unicodedata.normalize("NFD", "fünfhundert Milligramm"), "500"),
])
def test_these_state_the_value(text, value):
    assert Decimal(value) in stated_amounts(text)


# --- #7: a label made only of amount words is never grounded --------------------------------------------------

@pytest.mark.parametrize("label", ["milligrams", "five milligrams", "units", "treinta y cinco", "two and a half",
                                   "dos coma cinco"])
def test_an_amount_only_label_takes_the_claims_name(label):
    claim = parse("Farxiga five milligrams every morning", name_text="Farxiga", intake_amount=line(label, "5"))
    assert claim.intake_amount is not None and normalise(claim.intake_amount.inn) == "farxiga"
