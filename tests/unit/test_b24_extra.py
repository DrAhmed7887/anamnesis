"""Batch 24 extra unit checks: German compounds, Spanish comma runs, second-turn grounding."""

import json
from decimal import Decimal

import pytest

from anamnesis.core.catalogue import normalise
from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.stated import stated_amounts
from anamnesis.schema import AudioTurn


@pytest.mark.parametrize(("word", "value"), [
    ("dreihundertzwölf Milligramm", "312"),
    ("neunhundertneunundneunzig Milligramm", "999"),
    ("zweitausendfünfhundert Milligramm", "2500"),
])
def test_german_compound_edge_cases(word, value):
    assert Decimal(value) in stated_amounts(word)


def test_spanish_run_ends_at_a_comma():
    found = stated_amounts("tomo cinco miligramos, dos comprimidos")
    assert {Decimal(5), Decimal(2)} <= found
    assert Decimal(7) not in found


def test_round7_mixed_pair_never_adds():
    found = stated_amounts("cinco five mg")
    assert Decimal(10) not in found and Decimal(5) in found
    assert stated_amounts("la point seis") == frozenset()


def test_round9_mixed_runs_and_clock():
    assert Decimal(200) in stated_amounts("doscientos two hundred milligrams")
    assert Decimal(400) in stated_amounts("la four hundred milligrams")
    assert Decimal(41) not in stated_amounts("cuarenta y ein mg")
    assert Decimal(3) not in stated_amounts("a las siete y veinte y tres mil miligramos")


def test_round10_english_after_las_and_article_no_join():
    assert stated_amounts("las two hundred fifty milligrams") == frozenset(
        Decimal(v) for v in ("2", "100", "50", "250")
    )
    assert Decimal("201") not in stated_amounts("zweihundert ein gramm")
    assert Decimal("1") in stated_amounts("zweihundert ein gramm")
    assert Decimal("31") in stated_amounts("treinta y un miligramos")


def test_grounded_label_in_second_cited_turn():
    turns = [
        AudioTurn(turn_id="turn-0", start_ms=0, end_ms=1000,
                  transcript="I take Zykoral every morning", speaker=None, lang_hint="en"),
        AudioTurn(turn_id="turn-1", start_ms=1000, end_ms=2000,
                  transcript="that is bisoprolol five milligrams", speaker=None, lang_hint="en"),
    ]
    claim = {"name_text": "Zykoral", "inn": "bisoprolol", "strength": None,
             "intake_amount": {"inn": "bisoprolol", "amount": "5", "unit": "mg"},
             "regimen": None, "status": "active", "turn_ids": ["turn-0", "turn-1"]}
    [found] = parse_claims_json(json.dumps({"claims": [claim]}), turns)
    assert normalise(found.inn or "") == "bisoprolol"
    assert found.intake_amount is not None
    assert normalise(found.intake_amount.inn) == "bisoprolol"
