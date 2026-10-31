"""Batch 23 contract, round 6: the supervisor's round 5 review (evidence/batches/23/supervisor.md, Round 5) and the
CEO's differential check after round 5. Written by the CEO; Muse must not edit it.

- The refusal missed an amount printed beside its volume: a `.` of `B.P.` or `approx.` ended the sentence, and the
  before-form allowed nothing between the amount and the connector (`250 mg base/5 ml`, `250 mg in each 5 ml`). A
  sentence now ends at a `.` only before a capital letter, and the before-form takes up to three words.
- A pack that prints a per-volume strength (`120 mg/5 ml`) nulls a reading per dose, tablet or capsule: a dosing line
  or another product's line was satisfying the print.
- `mililitros`, `cm3`, `micrograms`; a bracket after a water word exempts only a lone volume; a hyphen with spaces
  around it isn't `water-based`.
- The reading's own per-ml or per-dose print later in the volume's sentence doesn't refuse it (`3 ml pen, 100 U/ml`),
  and a bracket that closes after the volume doesn't hide the water (`a glass (200 ml) of water`). A tablet print is
  matched by proximity, so it still refuses.
"""

import json
from decimal import Decimal

import pytest

from anamnesis.providers.spark import parse_label_json


def label(text, *parts, per="ml"):
    ingredients = [{"inn": inn, "amount": amount, "unit": unit} for inn, amount, unit in parts]
    return json.dumps({"label_text": text, "inn": parts[0][0], "country": None, "readability": "readable",
                       "strength": {"ingredients": ingredients, "per": per, "release": "unknown"}})


P250 = ("paracetamol", "250", "mg")


@pytest.mark.parametrize("text,part", [
    # the refusal: an abbreviation's `.` stays in the sentence (supervisor round 5 #1)
    ("Each 5 ml contains Paracetamol B.P. 250 mg. Also as 250 mg/ml drops", P250),
    ("Each 5 ml contains Paracetamol Ph.Eur. 250 mg\nParacetamol 250 mg/ml drops also available", P250),
    ("Each 5 ml contains Paracetamol B.P. 250 mg. Panadol 250 mg tablets also available", P250),
    ("Each 5 ml contains Paracetamol USP. 250 mg; 250 mg tablets also available", P250),
    ("Each 5 ml contains approx. 250 mg. 250 mg/ml drops", P250),
    # the refusal: words between the amount and the connector, and `each` after it (#1)
    ("Paracetamol 250 mg in each 5 ml. 250 mg/ml drops also available", P250),
    ("Paracetamol 250 mg base/5 ml. 250 mg/ml drops", P250),
    ("Paracetamol 250 milligrams per 5 ml. 250 mg/ml drops", P250),
    # a per-volume strength on the pack: a dosing line or another product's line isn't the reading's print (#2)
    ("Paracetamol 120 mg/5 ml. Children 6-12 years: 250 mg per dose", P250),
    ("Paracetamol 120 mg/5 ml. Equivalent to half a 250 mg tablet", P250),
    ("Paracetamol 250 mg oral suspension, not tablets. Shake. 5 ml", P250),
    # volumes spelled other ways (#3)
    ("Cada 5 mililitros contienen 250 mg", P250),
    ("Each 5 cm3 contains 250 mg", P250),
    ("Each 5 cm³ contains 250 mg", P250),
    ("شراب ٢٥٠ مجم/٥ ملي", P250),
    ("كل ٥ ملي تحتوي على ٢٥٠ مجم", P250),
    # brackets after a water word hold more than a volume (#4)
    ("Reconstitute with water (each 5 ml then contains 250 mg)", P250),
    ("Reconstitute with water (5 ml contains 250 mg)", P250),
])
@pytest.mark.parametrize("per", ["ml", "dose", "tablet"])
def test_an_amount_beside_its_volume_drops_the_strength(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text,part,per", [
    # the reading's own print after the volume (CEO's differential check; supervisor round 5 #5)
    ("Lantus SoloStar 3 ml pen, 100 U/ml", ("insulin glargine", "100", "iu"), "ml"),
    ("Lantus SoloStar 3 ml pen, 100 U/ml", ("insulin glargine", "100", "iu"), "dose"),
    ("NovoRapid FlexPen 3 ml, 100 units/ml", ("insulin aspart", "100", "iu"), "ml"),
    ("Amoxil oral drops 20 ml, 100 mg/ml", ("amoxicillin", "100", "mg"), "ml"),
    ("Each 10 ml bottle contains 50 mg/ml", ("paracetamol", "50", "mg"), "ml"),
    ("Each 15 ml dropper bottle contains 40 mg/ml", ("ibuprofen", "40", "mg"), "ml"),
    ("Each 2 ml ampoule contains 40 mg furosemide (20 mg/ml)", ("furosemide", "20", "mg"), "ml"),
    ("Furosemide 20 mg/2 ml (10 mg/ml)", ("furosemide", "10", "mg"), "ml"),
    ("Each 10 ml canister contains 200 doses of 100 mcg per dose", ("salbutamol", "100", "mcg"), "dose"),
    ("Ventolin Evohaler 100 micrograms per actuation, 200 doses, 18 ml", ("salbutamol", "100", "mcg"), "dose"),
    # water after a bracket that closes after the volume, or a lone volume in brackets after it (#5, #4)
    ("Effervescent tablets 1000 mg. Dissolve one tablet in a glass (200 ml) of water", ("ascorbic acid", "1000", "mg"),
     "tablet"),
    ("Fosfomycin 3 g granules: dissolve one sachet in a glass (150 ml) of water", ("fosfomycin", "3", "g"), "dose"),
    ("Disolver un sobre en un vaso (200 ml) de agua. 13,8 g", ("macrogol", "13.8", "g"), "dose"),
    ("Vitamin C 1000 mg. Dissolve one tablet in a glass of water (approx. 200 ml)", ("ascorbic acid", "1000", "mg"),
     "tablet"),
    # a dash with spaces after the water word isn't `water-based` (#6)
    ("يذاب القرص في ٢٠٠ مل ماء - فيتامين سي ١٠٠٠ مجم", ("ascorbic acid", "1000", "mg"), "tablet"),
])
def test_the_readings_own_print_or_water_keeps_it(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is not None
    assert reading.strength.ingredients[0].amount == Decimal(part[1])


@pytest.mark.parametrize("text,part,per", [
    ("Each 2 ml ampoule contains 40 mg furosemide (20 mg/ml)", ("furosemide", "40", "mg"), "ml"),
    ("Furosemide 20 mg/2 ml (10 mg/ml)", ("furosemide", "20", "mg"), "ml"),
    ("Lantus SoloStar 3 ml pen, 100 U/ml", ("insulin glargine", "100", "iu"), "tablet"),
    ("Each 5 ml contains 250 mg, 500 mg tablets also available", P250, "tablet"),
    ("5 ml syrup\n500 mg capsules", ("paracetamol", "500", "mg"), "capsule"),
    ("Dissolve 500 mg in a glass (200 ml) of water", ("paracetamol", "500", "mg"), "ml"),
])
def test_an_amount_beside_the_volume_still_refuses_another_print(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is None
