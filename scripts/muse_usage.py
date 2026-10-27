"""What one Muse Code session cost, from its own billing records, at the documented Spark prices.

    uv run python scripts/muse_usage.py <batch> <session-export.json>

Reads the provider billing records in a `muse export` file, appends one line to
evidence/spend/muse_ledger.jsonl, writes evidence/batches/<batch>/usage.json and prints the Meta total.
This is an estimate from Muse's own records; Meta's dashboard (https://dev.meta.ai/usage) is the final word.
Muse spend is not in evidence/spend/ledger.jsonl, which holds the adapter calls only.
"""

import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MUSE_LEDGER = ROOT / "evidence/spend/muse_ledger.jsonl"
ADAPTER_LEDGER = ROOT / "evidence/spend/ledger.jsonl"
CREDIT_USD = Decimal(150)
# USD per 1M tokens: input not cached, cached input, output (reasoning is part of output).
# Source: docs/muse/README.md (dev.meta.ai pricing).
PRICES = {"muse-spark-1.3": (Decimal("1.25"), Decimal("0.15"), Decimal("4.25"))}


def _events(export: dict) -> list[dict]:
    found = []
    for item in export.get("events", []):
        event = item.get("envelope", {}).get("payload", {}).get("event")
        if isinstance(event, dict):
            found.append(event)
    return found


def _models(export: dict) -> set[str]:
    """Model ids, which exports write as a string or as {"model_id": ...} depending on the version."""
    models = set()
    for item in export.get("events", []):
        derived = item.get("derived", {}).get("model")
        event = item.get("envelope", {}).get("payload", {}).get("event")
        candidates = [derived, event.get("model") if isinstance(event, dict) else None]
        for model in candidates:
            model = model.get("model_id") if isinstance(model, dict) else model
            if isinstance(model, str) and model and model != "same-as-main":
                models.add(model)
    return models


def tally(export: dict) -> dict:
    """Token totals over the provider billing records, plus every model id the session used."""
    tokens = {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
    models, sessions = _models(export), set()
    for event in _events(export):
        record = event.get("record")
        if isinstance(record, dict) and record.get("usage_family") == "provider":
            quantity = record.get("quantity", {})
            for key in tokens:
                tokens[key] += int(quantity.get(key) or 0)
            sessions.add(record.get("owner", {}).get("session_id"))
    return {**tokens, "models": sorted(models), "sessions": sorted(s for s in sessions if s)}


def price(usage: dict) -> Decimal:
    unpriced = [model for model in usage["models"] if model not in PRICES]
    if unpriced or not usage["models"]:
        missing = unpriced or "an unknown model"
        raise SystemExit(f"usage: no documented price for {missing}; check dev.meta.ai/usage")
    fresh, cached, out = PRICES[usage["models"][0]]
    billable_input = usage["input_tokens"] - usage["cached_tokens"]
    cost = billable_input * fresh + usage["cached_tokens"] * cached + usage["output_tokens"] * out
    return cost / 1_000_000


def _ledger_total(path: Path, field: str = "cost_usd") -> Decimal:
    if not path.exists():
        return Decimal(0)
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return sum((Decimal(str(line[field])) for line in lines), Decimal(0))


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    batch, export_path = sys.argv[1], Path(sys.argv[2])
    usage = tally(json.loads(export_path.read_text(encoding="utf-8")))
    if any("contributor" in model for model in usage["models"]):
        print("WARNING: a contributor model was used in this session", file=sys.stderr)
    cost = price(usage).quantize(Decimal("0.00001"))
    line = {"batch": batch, **usage, "cost_usd": str(cost), "estimated": True,
            "source": "muse export billing records", "at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
    with MUSE_LEDGER.open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps(line) + "\n")
    out_dir = ROOT / "evidence/batches" / batch
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "usage.json").write_text(json.dumps(line, indent=2) + "\n", encoding="utf-8")
    muse_total, adapter_total = _ledger_total(MUSE_LEDGER), _ledger_total(ADAPTER_LEDGER)
    meta_total = muse_total + adapter_total
    print(f"batch {batch} Muse: {usage['input_tokens']:,} input ({usage['cached_tokens']:,} cached), "
          f"{usage['output_tokens']:,} output -> ${cost}")
    print(f"Meta so far: Muse ${muse_total:.4f} + adapters ${adapter_total:.4f} = ${meta_total:.4f} "
          f"of the ${CREDIT_USD} credit (earlier Muse grills are in neither ledger: evidence/decisions.md)")


if __name__ == "__main__":
    main()
