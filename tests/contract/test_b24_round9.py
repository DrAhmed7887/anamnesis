"""Batch 24 round 9: a number run never mixes languages, and only `la una`, or `las` with a number up to 24, is a
clock time (SPEC §2, round 9). The supervisor's round 8 review found two false matches. A German strength repeated
in English ("zweihundertfünfzig two hundred fifty Milligramm") stated 150, and the English "LA" of long-acting brands
read as a Spanish clock hour ("Cardizem LA four hundred twenty milligrams" stated 120)."""

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
    return frozenset(Decimal(number) for number in numbers)


@pytest.mark.parametrize(("said", "name", "inn", "amount", "label"), [  # the supervisor's round 8 review
    ("Ich nehme Pregabalin zweihundertfünfzig two hundred fifty Milligramm.", "Pregabalin", "pregabalin", "150",
     "Pregabalin 150 mg"),
    ("I take Cardizem LA four hundred twenty milligrams of diltiazem.", "Cardizem LA", "diltiazem", "120",
     "Cardizem LA 120 mg"),
    ("Inderal LA two hundred fifty mg of propranolol.", "Inderal LA", "propranolol", "150", "Inderal LA 150 mg"),
    ("Tomo Concor y a las nueve menos cinco mil miligramos de paracetamol.", "Concor", "bisoprolol", "5",
     "Concor 5 mg"),
])
def test_an_invented_amount_never_reaches_match(said, name, inn, amount, label):
    assert finding(said, name, inn, amount, label) is D.INSUFFICIENT_INFORMATION


@pytest.mark.parametrize(("text", "found"), [  # what the code before batch 24 states for the English words
    ("Ich nehme Pregabalin zweihundertfünfzig two hundred fifty Milligramm.", values(2, 50, 100, 250)),
    ("vierhundertzwanzig four hundred twenty", values(4, 20, 100, 420)),
    ("dos mil quinientos two thousand five hundred", values(2, 5, 100, 1000, 2500)),
    ("quinientos fifty milligrams", values(50)), ("fünfhundert fifty Milligramm", values(50)),
])
def test_a_spanish_or_german_number_joins_no_english_number_after_it(text, found):
    assert stated_amounts(text) == found


def test_an_english_number_joins_no_spanish_number_after_it():
    found = stated_amounts("two hundred cincuenta milligrams")
    assert Decimal(250) not in found and Decimal(200) in found


@pytest.mark.parametrize(("text", "found"), [  # English and Arabic with a long-acting "LA" read as before batch 24
    ("I take Cardizem LA four hundred twenty milligrams of diltiazem.", values(4, 20, 100, 420)),
    ("Inderal LA two hundred fifty mg", values(2, 50, 100, 250)),
    ("Adalat LA thirty milligrams every morning", values(30)),
    ("باخد Adalat LA 30 ملغ", values(30)),
    ("Adalat LA 1 tablet", values(1)),
])
def test_la_after_a_brand_is_no_clock_time(text, found):
    assert stated_amounts(text) == found


@pytest.mark.parametrize(("text", "never"), [
    ("a las nueve menos cinco mil miligramos", "5"),          # minutes after menos
    ("a las cinco menos veinte mil gramos", "20000"),
    ("a la una menos diez y media pastilla", "10.5"),
    ("hasta la una y treinta y cinco mil doscientos miligramos", "5"),   # compound minutes
    ("hasta la una y treinta y cinco mil doscientos miligramos", "5200"),
    ("a las ocho y diez y cinco mil miligramos", "5"),
    ("a las 8 tomo dos pastillas", "8"),                      # a digit hour
    ("treinta y ein mg", "31"),                               # y joins no German article
])
def test_these_never_state_the_value(text, never):
    assert Decimal(never) not in stated_amounts(text)


@pytest.mark.parametrize(("text", "value"), [
    ("Tomo la ochocientos setenta y cinco miligramos", "875"),     # la is an hour only before una
    ("tomo las cuarenta y dos pastillas", "42"),                   # las is an hour only up to 24
    ("tomo las 500 de paracetamol", "500"),
    ("tomo las 300 y cuarenta y dos pastillas", "42"),            # digits above 24 are no hour, so no minutes follow
    ("las 2 pastillas", "2"),                                      # a digit hour before a dose word counts
    ("hasta la una y treinta y cinco mil doscientos miligramos", "1200"),
    ("a las ocho y diez y doscientos cincuenta miligramos", "250"),  # only a 1-9 joins the minutes
    ("a las ocho y cuarenta y dos pastillas", "2"),                # compound minutes before a dose word count
])
def test_these_still_state_the_value(text, value):
    assert Decimal(value) in stated_amounts(text)
