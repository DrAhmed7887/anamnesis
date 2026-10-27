"""Additional spend ledger integrity checks."""

import json
from decimal import Decimal

from anamnesis.providers.base import ProviderError, ProviderTrace, with_one_retry
from anamnesis.providers.spend import SpendGuard


def test_estimated_charge_records_reason_and_counts_toward_cap(tmp_path):
    guard = SpendGuard(tmp_path / "ledger.jsonl", Decimal("0.01"))

    call_id = guard.charge_estimate("sam-3.1", Decimal("0.0025"), "timeout")

    entry = json.loads(guard.ledger_path.read_text(encoding="utf-8"))
    assert call_id.startswith("estimated-")
    assert entry["call_id"] == call_id
    assert entry["estimated"] is True
    assert entry["reason"] == "timeout"
    assert guard.total_usd == Decimal("0.0025")


def test_retry_trace_keeps_estimated_prior_attempt(tmp_path):
    guard = SpendGuard(tmp_path / "ledger.jsonl", Decimal("1"))
    trace = ProviderTrace(
        call_id="call-2", model_id="sam-3.1", latency_ms=1,
        input_tokens=0, output_tokens=0, cost_usd=Decimal("0.0025"),
    )
    calls = 0

    def attempt():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ProviderError(
                "sam", "timeout", retryable=True, billable_uncertain=True,
                estimated_reason="timeout",
            )
        guard.charge_prechecked(trace)
        return [], trace

    _, result = with_one_retry(
        attempt, guard=guard, model_id="sam-3.1", estimate=Decimal("0.0025"),
    )

    assert result.prior_call_ids[0].startswith("estimated-")
    assert result.prior_cost_usd == Decimal("0.0025")
    assert guard.total_usd == Decimal("0.0025") + trace.cost_usd
