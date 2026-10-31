"""Batch 22 contract, part 2: a single number word as the whole amount parses (SPEC §2). Written by the CEO; Muse must
not edit it.

Live on 28 Oct (evidence/batches/21/live-after.md, U5), Spark still sometimes wrote "five" in an amount field despite
batch 21's prompt. Such an amount never parsed, so it was dropped. Only one word, the whole amount, parses: a run of
words can be ambiguous ("eight seventy-five" reads as 83), so it still never parses. The stated-amount check is
unchanged: the value must have been said or printed.
"""

import json
from decimal import Decimal

import pytest

from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.numbers import parse_amount_text
from anamnesis.schema import AudioTurn


@pytest.mark.parametrize("text,value", [
    ("five", "5"), ("Five", "5"), ("twenty", "20"), ("خمسة", "5"), ("خمسمية", "500"), ("ميتين", "200"),
    ("واحد", "1"), (" five ", "5"),
])
def test_one_number_word_parses_as_its_value(text, value):
    assert parse_amount_text(text) == Decimal(value)


@pytest.mark.parametrize("text", [
    "five hundred", "eight seventy-five", "two and a half", "five milligrams", "once", "twice", "half", "hundred",
    "thousand", "zero", "many", "خمسة وعشرين", "ألف",
])
def test_anything_but_one_number_word_does_not_parse(text):
    assert parse_amount_text(text) is None


def test_a_dose_the_model_wrote_as_a_word_is_kept_when_it_was_said():
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=3000, transcript="I take Norvasc five milligrams.")]
    raw = {"name_text": "Norvasc", "inn": None, "strength": None, "regimen": None, "status": "active",
           "turn_ids": ["turn-0"], "intake_amount": {"inn": "Norvasc", "amount": "five", "unit": "mg"}}
    [found] = parse_claims_json(json.dumps({"claims": [raw]}), turns)
    assert found.intake_amount is not None and found.intake_amount.amount == Decimal("5")


def test_a_word_the_patient_did_not_say_is_still_dropped():
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=3000, transcript="I take Norvasc in the evening.")]
    raw = {"name_text": "Norvasc", "inn": None, "strength": None, "regimen": None, "status": "active",
           "turn_ids": ["turn-0"], "intake_amount": {"inn": "Norvasc", "amount": "five", "unit": "mg"}}
    [found] = parse_claims_json(json.dumps({"claims": [raw]}), turns)
    assert found.intake_amount is None
