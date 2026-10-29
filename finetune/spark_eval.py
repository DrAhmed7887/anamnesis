"""Muse Spark 1.3's replies on the fine-tune's test splits, through the product's own claim extractor
(evidence/finetune/plan.md, "The comparison").

    PYTHONPATH=. .venv/bin/python finetune/spark_eval.py <split> [--data DIR] [--limit N] [--cap 8.00]
        [--session-usd 2.00]

Each example's turns go to MetaClaimExtractor.extract exactly as the intake sends them: the product's prompt,
schema, reasoning effort and max_tokens. Its first reply is the one scored, as each Glimmer gets one reply per
example. When the product's parser rejects a reply the extractor asks once more; that second reply is counted,
not scored. Every call is charged to evidence/spend/ledger.jsonl through the usual guards.
Output: evidence/finetune/runs/spark/<split>.jsonl, one {"index", "reply", ...} line per example, written as
each example finishes, for finetune/score.py.
"""

import argparse
import json
import os
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import intake_live as il  # noqa: E402

from anamnesis.providers import SpendGuard  # noqa: E402
from anamnesis.providers.base import ProviderError  # noqa: E402
from anamnesis.providers.claims import MetaClaimExtractor  # noqa: E402
from anamnesis.providers.meta import MetaClient  # noqa: E402
from anamnesis.providers.spend import SessionGuard  # noqa: E402
from finetune.common import DATA_DIR, read_jsonl, turns_from_records  # noqa: E402

OUT = ROOT / "evidence" / "finetune" / "runs" / "spark"


class Capturing:
    """The Meta client, keeping each reply's text and finish reason as the extractor receives them."""

    def __init__(self, client: Any) -> None:
        self.client, self.replies = client, []

    def post(self, *args: Any, **kwargs: Any) -> Any:
        payload, latency_ms = self.client.post(*args, **kwargs)
        choices = payload.get("choices") if isinstance(payload, dict) else None
        choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        usage = payload.get("usage") if isinstance(payload, dict) else None
        self.replies.append({"reply": message.get("content"), "finish": choice.get("finish_reason"),
                             "latency_ms": latency_ms, "usage": usage})
        return payload, latency_ms

    def __getattr__(self, name: str) -> Any:
        return getattr(self.client, name)


def run_split(extractor: MetaClaimExtractor, capture: Capturing, rows: list[dict], out: Path) -> dict:
    """One extraction per example, its first reply written as soon as it returns."""
    counts = {"examples": 0, "replies": 0, "second_attempts": 0, "errors": 0}
    with out.open("w", encoding="utf-8") as handle:
        for position, row in enumerate(rows):
            if row.get("index") != position:
                raise ValueError(f"answer line {position} has index {row.get('index')}")
            before, clock, error = len(capture.replies), time.monotonic(), None
            try:
                extractor.extract(turns_from_records(row["turns"]))
            except ProviderError as exc:
                error = str(exc)
            replies = capture.replies[before:]
            first = replies[0] if replies else {}
            line = {"index": position, "reply": first.get("reply"), "finish": first.get("finish"),
                    "latency_ms": first.get("latency_ms"), "usage": first.get("usage"),
                    "attempts": len(replies), "error": error,
                    "wall_ms": int((time.monotonic() - clock) * 1000)}
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")
            handle.flush()
            counts = {"examples": counts["examples"] + 1, "replies": counts["replies"] + bool(replies),
                      "second_attempts": counts["second_attempts"] + (len(replies) > 1),
                      "errors": counts["errors"] + (error is not None)}
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("split", help="a split of --data: test_iid, test_shift, test_codeswitch, test_real "
                                      "or, in finetune/data_v2, test_spain")
    parser.add_argument("--data", type=Path, default=DATA_DIR)
    parser.add_argument("--limit", type=int, default=None, help="only the first N examples")
    parser.add_argument("--cap", default="8.00", help="total USD cap across all live runs (ledger)")
    parser.add_argument("--session-usd", default="2.00", help="USD cap for this split")
    args = parser.parse_args()
    answers = args.data / f"{args.split}.answers.jsonl"
    if not answers.exists():
        sys.exit(f"no split {args.split} in {args.data}")
    rows = read_jsonl(answers)[: args.limit]
    ledger = SpendGuard(il.LEDGER, cap_usd=Decimal(args.cap))
    capture = Capturing(MetaClient(api_key=os.environ.get("MODEL_API_KEY") or il.keychain("META_API_KEY")))
    guard = SessionGuard(ledger, max_usd=Decimal(args.session_usd), max_calls=2 * len(rows))
    OUT.mkdir(parents=True, exist_ok=True)
    start = ledger.total_usd
    counts = run_split(MetaClaimExtractor(capture, guard), capture, rows, OUT / f"{args.split}.jsonl")
    print(f"{args.split}: {counts} · spend ${ledger.total_usd - start:.5f}"
          f" · ledger total ${ledger.total_usd:.5f}")


if __name__ == "__main__":
    main()
