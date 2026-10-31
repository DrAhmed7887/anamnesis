"""Batch 23.1 contract: the follow-ups from the supervisor's round 9 APPROVE and the Gemini 4 check of merged batch 23
(evidence/batches/23/supervisor.md, Round 9; evidence/grills/m6-timeline-final/effect.md #2-#4, #6). Written by the
CEO; Muse must not edit it.

- The tablet-word carve-out in the refusal's before-form applies only with `in` or `في`, the connectors every
  dissolving line uses. After `/`, `per`, `por`, `par` or `لكل`, a tablet word doesn't excuse the volume.
- The colloquial dual in the nominative, `معلقتان`, is pinned.
- Any number of bracket groups before the connector make a volume count outright, and a per-1-ml print may spell the
  volume in the plural.
- An estimated spend line refuses a `*-contributor` model id.
"""

import json
from decimal import Decimal

import pytest

from anamnesis.providers.spark import parse_label_json
from anamnesis.providers.spend import SessionGuard, SpendGuard


def label(text, *parts, per="ml"):
    ingredients = [{"inn": inn, "amount": amount, "unit": unit} for inn, amount, unit in parts]
    return json.dumps({"label_text": text, "inn": parts[0][0], "country": None, "readability": "readable",
                       "strength": {"ingredients": ingredients, "per": per, "release": "unknown"}})


P250 = ("paracetamol", "250", "mg")


@pytest.mark.parametrize("text,part,per", [
    ("Paracetamol 250 mg = 1 tablet per 5 ml", P250, "tablet"),
    ("Paracetamol 250 mg, same as one 250 mg tablet, per 5 ml", P250, "tablet"),
    ("Calpol 250 mg tab/5 ml", P250, "tablet"),
    ("Paracetamol 250 mg Tabs/5ml suspension", P250, "tablet"),
    ("باراسيتامول ٢٥٠ مجم ما يعادل قرص لكل ٥ مل", P250, "tablet"),
    ("باراسيتامول ٢٥٠ مجم أي قرص واحد لكل ٥ مل", P250, "tablet"),
    ("Paracetamol 250 mg comprimido por 5 ml", P250, "tablet"),
    ("Amoxicillin 250 mg capsule strength per 5 ml", ("amoxicillin", "250", "mg"), "capsule"),
])
def test_a_tablet_word_before_per_doesnt_excuse_the_volume(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text,part,per", [
    ("Vitamin C 1000 mg effervescent tablet, dissolve in 200 ml", ("ascorbic acid", "1000", "mg"), "tablet"),
    ("فيتامين سي ١٠٠٠ مجم أقراص فوارة، يذاب قرص في ٢٠٠ مل", ("ascorbic acid", "1000", "mg"), "tablet"),
    ("Disperse each 500 mg tablet in 10 ml of milk or juice", ("paracetamol", "500", "mg"), "tablet"),
    ("Omeprazole 20 mg capsules: open and mix in 15 ml of apple juice", ("omeprazole", "20", "mg"), "capsule"),
])
def test_a_dissolving_line_with_in_still_keeps_the_tablet_strength(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is not None
    assert reading.strength.ingredients[0].amount == Decimal(part[1])


@pytest.mark.parametrize("text", ["باراسيتامول ٢٥٠ مجم لكل معلقتان", "كل المعلقتان تحتوي على ٢٥٠ مجم"])
@pytest.mark.parametrize("per", ["ml", "dose", "tablet"])
def test_the_colloquial_dual_in_the_nominative_is_a_spoon(text, per):
    reading = parse_label_json(label(text, P250, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text,part,per", [
    ("Amoxicillin 125 mg (as trihydrate) (sugar free) per 5 ml. Amoxil 250 mg capsules", ("amoxicillin", "250", "mg"),
     "capsule"),
    ("Paracetamol 120 mg (as base) [anhydrous] per 5 ml. Children 6-12 years: 250 mg per dose", P250, "dose"),
])
def test_several_bracket_groups_before_the_connector_still_count(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text,part", [
    ("Paracetamol drops 100 mg per 1 millilitres, 15 ml bottle", ("paracetamol", "100", "mg")),
    ("Paracetamol gotas 100 mg por mililitros, frasco de 15 ml", ("paracetamol", "100", "mg")),
])
def test_a_plural_per_1_ml_print_is_the_readings_own(text, part):
    reading = parse_label_json(label(text, part, per="ml"), "r1")
    assert reading.strength is not None
    assert reading.strength.ingredients[0].amount == Decimal(part[1])


@pytest.mark.parametrize("model_id", ["muse-spark-1.3-contributor", " Muse-Spark-1.3-CONTRIBUTOR ",
                                      "muse-spark-contributor-1.3"])
def test_an_estimated_spend_line_refuses_a_contributor_model(tmp_path, model_id):
    ledger = tmp_path / "ledger.jsonl"
    guard = SpendGuard(ledger, Decimal("5"))
    with pytest.raises(ValueError):
        guard.charge_estimate(model_id, Decimal("0.01"), "estimate")
    with pytest.raises(ValueError):
        SessionGuard(guard, Decimal("1"), 10).charge_estimate(model_id, Decimal("0.01"), "estimate")
    assert not ledger.exists() or ledger.read_text(encoding="utf-8") == ""
