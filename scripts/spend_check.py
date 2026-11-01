"""Spend gate: what each credit has spent, from our own ledgers, against a stop line (50% by default).

    uv run python scripts/spend_check.py [--stop-at 0.5] [--next meta=2.00 google=0.50 ...]

Exits 1 when any credit has reached the stop line, or would with the next step's estimate, so a step that
spends runs only after this passes (Ahmed, 28 Oct: pause at 50% of Meta's or any partner's credit). An unknown
provider in a ledger also stops it. The ledgers are estimates; each provider's dashboard is the final word.
"""

import argparse
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The credits as recorded in the plan and Notion (Credits & Subscriptions), 28 Oct 2026.
CREDITS = {"meta": Decimal(150), "fireworks": Decimal(100), "baseten": Decimal(100),
           "google": Decimal("50.95"), "modal": Decimal(100)}
# Ahmed, 1 Nov 13:15: Meta stops at $100 (it was $80 from 31 Oct 15:13; evidence/decisions.md).
# Muse's read-only grills are in neither ledger, so they're added here: 13 sessions, $3.1251 at
# muse_usage.py's prices (31 Oct 17:10). Raise it after each new grill.
STOP_USD = {"meta": Decimal(100)}
NOT_IN_LEDGERS = {"meta": Decimal("3.13")}


def _worktrees() -> list[Path]:
    listing = subprocess.run(["git", "-C", str(ROOT), "worktree", "list", "--porcelain"],
                             capture_output=True, text=True).stdout
    trees = [Path(line[len("worktree "):]) for line in listing.splitlines() if line.startswith("worktree ")]
    return trees or [ROOT]


def ledger_lines(name: str) -> list[dict]:
    """Every line of one ledger across all worktrees of this repo, each once. A batch branch lags main's
    adapter ledger and main lags the branch's Muse ledger, so no single copy is the whole spend (28 Oct)."""
    seen: set[str] = set()
    rows = []
    for tree in _worktrees():
        path = tree / "evidence/spend" / name
        for line in path.read_text(encoding="utf-8").splitlines() if path.exists() else []:
            if line.strip() and line not in seen:
                seen.add(line)
                rows.append(json.loads(line))
    return rows


def spent() -> dict[str, Decimal]:
    total = dict.fromkeys(CREDITS, Decimal(0))
    for line in ledger_lines("muse_ledger.jsonl"):
        total["meta"] += Decimal(str(line["cost_usd"]))
    for line in ledger_lines("ledger.jsonl"):  # open weights carry their provider: muse-spark-open@fireworks
        provider = line.get("model_id", "").partition("@")[2] or "meta"
        total[provider] = total.get(provider, Decimal(0)) + Decimal(str(line["cost_usd"]))
    for provider in ("google", "modal"):
        for line in ledger_lines(f"{provider}_ledger.jsonl"):
            total[provider] += Decimal(str(line["cost_usd"]))
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stop-at", type=Decimal, default=Decimal("0.5"))
    parser.add_argument("--next", nargs="*", default=[], help="the next step's estimate, as provider=USD")
    args = parser.parse_args()
    total = spent()
    upcoming = {name: Decimal(usd) for name, usd in (item.split("=", 1) for item in args.next)}
    stop = False
    for provider in sorted(set(total) | set(upcoming)):
        after = total.get(provider, Decimal(0)) + upcoming.get(provider, Decimal(0))
        credit = CREDITS.get(provider)
        if credit is None:
            print(f"{provider:10} ${after:9.4f}  STOP: no known credit for this provider")
            stop = True
            continue
        after += NOT_IN_LEDGERS.get(provider, Decimal(0))
        share = after / credit
        line = STOP_USD.get(provider)
        flag = "STOP" if (after >= line if line is not None else share >= args.stop_at) else "ok"
        stop |= flag == "STOP"
        note = f" (line ${line}, grills included)" if line is not None else ""
        print(f"{provider:10} ${after:9.4f} of ${credit:>6} = {share:6.1%}  {flag}{note}")
    sys.exit(1 if stop else 0)


if __name__ == "__main__":
    main()
