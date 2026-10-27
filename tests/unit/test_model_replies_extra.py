"""Extra offline checks for batch 16 model-reply handling (SPEC §2)."""

import json
from decimal import Decimal

import pytest

from anamnesis.providers.base import ProviderError
from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.numbers import coerce_strength, parse_amount_text
from anamnesis.providers.spark import parse_label_json
from anamnesis.schema import AudioTurn

TURNS = [
    AudioTurn(turn_id="turn-0", start_ms=0, end_ms=4000, transcript="I take Concor 2,5 mg once a day."),
]


def _claim(**fields):
    base = {"name_text": "Concor", "inn": None, "strength": None, "intake_amount": None,
            "regimen": None, "status": "active", "turn_ids": ["turn-0"]}
    return base | fields


def _reply(*claims):
    return json.dumps({"claims": list(claims)})


@pytest.mark.parametrize("text,expected", [
    (" 2,5 ", Decimal("2.5")),
    ("1,00", Decimal("1.00")),
    ("2,55", Decimal("2.55")),
    ("12,345", None),
    ("1,000", None),
    ("5.", None),
    (".5", None),
    ("0,0", None),
    ("0.5", Decimal("0.5")),
    ("007", Decimal("7")),
])
def test_number_parser_edge_cases(text, expected):
    assert parse_amount_text(text) == expected


def test_number_parser_rejects_non_strings():
    assert parse_amount_text(None) is None
    assert parse_amount_text(True) is None
    assert parse_amount_text(-3) is None
    assert parse_amount_text(Decimal("0")) is None
    assert parse_amount_text(Decimal("1.5")) == Decimal("1.5")


def test_duplicate_inn_strength_becomes_null():
    strength = {"ingredients": [
        {"inn": "metoprolol succinate", "amount": "95", "unit": "mg"},
        {"inn": "metoprolol tartrate", "amount": "100", "unit": "mg"},
    ], "per": "tablet", "release": "modified"}
    assert coerce_strength(strength) is None


def test_bad_intake_keeps_regimen_and_status():
    raw = _claim(intake_amount={"inn": "bisoprolol", "amount": "1-2", "unit": "mg"},
                 regimen={"units_per_intake": "1", "intakes_per_day": "2", "as_needed": None})
    [found] = parse_claims_json(_reply(raw), TURNS)
    assert found.intake_amount is None
    assert found.regimen.intakes_per_day == Decimal("2")


def test_advice_in_regimen_free_claim_inn_is_rejected():
    with pytest.raises(ProviderError) as error:
        parse_claims_json(_reply(_claim(inn="you should take bisoprolol")), TURNS)
    assert error.value.retryable


def test_label_country_and_advice_helpers():
    base = {"label_text": "Concor 5 mg", "inn": "bisoprolol", "readability": "readable",
            "strength": {"ingredients": [{"inn": "bisoprolol", "amount": "5", "unit": "mg"}],
                         "per": "tablet", "release": "immediate"}}
    assert parse_label_json(json.dumps({**base, "country": "de"}), "r1").country == "DE"
    assert parse_label_json(json.dumps({**base, "country": "USA"}), "r1").country is None
    with pytest.raises(ProviderError):
        parse_label_json(json.dumps({**base, "inn": "take bisoprolol now"}), "r1")


def test_ungrounded_name_lists_retryable_error():
    with pytest.raises(ProviderError) as error:
        parse_claims_json(_reply(_claim(name_text="Lipitor")), TURNS)
    assert error.value.retryable


ADVICE_BEFORE_DROP = {"inn": "bisoprolol; take two", "amount": "five", "unit": "mg"}


def test_advice_in_a_strength_ingredient_is_rejected_before_the_amount_is_dropped():
    strength = {"ingredients": [ADVICE_BEFORE_DROP], "per": "tablet", "release": "unknown"}
    with pytest.raises(ProviderError) as error:
        parse_claims_json(_reply(_claim(strength=strength)), TURNS)
    assert error.value.retryable


def test_advice_in_an_intake_amount_is_rejected_before_it_is_dropped():
    with pytest.raises(ProviderError) as error:
        parse_claims_json(_reply(_claim(intake_amount=dict(ADVICE_BEFORE_DROP))), TURNS)
    assert error.value.retryable


def test_advice_in_a_label_strength_ingredient_is_rejected_before_the_amount_is_dropped():
    base = {"label_text": "Concor 5 mg", "inn": "bisoprolol", "readability": "readable",
            "strength": {"ingredients": [dict(ADVICE_BEFORE_DROP)],
                         "per": "tablet", "release": "immediate"}}
    with pytest.raises(ProviderError) as error:
        parse_label_json(json.dumps(base), "r1")
    assert error.value.retryable
