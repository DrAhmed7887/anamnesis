"""Focused offline checks for patient claim extraction."""

import json
from decimal import Decimal

import httpx
import pytest

from anamnesis.providers import ProviderError, SpendGuard
from anamnesis.providers.claims import CLAIMS_SCHEMA, MetaClaimExtractor, parse_claims_json
from anamnesis.providers.meta import MetaClient
from anamnesis.schema import AudioTurn


def _turn() -> AudioTurn:
    return AudioTurn(
        turn_id="turn-0", start_ms=0, end_ms=8700,
        transcript="Concor five milligrams", speaker="A",
    )


def _claim() -> dict[str, object]:
    return {
        "name_text": "Concor",
        "inn": None,
        "strength": None,
        "intake_amount": {"inn": "bisoprolol", "amount": "5", "unit": "mg"},
        "regimen": {"units_per_intake": None, "intakes_per_day": "1", "as_needed": None},
        "status": "active",
        "turn_ids": ["turn-0"],
    }


def test_claim_schema_is_inline_and_requires_every_claim_field():
    encoded = json.dumps(CLAIMS_SCHEMA)
    assert "$ref" not in encoded and "$defs" not in encoded
    assert set(CLAIMS_SCHEMA["required"]) == {"claims"}
    claim_schema = CLAIMS_SCHEMA["properties"]["claims"]["items"]
    assert set(claim_schema["required"]) == set(_claim())
    assert claim_schema["additionalProperties"] is False


@pytest.mark.parametrize("change", [
    {"intake_amount": {"inn": "bisoprolol", "amount": "5", "unit": "mg", "extra": 1}},
    {"regimen": {"units_per_intake": None, "intakes_per_day": "1", "as_needed": None, "extra": 1}},
    {"strength": {"ingredients": [], "per": "tablet", "release": "immediate", "extra": 1}},
])
def test_parser_rejects_extra_nested_fields(change):
    raw = {"claims": [{**_claim(), **change}]}
    with pytest.raises(ProviderError) as raised:
        parse_claims_json(json.dumps(raw), [_turn()])
    assert raised.value.provider == "spark" and raised.value.retryable


def test_parser_rejects_missing_required_fields():
    raw = {"claims": [{key: value for key, value in _claim().items() if key != "inn"}]}
    with pytest.raises(ProviderError):
        parse_claims_json(json.dumps(raw), [_turn()])


def test_extractor_sends_verbatim_timed_turn_and_charges_usage(tmp_path):
    response = {
        "id": "chat_claims",
        "choices": [{"message": {"content": json.dumps({"claims": [_claim()]})}}],
        "usage": {"prompt_tokens": 800, "completion_tokens": 300},
    }
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=response)

    guard = SpendGuard(tmp_path / "ledger.jsonl", Decimal("1"))
    client = MetaClient("test-key", transport=httpx.MockTransport(respond))
    claims, trace = MetaClaimExtractor(client, guard).extract([_turn()])
    request = json.loads(requests[0].content)
    assert request["messages"][1]["content"] == (
        "[turn-0 0–8700 ms, speaker A] Concor five milligrams"
    )
    assert claims[0].claim_id == "c1"
    assert trace is not None and trace.cost_usd == Decimal("0.001") + Decimal("0.001275")
    assert guard.total_usd == trace.cost_usd
