"""Batch 24 round 8: a Spanish clock time states no amount, and a Spanish or German number joins nothing English or
Arabic after it (SPEC §2, round 8). The supervisor's round 7 review found three false matches: an English hundred
joined a German number before it ("sechs hundred" stated 600), a clock hour joined `mil` ("a las cinco mil miligramos"
stated 5 and 5000), and clock minutes joined a count ("a las ocho y cuarenta y dos pastillas" stated 40 and 42)."""

import json
from decimal import Decimal

import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all
from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.stated import stated_amounts
from anamnesis.schema import AudioTurn, IngredientAmount, PackObservation, Strength
from anamnesis.schema import DiscrepancyType as D

CAT = load_catalogue()


def finding(said, name, inn, amount, label):
    turn = AudioTurn(turn_id="turn-0", start_ms=0, end_ms=1000, transcript=said, speaker=None, lang_hint="en")
    raw = {"name_text": name, "inn": inn, "strength": None, "intake_amount": {"inn": inn, "amount": amount, "unit": "mg"},
           "regimen": None, "status": "active", "turn_ids": ["turn-0"]}
    [claim] = parse_claims_json(json.dumps({"claims": [raw]}, ensure_ascii=False), [turn])
    pack = PackObservation(observation_id="o1", label_text=label, readability="readable", visual_evidence=["r_o1"],
                           strength=Strength(ingredients=[IngredientAmount(inn=inn, amount=Decimal(amount), unit="mg")],
                                             per="tablet", release="unknown"))
    [found] = reconcile_all([claim], [pack], CAT)
    return found.type


@pytest.mark.parametrize(("said", "name", "inn", "amount", "label"), [  # the supervisor's round 7 review
    ("Ich nehme Ibuprofen und sechs hundred Milligramm ASS.", "Ibuprofen", "ibuprofen", "600", "Ibuprofen 600 mg"),
    ("Tomo Concor por la mañana y metformina a las cinco mil miligramos.", "Concor", "bisoprolol", "5", "Concor 5 mg"),
    ("Tomo Lipitor a las ocho y cuarenta y dos pastillas de paracetamol.", "Lipitor", "atorvastatin", "40",
     "Lipitor 40 mg"),
    ("Tomo Lipitor a las ocho cuarenta y dos pastillas de paracetamol.", "Lipitor", "atorvastatin", "40",
     "Lipitor 40 mg"),
])
def test_an_invented_amount_never_reaches_match(said, name, inn, amount, label):
    assert finding(said, name, inn, amount, label) is D.INSUFFICIENT_INFORMATION


@pytest.mark.parametrize(("text", "never"), [
    ("seis hundred milligrams", "600"), ("zwei thousand Milligramm", "2000"), ("seis ميه milligrams", "600"),
    ("cinco and a half mg", "5.5"), ("treinta y five mg", "35"),
])
def test_a_spanish_or_german_number_joins_no_english_or_arabic_word_after_it(text, never):
    assert Decimal(never) not in stated_amounts(text)


@pytest.mark.parametrize("text", ["siete point five milligrams", "dos point cinco miligramos"])
def test_a_decimal_begun_in_spanish_or_german_with_an_english_point_states_nothing(text):
    assert stated_amounts(text) == frozenset()


@pytest.mark.parametrize(("text", "never"), [
    ("a las cinco mil miligramos", "5000"), ("a las cinco mil miligramos", "5"),
    ("a las ocho y cuarenta y dos pastillas", "40"), ("a las ocho y cuarenta y dos pastillas", "42"),
    ("a las ocho cuarenta y dos pastillas", "42"), ("a la una y cuarenta y dos pastillas", "42"),
    ("a las 8 y cuarenta y dos pastillas", "42"), ("a las eight y cuarenta y dos pastillas", "42"),
])
def test_a_clock_hour_and_its_minutes_state_no_amount(text, never):
    assert Decimal(never) not in stated_amounts(text)


@pytest.mark.parametrize(("text", "value"), [
    ("tomo las dos pastillas", "2"),              # "the two pills": an hour before a dose word still counts
    ("a las ocho veinte miligramos", "20"),       # so do minutes before a unit word
    ("a las dos tres pastillas", "3"),            # minutes said without y are 10-59
    ("a las dos tres mil miligramos", "3000"),
    ("a las ocho trescientos cincuenta miligramos", "350"),
    ("a las ocho y cuarenta y dos pastillas", "2"),
])
def test_an_amount_after_a_clock_time_still_reads(text, value):
    assert Decimal(value) in stated_amounts(text)


def test_german_null_before_komma_is_zero():
    assert Decimal("0.5") in stated_amounts("null Komma fünf Milligramm")


@pytest.mark.parametrize(("text", "values"), [
    ("GCS eight coma three", {"8", "3"}), ("I take um eight of them", {"8"}),
    ("two hundred milligrams", {"2", "100", "200"}), ("two point five milligrams", {"2", "2.5", "5"}),
    ("point five milligrams", {"0.5", "5"}),
])
def test_english_reads_as_before(text, values):
    assert stated_amounts(text) == frozenset(Decimal(value) for value in values)
