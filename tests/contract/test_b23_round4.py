"""Batch 23 contract, round 4: one clause rule for a strength printed per a volume other than 1 ml (SPEC §2), after the
supervisor's round 3 review (evidence/batches/23/supervisor.md, Round 3 #1-#5, #7). Written by the CEO; Muse must not
edit it.

Rounds 1-3 listed wordings, and every review found more that kept a fivefold error: the standard amoxicillin carton
("Each 5 ml of reconstituted suspension contains 250 mg"), «تحتوى» and «بها», «contienen», "Per 5 ml:", a bare
"5 ml contains", a spoon, and a container's total read per ml. Round 4 asks instead whether a clause that isn't about
water prints a dose volume at all. The earlier rounds' contracts still hold.
"""

import json
from decimal import Decimal

import pytest

from anamnesis.providers.spark import parse_label_json


def label(text, *parts, per="ml"):
    ingredients = [{"inn": inn, "amount": amount, "unit": unit} for inn, amount, unit in parts]
    return json.dumps({"label_text": text, "inn": parts[0][0], "country": None, "readability": "readable",
                       "strength": {"ingredients": ingredients, "per": per, "release": "unknown"}})


P250, A250, P120 = ("paracetamol", "250", "mg"), ("amoxicillin", "250", "mg"), ("paracetamol", "120", "mg")


@pytest.mark.parametrize("text,part", [
    ("Each 5 ml of reconstituted suspension contains amoxicillin 250 mg", A250),
    ("Each 5 ml of the suspension contains 250 mg", A250),
    ("Cada 5 ml de suspensión contienen 250 mg de amoxicilina", A250),
    ("Cada 5 ml contienen 250 mg", A250),
    ("Cada 5 ml de suspensión reconstituida contiene 250 mg", A250),
    ("كل ٥ مل تحتوى على باراسيتامول ٢٥٠ مجم", P250),
    ("كل ٥ مل يحتوى على ٢٥٠ مجم", P250),
    ("كل ٥ مل من المعلق بعد التحضير تحتوي على ٢٥٠ مجم", P250),
    ("كل ٥ مل بها ٢٥٠ مجم", P250),
    ("Each 5 ml provides 250 mg", P250),
    ("Each 5 ml containing 250 mg", P250),
    ("5 ml contains paracetamol 250 mg", P250),
    ("Composition: 5 ml suspension contains 250 mg", P250),
    ("Per 5 ml: paracetamol 250 mg", P250),
    ("Per 5 ml\nParacetamol 250 mg", P250),
    ("One teaspoonful (5 ml) contains 250 mg", P250),
    ("A 5 ml spoonful contains 250 mg", P250),
    ("Chaque cuillère-mesure de 5 ml contient 250 mg", P250),
    ("Une cuillère-mesure de 5 ml contient 250 mg", P250),
    ("Syrup 250 mg per spoon (5 ml)", P250),
    ("Each spoon (5 ml) contains 250 mg", P250),
    ("Paracetamol 120 mg in 5 ml\nPurified water q.s.", P120),
    ("باراسيتامول ١٢٠ مجم في ٥ مل ماء مقطر", P120),
    ("Paracetamol 120 mg in 5 ml water-based syrup", P120),
])
@pytest.mark.parametrize("per", ["ml", "dose", "tablet"])
def test_a_dose_volume_drops_the_strength_whatever_the_wording(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text,part", [
    ("Furosemide: each 2 ml ampoule contains 40 mg", ("furosemide", "40", "mg")),
    ("Insulin: each 3 ml pen contains 300 units", ("insulin", "300", "iu")),
    ("Each 5 ml bottle: 250 mg", P250),
    ("Each 5 ml cup contains 250 mg", P250),
])
@pytest.mark.parametrize("per", ["ml", "dose"])
def test_a_containers_total_read_per_ml_is_dropped(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text,parts,per", [
    ("Insulin 100 units/ml. Each 3 ml pen contains 300 units", [("insulin", "100", "iu")], "ml"),
    ("Dissolve 500 mg in 200 ml of lukewarm drinking water", [("paracetamol", "500", "mg")], "tablet"),
    ("Dissolve 500 mg in 200 ml (a glass) of water", [("paracetamol", "500", "mg")], "tablet"),
    ("Vitamin C 1000 mg per 200 ml of water", [("ascorbic acid", "1000", "mg")], "tablet"),
    ("Each 5 ml = 1 teaspoon. Concor 5 mg tablets", [("bisoprolol", "5", "mg")], "tablet"),
    ("Every 10 ml of water: dissolve one tablet. Panadol 500 mg", [("paracetamol", "500", "mg")], "tablet"),
    ("Amoxil 25 mg/ml oral drops, 20 ml bottle", [("amoxicillin", "25", "mg")], "ml"),
])
def test_a_printed_per_ml_strength_a_water_clause_or_another_clause_keeps_it(text, parts, per):
    reading = parse_label_json(label(text, *parts, per=per), "r1")
    assert reading.strength is not None
    assert [part.amount for part in reading.strength.ingredients] == [Decimal(amount) for _, amount, _ in parts]
