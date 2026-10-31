"""Batch 23 contract, round 5: a strength is kept beside a dose volume only when each amount is printed in the
reading's own unit (SPEC §2), after the supervisor's round 4 review (evidence/batches/23/supervisor.md, Round 4).
Written by the CEO; Muse must not edit it.

Round 4's clause rule still kept the fivefold error where water to dissolve in was named anywhere in a clause (the
powder-for-suspension cartons) and where a spoon carried no ml number. Round 5 drops the clauses: water to dissolve in
belongs to one volume, spoons count, and a counting volume nulls the strength unless the amount is printed per 1 ml,
per dose or per tablet, and not also printed over a volume. The earlier rounds' contracts still hold, except two keeps
that now fail closed on purpose (marked in test_b23_coverage.py and test_b23_round4.py).
"""

import json
from decimal import Decimal

import pytest

from anamnesis.providers.spark import parse_label_json


def label(text, *parts, per="ml"):
    ingredients = [{"inn": inn, "amount": amount, "unit": unit} for inn, amount, unit in parts]
    return json.dumps({"label_text": text, "inn": parts[0][0], "country": None, "readability": "readable",
                       "strength": {"ingredients": ingredients, "per": per, "release": "unknown"}})


def kept(text, parts, per):
    reading = parse_label_json(label(text, *parts, per=per), "r1")
    return reading.strength is not None and \
        [part.amount for part in reading.strength.ingredients] == [Decimal(amount) for _, amount, _ in parts]


A250, P250, P125, P120 = (("amoxicillin", "250", "mg"), ("paracetamol", "250", "mg"), ("paracetamol", "125", "mg"),
                          ("paracetamol", "120", "mg"))


@pytest.mark.parametrize("text,part", [
    # water to dissolve in, named beside the strength's own volume (supervisor round 4 #1)
    ("Amoxicillin 250 mg/5 ml when reconstituted with water", A250),
    ("Powder for oral suspension 250 mg/5 ml (add 60 ml water)", A250),
    ("Reconstitute with 60 ml of water to give 250 mg/5 ml", A250),
    ("مسحوق لتحضير معلق ٢٥٠ مجم/٥ مل بعد إضافة ماء", A250),
    ("Cada 5 ml contienen 250 mg (reconstituir con agua)", A250),
    ("Paracetamol 250 mg/5 ml in water", P250),
    ("Water-free suspension 250 mg/5 ml", P250),
    ("Each 5 ml reconstituted with water contains 250 mg", A250),
    ("Cada 5 ml reconstituidos con agua contienen 250 mg", A250),
    ("كل ٥ مل بعد التحضير بالماء تحتوي على ٢٥٠ مجم", A250),
    ("Each 5 ml contains water, sorbitol and paracetamol 250 mg", P250),
    ("Vitamin C 1000 mg per 200 ml of water", ("ascorbic acid", "1000", "mg")),
    # a spoon or a measure without a number in ml (#2)
    ("Each teaspoonful contains paracetamol 125 mg", P125),
    ("كل ملعقة صغيرة تحتوي على ١٢٥ مجم", P125),
    ("Cada cucharadita contiene 125 mg", P125),
    ("Chaque cuillère contient 125 mg", P125),
    ("125 mg per teaspoon", P125),
    ("125 mg per measure", P125),
    ("Each dessertspoonful contains 125 mg", P125),
    # another line's per-ml print doesn't rescue the strength's own volume (#3)
    ("Paracetamol 250 mg / 5 ml. Paracetamol 250 mg/ml drops also available", P250),
    ("Paracetamol 120 mg/5 ml. Sorbitol 120 mg/ml", P120),
    ("Ibuprofen 100 mg/5 ml, Ibuprofen 100 mg/ml? 40 mg/ml drops", ("ibuprofen", "100", "mg")),
    ("Each 5 ml contains 250 mg. Paracetamol 250 mg/ml drops also available", P250),
    ("Each 5 ml of reconstituted suspension contains amoxicillin 250 mg. Amoxicillin 250 mg/ml drops", A250),
    ("Per 5 ml\nParacetamol 250 mg\nParacetamol 250 mg/ml drops", P250),
    ("Each 5 ml contains 250 mg. Also available as 250 mg tablets", P250),
    # a tablet word that isn't the amount's own (#4)
    ("Paracetamol 250 mg\nper 5 ml\nAlso available as 500 mg tablets", P250),
    ("Paracetamol 250 mg\n/5 ml\nNot for tablets use", P250),
    ("Each 5 ml contains 250 mg. Tablets also available", P250),
    ("Each 5 ml contains 250 mg\nTablets also available", P250),
    ("Each 5 ml contains 250 mg; tablets 500 mg", P250),
    ("Paracetamol syrup 250 mg. Tablets also available. Dose: 5 ml", P250),
    ("Panadol 500 mg\n24 tablets, 100 ml bottle", ("paracetamol", "500", "mg")),
])
@pytest.mark.parametrize("per", ["ml", "dose", "tablet"])
def test_a_dose_volume_drops_a_strength_not_printed_in_its_own_unit(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text,part", [
    ("Paracetamol 120 mg in 5 ml of water", P120),
    ("Paracetamol 120 mg in 5 ml water", P120),
    ("Dissolve 500 mg in 200 ml of water", ("paracetamol", "500", "mg")),
    ("يذاب ١٠٠٠ مجم في ٢٠٠ مل من الماء", ("ascorbic acid", "1000", "mg")),
])
def test_water_to_dissolve_in_never_keeps_a_reading_per_ml(text, part):
    reading = parse_label_json(label(text, part, per="ml"), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text,parts,per", [
    # Arabic: the article and the suffixes (#5)
    ("بانادول ٥٠٠ مجم ٢٤ قرصاً. يذاب في ٢٠٠ مل من الماء", [("paracetamol", "500", "mg")], "tablet"),
    ("فوار ١٠٠٠ مجم، يذاب القرص في ٢٠٠ مل من الماء", [("ascorbic acid", "1000", "mg")], "tablet"),
    ("أوميبرازول ٢٠ مجم كبسولة، عبوة ١٤ كبسولة، الجرعة ١٠ مل", [("omeprazole", "20", "mg")], "capsule"),
    ("فيتامين سي ١٠٠٠ مجم. يذاب في ٢٠٠ مل من الماء", [("ascorbic acid", "1000", "mg")], "tablet"),
    ("ماكروجول ١٣٫٨ جم. يذاب الكيس في ١٢٥ مل من الماء", [("macrogol", "13.8", "g")], "dose"),
    # U, unidades and a per-dose print (#6)
    ("Lantus 100 U/ml, 3 ml pen", [("insulin glargine", "100", "iu")], "ml"),
    ("Insulina glargina 100 unidades/ml, pluma de 3 ml", [("insulin glargine", "100", "iu")], "ml"),
    ("Salbutamol inhaler 100 mcg per dose, 200 doses, 10 ml canister", [("salbutamol", "100", "mcg")], "dose"),
    ("Nasonex 50 mcg/dose nasal spray, 18 ml", [("mometasone", "50", "mcg")], "dose"),
    ("Salbutamol 100 mcg per actuation, 200 actuations, 10 ml", [("salbutamol", "100", "mcg")], "dose"),
    # abbreviations and brackets (#7)
    ("Movicol: dissolve one sachet in 125 ml (approx. a quarter glass) of water. 13.8 g", [("macrogol", "13.8", "g")],
     "dose"),
    ("Fizzy 1000 mg tablet. Dissolve in 200 ml (approx. one glass) of water", [("ascorbic acid", "1000", "mg")],
     "tablet"),
    # water to dissolve in, inside brackets after the water word
    ("Vitamin C 1000 mg. Dissolve in a glass of water (200 ml)", [("ascorbic acid", "1000", "mg")], "tablet"),
    ("Disolver un sobre en un vaso de agua (200 ml). 13,8 g", [("macrogol", "13.8", "g")], "dose"),
    ("Dissolve 500 mg in 60 ml of cooled boiled water", [("paracetamol", "500", "mg")], "tablet"),
    ("Dissolve 500 mg in a spoonful of water", [("paracetamol", "500", "mg")], "tablet"),
    ("Dissoudre 500 mg dans 200 ml d'eau", [("paracetamol", "500", "mg")], "tablet"),
    # an amount later in the volume's sentence refuses a rescue; one in another sentence doesn't
    ("Paracetamol 100 mg/ml oral drops. 15 ml bottle. Each ml contains 100 mg", [("paracetamol", "100", "mg")], "ml"),
    # printed per tablet beside a pack volume
    ("Concor 5 mg film-coated tablets, 5 ml measuring spoon", [("bisoprolol", "5", "mg")], "tablet"),
])
def test_a_strength_printed_in_its_own_unit_or_beside_water_is_kept(text, parts, per):
    assert kept(text, parts, per)
