"""Batch 23 contract, round 9: the supervisor's round 8 review (evidence/batches/23/supervisor.md, Round 8), an
APPROVE with two minors. Written by the CEO; Muse must not edit it.

- The five-word before-form dropped correct tablet strengths whose dissolving line names no water: "Vitamin C 1000 mg
  effervescent tablet, dissolve in 200 ml". A tablet or capsule word between the amount and the connector means the
  volume is for dissolving, so the before-form doesn't refuse it. A syrup's salt phrase never holds one; text in
  brackets is stripped first, so "(equivalent to half a tablet)" still refuses.
- The colloquial dual «معلقتين» is a spoon.
"""

import json
from decimal import Decimal

import pytest

from anamnesis.providers.spark import parse_label_json


def label(text, *parts, per="ml"):
    ingredients = [{"inn": inn, "amount": amount, "unit": unit} for inn, amount, unit in parts]
    return json.dumps({"label_text": text, "inn": parts[0][0], "country": None, "readability": "readable",
                       "strength": {"ingredients": ingredients, "per": per, "release": "unknown"}})


VITC, PRED = ("ascorbic acid", "1000", "mg"), ("prednisolone", "5", "mg")
TABLET_LINES = [
    ("Vitamin C 1000 mg effervescent tablet, dissolve in 200 ml", VITC, "tablet"),
    ("فيتامين سي ١٠٠٠ مجم أقراص فوارة، يذاب قرص في ٢٠٠ مل", VITC, "tablet"),
    ("Prednisolone 5 mg soluble tablets: dissolve in 10 ml", PRED, "tablet"),
    ("Prednisolone 5 mg soluble tablets: dissolve in 10 ml of juice", PRED, "tablet"),
    ("Zithromax 500 mg dispersible tablets disperse in 30 ml liquid", ("azithromycin", "500", "mg"), "tablet"),
    ("Euthyrox 50 µg tablets, crush and suspend in 10 ml", ("levothyroxine", "50", "mcg"), "tablet"),
    ("Omeprazole 20 mg capsules: open and mix in 15 ml of apple juice", ("omeprazole", "20", "mg"), "capsule"),
]


@pytest.mark.parametrize("text,part,per", TABLET_LINES)
def test_a_tablet_word_before_the_volume_keeps_the_tablet_strength(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is not None
    assert reading.strength.ingredients[0].amount == Decimal(part[1])


def test_a_sentence_end_stops_the_before_form_without_a_tablet_word():
    reading = parse_label_json(label("Cetirizine 5 mg/ml oral drops. Mix in 5 ml of juice", ("cetirizine", "5", "mg"),
                                     per="ml"), "r1")
    assert reading.strength is not None
    assert reading.strength.ingredients[0].amount == Decimal("5")


@pytest.mark.parametrize("text,part,per", [(text, part, "ml") for text, part, _ in TABLET_LINES])
def test_the_same_lines_read_per_ml_still_drop(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text,part", [
    ("Paracetamol 250 mg (equivalent to half a tablet) per 5 ml. 250 mg/ml drops", ("paracetamol", "250", "mg")),
    ("باراسيتامول ٢٥٠ مجم لكل معلقتين", ("paracetamol", "250", "mg")),
    ("كل معلقتين تحتوي على ٢٥٠ مجم", ("paracetamol", "250", "mg")),
])
@pytest.mark.parametrize("per", ["ml", "dose", "tablet"])
def test_a_bracketed_tablet_word_or_the_colloquial_dual_still_drops(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is None
