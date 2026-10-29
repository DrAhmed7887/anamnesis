"""Batch 24 round 3: the supervisor's round 2 review (evidence/batches/24/supervisor.md), pinned (SPEC §2, round 3)."""

import json
from decimal import Decimal

import pytest

from anamnesis.core.catalogue import load_catalogue, normalise
from anamnesis.core.reconcile import reconcile_all
from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.stated import stated_amounts
from anamnesis.schema import AudioTurn, IngredientAmount, PackObservation, Strength
from anamnesis.schema import DiscrepancyType as D

CAT = load_catalogue()


def parse(said, **fields):
    turn = AudioTurn(turn_id="turn-0", start_ms=0, end_ms=1000, transcript=said, speaker=None, lang_hint="en")
    claim = {"name_text": "Farxiga", "inn": None, "strength": None, "intake_amount": None, "regimen": None,
             "status": "active", "turn_ids": ["turn-0"], **fields}
    return parse_claims_json(json.dumps({"claims": [claim]}, ensure_ascii=False), [turn])[0]


def line(inn, amount):
    return {"inn": inn, "amount": amount, "unit": "mg"}


# --- #1: English "media" and Spanish phrases that aren't numbers state no half --------------------------------

def test_social_media_never_lets_an_invented_half_reach_match():
    claim = parse("I take alprazolam at night, I read about it on social media.", name_text="alprazolam",
                  inn="alprazolam", intake_amount=line("alprazolam", "0.5"))
    assert claim.intake_amount is None
    pack = PackObservation(observation_id="o1", label_text="Alprazolam 0.5 mg", readability="readable",
                           visual_evidence=["r_o1"],
                           strength=Strength(ingredients=[IngredientAmount(inn="alprazolam", amount=Decimal("0.5"),
                                                                           unit="mg")],
                                             per="tablet", release="unknown"))
    [found] = reconcile_all([claim], [pack], CAT)
    assert found.type is D.INSUFFICIENT_INFORMATION


@pytest.mark.parametrize("text", ["I read about it on social media.", "por medio de la farmacia",
                                  "es por el medio ambiente", "the media said so"])
def test_these_state_no_half(text):
    assert Decimal("0.5") not in stated_amounts(text)


@pytest.mark.parametrize(("text", "value"), [("medio comprimido", "0.5"), ("media pastilla", "0.5"),
                                             ("uno y medio comprimidos", "1.5"), ("dos y media pastillas", "2.5")])
def test_a_spanish_half_still_reads(text, value):
    assert Decimal(value) in stated_amounts(text)


# --- #3: after "mil", only a Spanish unit word makes it a thousand ---------------------------------------------

@pytest.mark.parametrize("text", ["five mil ml", "ten mil mg", "خمسين mil mg"])
def test_mil_before_an_abbreviation_is_no_thousand(text):
    assert not {Decimal(1000), Decimal(5000), Decimal(10000), Decimal(50000)} & stated_amounts(text)


def test_mil_before_a_spanish_unit_word_is_still_a_thousand():
    assert Decimal(1000) in stated_amounts("mil miligramos")


# --- #2: a label of number words that need a neighbour is never grounded ---------------------------------------

@pytest.mark.parametrize(("said", "label", "amount"), [
    ("Farxiga, mil miligramos", "mil miligramos", "1000"),
    ("Farxiga ein Gramm", "ein Gramm", "1"),
    ("Farxiga cero coma cinco miligramos", "cero coma cinco", "0.5"),
    ("Farxiga zero point five", "zero point five", "0.5"),
    ("Farxiga null Komma fünf Milligramm", "null Komma fünf", "5"),
])
def test_a_number_word_label_takes_the_claims_name(said, label, amount):
    claim = parse(said, intake_amount=line(label, amount))
    assert claim.intake_amount is not None and normalise(claim.intake_amount.inn) == "farxiga"
