"""Batch 24 round 10: after `las`, only a Spanish number word or digits make a clock hour, and an article joins no
number before it, of any size (SPEC §2, round 10). The supervisor's round 9 review found English number words after
`las` read as an hour: "Me tomo las two hundred fifty milligram tablets" dropped "two" and stated 150, and the English
plural "Cardizem LAs" did the same in English-only text."""

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


def values(*numbers):
    return frozenset(Decimal(str(number)) for number in numbers)


@pytest.mark.parametrize(("said", "name", "inn", "amount", "label"), [  # the supervisor's round 9 review
    ("Me tomo las two hundred fifty milligram tablets de Pregabalin.", "Pregabalin", "pregabalin", "150",
     "Pregabalin 150 mg"),
    ("Tomo Cardizem LA, las four hundred twenty milligram capsules de diltiazem.", "Cardizem LA", "diltiazem", "120",
     "Cardizem LA 120 mg"),
    ("I take two Cardizem LAs four hundred twenty milligrams each of diltiazem.", "Cardizem LA", "diltiazem", "120",
     "Cardizem LA 120 mg"),
])
def test_an_invented_amount_never_reaches_match(said, name, inn, amount, label):
    assert finding(said, name, inn, amount, label) is D.INSUFFICIENT_INFORMATION


@pytest.mark.parametrize(("text", "found"), [  # what the code before batch 24 states for these words
    ("Me tomo las two hundred fifty milligram tablets de Pregabalin.", values(2, 50, 100, 250)),
    ("I take two Cardizem LAs four hundred twenty milligrams each of diltiazem.", values(2, 4, 20, 100, 420)),
    ("las two point five", values(2, "2.5", 5)),
    ("las twenty-five hundred", values(5, 20, 100, 2500)),
])
def test_an_english_number_after_las_reads_as_before(text, found):
    assert stated_amounts(text) == found


@pytest.mark.parametrize(("text", "never"), [
    ("zweihundert Ein-Gramm-Tabletten", "201"), ("hundert Ein-Gramm-Tabletten", "101"),
    ("doscientos un miligramos", "201"), ("two hundred un miligramos", "201"), ("one thousand un gramo", "1001"),
])
def test_an_article_joins_no_number_before_it(text, never):
    assert Decimal(never) not in stated_amounts(text)


@pytest.mark.parametrize(("text", "value"), [
    ("treinta y un miligramos", "31"),         # only y joins an article
    ("zweihundert Ein-Gramm-Tabletten", "1"),  # the article still counts before its unit
])
def test_an_article_still_counts(text, value):
    assert Decimal(value) in stated_amounts(text)
