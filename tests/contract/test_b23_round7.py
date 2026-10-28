"""Batch 23 contract, round 7: three gaps in the SPEC's own wording, found by the CEO's differential check after
round 6 (evidence/batches/23/reference.md, Round 7). Written by the CEO; Muse must not edit it.

- The refusal's before-form now skips text in brackets, as the water rule does: "250 mg (as amoxicillin trihydrate)
  per 5 ml" is the standard wording, and round 6 kept it read as 250 per ml beside a 250 mg/ml line.
- The Arabic spoon is the stem `ملعق` with any letters after it, so the dual `ملعقتين` counts.
- A `.` ends a sentence only before spaces and a capital, not before a line break: "B.P.\nParacetamol 250 mg". And
  never after a word of one to three Latin letters, which is how "Ph. Eur." and "B. P." are printed (the supervisor's
  round 6 review, evidence/batches/23/supervisor.md, Round 6 #1).
- Brackets between the amount and the connector also make a volume count outright (#2); a spelled-out Arabic
  milligram (`مللي جرام`) is a unit, not ml (#4); and a drop is a dose (#5).
"""

import json
from decimal import Decimal

import pytest

from anamnesis.providers.spark import parse_label_json


def label(text, *parts, per="ml"):
    ingredients = [{"inn": inn, "amount": amount, "unit": unit} for inn, amount, unit in parts]
    return json.dumps({"label_text": text, "inn": parts[0][0], "country": None, "readability": "readable",
                       "strength": {"ingredients": ingredients, "per": per, "release": "unknown"}})


A250, P250 = ("amoxicillin", "250", "mg"), ("paracetamol", "250", "mg")


@pytest.mark.parametrize("text,part", [
    ("Paracetamol 250 mg (as base) per 5 ml. 250 mg/ml drops", P250),
    ("Amoxicillin 250 mg (as trihydrate) per 5 ml. Amoxicillin 250 mg/ml drops", A250),
    ("Amoxicillin 250 mg (as amoxicillin trihydrate)/5 ml. Amoxicillin 250 mg/ml drops", A250),
    ("Amoxicillin 250 mg [as trihydrate] in each 5 ml. 250 mg/ml drops", A250),
    ("باراسيتامول ٢٥٠ مجم لكل ملعقتين", P250),
    ("كل ملعقتين تحتوي على ٢٥٠ مجم", P250),
    ("Each 5 ml contains Paracetamol B.P.\nParacetamol 250 mg. 250 mg/ml drops", P250),
    ("Each 5 ml contains Amoxicillin Ph. Eur. 250 mg. Also 250 mg/ml drops", A250),
    ("Each 5 ml contains B.P. Paracetamol 250 mg. Also 250 mg/ml drops", P250),
    ("Each 5 ml contains Paracetamol B. P. 250 mg. Also 250 mg/ml drops", P250),
    ("Each 5 ml contains: Paracetamol Ph. Eur.\n250 mg\n250 mg/ml drops also available", P250),
    ("Each 5 ml of suspension.\nAmoxicillin 250 mg. Amoxicillin 250 mg/ml drops", A250),
])
@pytest.mark.parametrize("per", ["ml", "dose", "tablet"])
def test_the_amounts_own_volume_drops_it(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text,part", [
    ("Each 5 ml contains Amoxicillin Ph. Eur. 250 mg. Amoxil 250 mg capsules also available", A250),
    ("Amoxicillin 125 mg (as trihydrate) per 5 ml. Amoxil 250 mg capsules", A250),
])
def test_a_suspension_line_drops_a_capsule_reading(text, part):
    reading = parse_label_json(label(text, part, per="capsule"), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text,part,per", [
    ("كونكور ٥ مللي جرام ٣٠ قرص", ("bisoprolol", "5", "mg"), "tablet"),
    ("كونكور ٥ ملليجرام أقراص", ("bisoprolol", "5", "mg"), "tablet"),
    ("أملور ١٠ ملي جرام أقراص", ("amlodipine", "10", "mg"), "tablet"),
    ("كونكور ٥ مللي جرام", ("bisoprolol", "5", "mg"), "tablet"),
    ("فنتولين ١٠٠ ميكروجرام لكل بخة، ٢٠٠ بخة، ١٨ مل", ("salbutamol", "100", "mcg"), "dose"),
    ("Vitamin D3 1000 IU per drop, 10 ml", ("colecalciferol", "1000", "iu"), "dose"),
    ("Vitamina D3 1000 UI por gota, frasco de 10 ml", ("colecalciferol", "1000", "iu"), "dose"),
    ("Insulin 100 units/ml (Lantus), 3 ml pen", ("insulin glargine", "100", "iu"), "ml"),
    ("Lantus SoloStar (insulin glargine) 3 ml pen, 100 U/ml", ("insulin glargine", "100", "iu"), "ml"),
])
def test_brackets_before_a_pack_volume_keep_the_print(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is not None
    assert reading.strength.ingredients[0].amount == Decimal(part[1])
