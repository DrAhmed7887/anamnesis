"""Batch 23 contract, parts 3 and 4: what the 28 Oct comparison found on real phone photos
(evidence/batches/22/comparison.md). Written by the CEO; Muse must not edit it.

Part 3: SAM 3.1 found no region with "medicine box" or "label" in 19 of 30 Cairo University phone photos. "package"
found one in all 19, and Spark 1.3 read 15 of those crops correctly. So "package" is the third concept, tried only
when the first two find nothing (SPEC §4 step 3).
Part 4: a syrup labelled "250 mg / 5 ml" was read as 250 mg per ml, a fivefold error, or per dose. The schema can't say
per 5 ml, so a strength printed with a volume other than 1 ml becomes null, like an amount that isn't printed (SPEC §2
"A volume other than 1 ml").
"""

import json
from decimal import Decimal

import pytest

from anamnesis.agent import run_intake
from anamnesis.providers.spark import parse_label_json
from tests.contract import test_b19_brief as b19

# --- part 3: "package" is the third concept --------------------------------------------------------------------


class Concepts(b19.Segmenter):
    """Finds the pack only with the given concepts, and records every concept it was asked for."""

    def __init__(self, finds_with):
        super().__init__({})
        self.finds_with, self.asked = set(finds_with), []

    def segment(self, image, concept, *, mime):
        self.asked.append(concept)
        return ([b19.RC] if concept in self.finds_with else []), b19.trace("sam")


def intake_with(segmenter):
    pack = b19.reading("Concor 5 mg\nBisoprolol fumarate", b19.st(b19.mg("bisoprolol fumarate", 5)))
    return run_intake(None, [(b19.PHOTO, "image/png")], transcriber=b19.Transcriber(), extractor=b19.Extractor(),
                      segmenter=segmenter, reader=b19.Reader({b19.RC.region_id: [pack]}), catalogue=b19.CAT)


def test_package_is_the_third_concept_when_the_first_two_find_nothing():
    segmenter = Concepts({"package"})
    report = intake_with(segmenter)
    assert segmenter.asked == ["medicine box", "label", "package"]
    assert [region.region_id for region in report.regions] == [b19.RC.region_id]
    assert len(report.observations) == 1


@pytest.mark.parametrize("finds_with,asked", [
    ({"medicine box", "package"}, ["medicine box"]),
    ({"label", "package"}, ["medicine box", "label"]),
])
def test_package_is_not_asked_once_an_earlier_concept_finds_a_pack(finds_with, asked):
    segmenter = Concepts(finds_with)
    intake_with(segmenter)
    assert segmenter.asked == asked


def test_nothing_found_by_all_three_is_still_no_pack():
    segmenter = Concepts(set())
    report = intake_with(segmenter)
    assert segmenter.asked == ["medicine box", "label", "package"]
    assert report.regions == [] and report.observations == []


# --- part 4: a strength printed per a volume other than 1 ml is dropped ----------------------------------------

def label(text, amount="250", per="ml", inn="paracetamol"):
    return json.dumps({"label_text": text, "inn": inn, "country": None, "readability": "readable",
                       "strength": {"ingredients": [{"inn": inn, "amount": amount, "unit": "mg"}], "per": per,
                                    "release": "unknown"}})


@pytest.mark.parametrize("text", [
    "CETAL\nParacetamol (Microfined) 250 mg / 5 ml",
    "Paracetamol 250mg/5ml oral suspension",
    "Paracetamol 250 mg per 5 mL",
    "Paracetamol 250 mg in 5 ml",
    "باراسيتامول ٢٥٠ مجم / ٥ مل",
])
@pytest.mark.parametrize("per", ["ml", "dose", "tablet"])
def test_a_strength_printed_per_a_volume_other_than_1_ml_is_dropped(text, per):
    reading = parse_label_json(label(text, per=per), "r1")
    assert reading.strength is None
    assert reading.inn == "paracetamol" and reading.label_text == text


@pytest.mark.parametrize("text,amount,per", [
    ("Panadol 500 mg film-coated tablets", "500", "tablet"),
    ("Paracetamol 50 mg/ml oral drops", "50", "ml"),
    ("Paracetamol 250 mg / 1 ml", "250", "ml"),
    ("Panadol 500 mg\n24 tablets, 100 ml bottle", "500", "tablet"),
])
def test_other_strengths_are_kept(text, amount, per):
    reading = parse_label_json(label(text, amount=amount, per=per), "r1")
    assert reading.strength is not None
    assert reading.strength.ingredients[0].amount == Decimal(amount)
