"""Batch 24 round 7: every Spanish or German run follows round 6's amount rule, whatever closes it (SPEC §2, round 7).
The CEO's probe and differential of round 6 found the gaps: a Spanish or German number added an English one after it
("cinco five mg" stated 10), an adjacency close skipped the rule ("elf cinco miligramos" stated 11), and an English
"point" with Spanish or German digits made a decimal outside any amount ("la point seis" stated 0.6)."""

import json
from decimal import Decimal

import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all
from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.stated import stated_amounts
from anamnesis.schema import AudioTurn, IngredientAmount, PackObservation, Strength
from anamnesis.schema import DiscrepancyType as D

CAT = load_catalogue()


@pytest.mark.parametrize(("text", "never", "value"), [
    ("cinco five mg", "10", "5"), ("diez thirty milligrams", "40", "30"), ("zwei two Tabletten", "4", "2"),
    ("five cinco mg", "10", "5"),
])
def test_a_mixed_language_pair_never_adds_up(text, never, value):
    found = stated_amounts(text)
    assert Decimal(never) not in found and Decimal(value) in found


@pytest.mark.parametrize(("text", "value"), [("twenty five milligrams", "25"), ("treinta y cinco miligramos", "35")])
def test_one_languages_joins_still_read(text, value):
    assert Decimal(value) in stated_amounts(text)


def test_a_self_correction_across_languages_never_reaches_match():
    turn = AudioTurn(turn_id="turn-0", start_ms=0, end_ms=1000, transcript="Tomo Concor, cinco five mg.", speaker=None,
                     lang_hint="en")
    raw = {"name_text": "Concor", "inn": None, "strength": None,
           "intake_amount": {"inn": "bisoprolol", "amount": "10", "unit": "mg"},
           "regimen": None, "status": "active", "turn_ids": ["turn-0"]}
    [claim] = parse_claims_json(json.dumps({"claims": [raw]}), [turn])
    pack = PackObservation(observation_id="o1", label_text="Concor 10 mg", readability="readable",
                           visual_evidence=["r_o1"],
                           strength=Strength(ingredients=[IngredientAmount(inn="bisoprolol", amount=Decimal(10),
                                                                           unit="mg")],
                                             per="tablet", release="unknown"))
    [found] = reconcile_all([claim], [pack], CAT)
    assert found.type is D.INSUFFICIENT_INFORMATION


@pytest.mark.parametrize(("text", "never"), [
    ("elf cinco miligramos", "11"),            # closed by the next number: still no amount after it
    ("dos ml ochocientos hundred", "800"),     # closed by an English hundred
    ("diez y cincuenta miligramos", "10"),     # closed by a y that joins nothing
])
def test_a_spanish_or_german_run_needs_an_amount_whatever_closes_it(text, never):
    assert Decimal(never) not in stated_amounts(text)


@pytest.mark.parametrize("text", ["la point seis", "al point sieben diez"])
def test_a_decimal_with_spanish_or_german_digits_needs_an_amount(text):
    assert stated_amounts(text) == frozenset()


def test_a_decimal_with_spanish_or_german_digits_before_a_unit_counts():
    assert Decimal("0.7") in stated_amounts("point sieben Milligramm")
