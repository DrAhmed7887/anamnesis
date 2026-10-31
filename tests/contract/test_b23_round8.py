"""Batch 23 contract, round 8: the supervisor's round 7 review (evidence/batches/23/supervisor.md, Round 7). Written by
the CEO; Muse must not edit it.

- A salt phrase of four or five words without brackets escaped the refusal's before-form: "250 mg as amoxicillin
  trihydrate per 5 ml". It now takes up to five words, and none of them may cross a sentence end.
- «معلقة», the colloquial Egyptian spelling of «ملعقة», is a spoon; the stem «معلق» alone is a suspension, not a spoon.
"""

import json
from decimal import Decimal

import pytest

from anamnesis.providers.spark import parse_label_json


def label(text, *parts, per="ml"):
    ingredients = [{"inn": inn, "amount": amount, "unit": unit} for inn, amount, unit in parts]
    return json.dumps({"label_text": text, "inn": parts[0][0], "country": None, "readability": "readable",
                       "strength": {"ingredients": ingredients, "per": per, "release": "unknown"}})


A250, P250, P125 = ("amoxicillin", "250", "mg"), ("paracetamol", "250", "mg"), ("paracetamol", "125", "mg")


@pytest.mark.parametrize("text,part,per", [
    ("Amoxicillin 250 mg as amoxicillin trihydrate per 5 ml oral suspension. Amoxil 250 mg capsules also available",
     A250, "capsule"),
    ("Amoxicillin 250 mg as amoxicillin trihydrate per 5 ml; Amoxil 250 mg capsules also available", A250, "capsule"),
    ("أموكسيسيلين ٢٥٠ مجم على هيئة ترايهيدرات لكل ٥ مل. أموكسيل ٢٥٠ مجم كبسولات", A250, "capsule"),
    ("أموكسيسيلين ٢٥٠ مجم على هيئة أموكسيسيلين ترايهيدرات لكل ٥ مل؛ أموكسيل ٢٥٠ مجم كبسولات", A250, "capsule"),
    ("Amoxicillin 250 mg as amoxicillin trihydrate BP per 5 ml. 250 mg/ml drops", A250, "ml"),
    ("Amoxicillin 250 mg (as amoxicillin trihydrate, sugar free) per 5 ml. 250 mg/ml drops", A250, "ml"),
])
def test_a_long_salt_phrase_before_the_volume_still_refuses(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text,part", [
    ("باراسيتامول ٢٥٠ مجم لكل معلقة", P250),
    ("كل معلقة صغيرة تحتوي على ١٢٥ مجم", P125),
    ("كل معلقه تحتوي على ١٢٥ مجم", P125),
])
@pytest.mark.parametrize("per", ["ml", "dose", "tablet"])
def test_the_colloquial_spoon_counts(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is None


def test_a_sentence_end_stops_the_before_form():
    text = "Euthyrox 50 µg tablets; crush and suspend in 10 ml of liquid"
    reading = parse_label_json(label(text, ("levothyroxine", "50", "mcg"), per="tablet"), "r1")
    assert reading.strength is not None
    assert reading.strength.ingredients[0].amount == Decimal("50")
