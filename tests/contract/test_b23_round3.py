"""Batch 23 contract, round 3: the supervisor's round 2 review (evidence/batches/23/supervisor.md, Round 2 #2, #3) and
the Gemini 4 check of round 2 (evidence/grills/m6-timeline-r2/qm.md, #4-#6). Written by the CEO; Muse must not edit it.

- Syrup wordings that still kept a strength printed per 5 ml: a bracket or a spoon before the volume, the volume-first
  form with a spoon or "of syrup", Spanish and French, "5-mL", "millilitres", and a decimal-comma volume.
- Strengths that round 2 dropped on packs that aren't syrups: water to dissolve a tablet in, a pack size after
  "each", and a measuring line. The volume-first form now needs a contains word, and the "in" form skips water.
- The timeline's total cell spans the whole table.
"""

import json
from decimal import Decimal

import pytest

from anamnesis.agent import run_intake
from anamnesis.brief import render_brief
from anamnesis.providers.spark import parse_label_json
from anamnesis.schema.templates import TIMELINE_COLUMNS
from tests.contract import test_b19_brief as b19


def label(text, *parts, per="ml"):
    ingredients = [{"inn": inn, "amount": amount, "unit": unit} for inn, amount, unit in parts]
    return json.dumps({"label_text": text, "inn": parts[0][0], "country": None, "readability": "readable",
                       "strength": {"ingredients": ingredients, "per": per, "release": "unknown"}})


P250 = ("paracetamol", "250", "mg")
A250 = ("amoxicillin", "250", "mg")


@pytest.mark.parametrize("text,part", [
    ("Each teaspoonful (5 ml) contains paracetamol 250 mg", P250),
    ("كل ملعقة (٥ مل) تحتوي على باراسيتامول ٢٥٠ مجم", P250),
    ("Each spoonful of 5 ml contains paracetamol 250 mg", P250),
    ("Each 5 ml of syrup contains paracetamol 250 mg", P250),
    ("Each 5 ml: paracetamol 250 mg", P250),
    ("Each 2,5 ml contains paracetamol 250 mg", P250),
    ("Cada 5 ml contiene 250 mg de amoxicilina", A250),
    ("Amoxicilina 250 mg por 5 ml", A250),
    ("Chaque 5 ml contient 250 mg de paracétamol", P250),
    ("Paracétamol 250 mg par 5 ml", P250),
    ("Paracetamol 250 mg per 5-mL teaspoon", P250),
    ("Paracetamol 250 mg in 5 millilitres", P250),
    ("Paracetamol 250 mg per (5 ml)", P250),
    ("Paracetamol 250 mg/(5 ml)", P250),
    ("Paracetamol 250 mg / 2,5 ml", P250),
])
@pytest.mark.parametrize("per", ["ml", "dose", "tablet"])
def test_more_syrup_wordings_drop_the_strength(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text,parts,per", [
    ("Aspirin 300 mg. Dissolve 300 mg in 100 ml of water", [("acetylsalicylic acid", "300", "mg")], "tablet"),
    ("فيتامين سي ١٠٠٠ مجم في ٢٠٠ مل ماء", [("ascorbic acid", "1000", "mg")], "tablet"),
    ("Movicol sachet 13.8 g in 125 ml of water", [("macrogol", "13.8", "g")], "dose"),
    ("Paracetamol 50 mg/ml, each 5 ml bottle", [("paracetamol", "50", "mg")], "ml"),
    ("Insulin glargine 100 units/ml, each 3 ml pen contains 300 units", [("insulin glargine", "100", "iu")], "ml"),
    ("Insulin 100 IU/ml. Each 3 ml cartridge", [("insulin", "100", "iu")], "ml"),
    ("Every 5 mL use the measuring cup; Concor 5 mg tablets", [("bisoprolol", "5", "mg")], "tablet"),
])
def test_packs_that_are_not_syrups_keep_their_strength(text, parts, per):
    reading = parse_label_json(label(text, *parts, per=per), "r1")
    assert reading.strength is not None
    assert [part.amount for part in reading.strength.ingredients] == [Decimal(amount) for _, amount, _ in parts]


def test_the_timeline_total_spans_the_table():
    report = run_intake(b19.AUDIO[0], [(b19.PHOTO, "image/png")], transcriber=b19.Transcriber(b19.TURNS),
                        extractor=b19.Extractor(b19.CLAIMS),
                        segmenter=b19.Segmenter({b19.RC.image_sha256: [b19.RC, b19.RB, b19.RN, b19.RU]}),
                        reader=b19.Reader(b19.reads()), catalogue=b19.CAT, top_k=4)
    timeline = b19.Page(render_brief(report, [(b19.PHOTO, "image/png")], b19.AUDIO, b19.CAT)).root.by_id("timeline")
    [cell] = timeline.find_all("tfoot")[0].find_all("td")
    assert cell.attrs.get("colspan") == str(len(TIMELINE_COLUMNS))
