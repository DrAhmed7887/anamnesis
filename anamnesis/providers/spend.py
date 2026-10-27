"""Local append-only ledger for model spending."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from anamnesis.providers.base import ProviderTrace


class SpendCapExceeded(Exception):
    pass


class SpendGuard:
    def __init__(self, ledger_path: str | Path, cap_usd: Decimal) -> None:
        self.ledger_path = Path(ledger_path)
        self.cap_usd = Decimal(cap_usd)

    @property
    def total_usd(self) -> Decimal:
        if not self.ledger_path.exists():
            return Decimal(0)
        with self.ledger_path.open(encoding="utf-8") as ledger:
            return sum((Decimal(json.loads(line)["cost_usd"]) for line in ledger), Decimal(0))

    def check(self, estimate: Decimal) -> None:
        if Decimal(estimate) < 0:
            raise ValueError("estimate cannot be negative")
        if self.total_usd + Decimal(estimate) > self.cap_usd:
            raise SpendCapExceeded("spend cap would be exceeded")

    def charge(self, trace: ProviderTrace) -> None:
        self.check(trace.cost_usd)
        self._append(trace.call_id, trace.model_id, trace.cost_usd, estimated=False)

    def charge_prechecked(self, trace: ProviderTrace) -> None:
        """Record a billed call whose pre-call estimate already passed the cap check."""
        self._append(trace.call_id, trace.model_id, trace.cost_usd, estimated=False)

    def charge_estimate(self, model_id: str, amount: Decimal, reason: str) -> str:
        amount = Decimal(amount)
        if amount < 0:
            raise ValueError("estimate cannot be negative")
        if not reason:
            raise ValueError("estimated charge reason cannot be empty")
        call_id = f"estimated-{uuid4()}"
        self._append(call_id, model_id, amount, estimated=True, reason=reason)
        return call_id

    def _append(
        self, call_id: str, model_id: str, amount: Decimal, *, estimated: bool,
        reason: str | None = None,
    ) -> None:
        record = {
            "call_id": call_id,
            "model_id": model_id,
            "cost_usd": str(amount),
            "time_utc": datetime.now(UTC).isoformat(),
            "estimated": estimated,
        }
        if estimated:
            record["reason"] = reason
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a", encoding="utf-8") as ledger:
            ledger.write(json.dumps(record) + "\n")


class SessionCapExceeded(SpendCapExceeded):
    """The per-session dollar or call cap would be exceeded."""


class SessionGuard:
    """Per-session caps in front of a parent ledger; every charge still reaches the parent."""

    def __init__(self, parent: SpendGuard, max_usd: Decimal, max_calls: int) -> None:
        self.parent = parent
        self.max_usd = Decimal(max_usd)
        self.max_calls = max_calls
        self._usd = Decimal(0)
        self._calls = 0

    @property
    def total_usd(self) -> Decimal:
        return self._usd

    def check(self, estimate: Decimal) -> None:
        if Decimal(estimate) < 0:
            raise ValueError("estimate cannot be negative")
        self._check_session(estimate)
        self.parent.check(estimate)

    def _check_session(self, estimate: Decimal) -> None:
        if self._calls >= self.max_calls:
            raise SessionCapExceeded("session call cap reached")
        if self._usd + Decimal(estimate) > self.max_usd:
            raise SessionCapExceeded("session spend cap would be exceeded")

    def charge(self, trace: ProviderTrace) -> None:
        self._check_session(trace.cost_usd)
        self.parent.charge(trace)
        self._record(trace.cost_usd)

    def charge_prechecked(self, trace: ProviderTrace) -> None:
        self.parent.charge_prechecked(trace)
        self._record(trace.cost_usd)

    def charge_estimate(self, model_id: str, amount: Decimal, reason: str) -> str:
        call_id = self.parent.charge_estimate(model_id, amount, reason)
        self._record(Decimal(amount))
        return call_id

    def _record(self, amount: Decimal) -> None:
        self._usd += Decimal(amount)
        self._calls += 1
