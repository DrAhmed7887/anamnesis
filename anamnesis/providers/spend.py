"""Local append-only ledger for model spending."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

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
        record = {
            "call_id": trace.call_id,
            "model_id": trace.model_id,
            "cost_usd": str(trace.cost_usd),
            "time_utc": datetime.now(UTC).isoformat(),
        }
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a", encoding="utf-8") as ledger:
            ledger.write(json.dumps(record) + "\n")
