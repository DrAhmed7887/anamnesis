"""Batch 24 round 6: a Spanish or German number states an amount only before a unit or dose word, and German number
words never combine (SPEC §2, round 6). Five review rounds each found new idioms that stated a number nobody said
(evidence/batches/24/supervisor.md), so the rule is structural: outside an amount, a Spanish or German run states
nothing, whatever the phrase. English and Arabic are unchanged."""

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


@pytest.mark.parametrize(("said", "name", "inn", "amount", "label"), [  # the supervisor's round 5 review
    ("Ich nehme Concor und Paracetamol, vier Ein-Gramm-Tabletten am Tag.", "Concor", "bisoprolol", "5", "Concor 5 mg"),
    ("Tomo Concor por la mañana y a las cuatro un gramo de paracetamol.", "Concor", "bisoprolol", "5", "Concor 5 mg"),
    ("Ich nehme Lipitor abends und Paracetamol um neun ein Gramm.", "Lipitor", "atorvastatin", "10", "Lipitor 10 mg"),
    ("Tomo Lipitor a las diez thirty.", "Lipitor", "atorvastatin", "40", "Lipitor 40 mg"),
    ("Ich nehme Candesartan und gebe beim Salz Acht.", "Candesartan", "candesartan", "8", "Candesartan 8 mg"),
    ("Ich nehme Candesartan, weil ich auf meinen Blutdruck Acht gebe.", "Candesartan", "candesartan", "8",
     "Candesartan 8 mg"),
    ("Ich nehme Ibuprofen und um sechs hundert Milligramm ASS.", "Ibuprofen", "ibuprofen", "600", "Ibuprofen 600 mg"),
])
def test_an_invented_amount_never_reaches_match(said, name, inn, amount, label):
    assert finding(said, name, inn, amount, label) is D.INSUFFICIENT_INFORMATION


@pytest.mark.parametrize("text", [
    "Panadol de quinientos", "tengo cuarenta años", "el dos de mayo", "a las dos", "cada ocho horas", "dos veces al día",
    "in acht Tagen", "ich gebe Acht", "zweitausend", "dieciséis", "um halb acht", "veinte por ciento",
])
def test_a_spanish_or_german_number_outside_an_amount_states_nothing(text):
    assert stated_amounts(text) == frozenset()


@pytest.mark.parametrize(("text", "value"), [
    ("quinientos miligramos", "500"), ("acht Tabletten", "8"), ("dos comprimidos", "2"), ("dieciséis miligramos", "16"),
    ("medio comprimido", "0.5"), ("dos coma cinco miligramos", "2.5"), ("zweieinhalb Tabletten", "2.5"),
    ("cinco mg", "5"), ("fünf Milligramm", "5"), ("cinco milligrams", "5"),
])
def test_a_spanish_or_german_number_before_a_unit_or_dose_word_states_it(text, value):
    assert Decimal(value) in stated_amounts(text)


@pytest.mark.parametrize(("text", "never", "value"), [
    ("um sechs hundert Milligramm", "600", "100"),
    ("seit zweitausendzehn fünf Milligramm", "2015", "5"),
    ("vier Ein-Gramm-Tabletten", "5", "1"),
])
def test_german_numbers_never_combine(text, never, value):
    found = stated_amounts(text)
    assert Decimal(never) not in found and Decimal(value) in found


@pytest.mark.parametrize(("text", "value"), [("Concor five", "5"), ("خمسمية", "500"), ("I take two tablets", "2")])
def test_english_and_arabic_bare_numbers_are_unchanged(text, value):
    assert Decimal(value) in stated_amounts(text)
