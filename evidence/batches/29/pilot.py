"""Batch 29 pilot (31 Oct, pre-registered in pilot-plan.md): does one added sentence make Spark 1.3 write a
combination's two spoken amounts as its strength? Ten calls, through the product's MetaClaimExtractor, with
the sentence added to Spark's prompt in this process only. Keys from the Keychain, never printed."""
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import anamnesis.providers.claims as claims
from anamnesis.providers import SpendGuard
from anamnesis.providers.meta import MetaClient
from anamnesis.schema import AudioTurn

SENTENCE = ("A combination product said with one amount per ingredient, such as 'Augmentin 875 and 125 "
            "milligrams', is its strength: one ingredient per amount, in the order said, each named for the "
            "ingredient it belongs to.")
claims._SYSTEM_PROMPT = claims._SYSTEM_PROMPT + " " + SENTENCE
CASES = [
    ("U2", "I take Augmentin, 875 and 125 milligrams, twice a day", 3),
    ("U2-ar", "باخد اوجمنتين ٨٧٥ و ١٢٥ مجم مرتين في اليوم", 3),
    ("U1", "I take Concor five milligrams once a day.", 2),
    ("U12", "I take Concor 10 milligrams every morning and BelocZok 50 milligrams twice a day", 2),
]


class Capture(MetaClient):
    replies: list = []

    def post(self, path, **kwargs):  # noqa: D102
        payload, latency_ms = super().post(path, **kwargs)
        Capture.replies.append(payload)
        return payload, latency_ms


key = subprocess.run(["security", "find-generic-password", "-s", "META_API_KEY", "-w"],
                     capture_output=True, text=True, check=True).stdout.strip()
guard = SpendGuard(Path("evidence/spend/ledger.jsonl"), cap_usd=Decimal("14.00"))
extractor = claims.MetaClaimExtractor(Capture(api_key=key), guard)
rows = []
for name, text, times in CASES:
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=5000, transcript=text)]
    for i in range(times):
        Capture.replies.clear()
        try:
            parsed, _ = extractor.extract(turns)
            kept = [{"name": c.name_text, "intake": c.intake_amount and str(c.intake_amount.amount),
                     "strength": c.strength and [f"{p.inn} {p.amount}" for p in c.strength.ingredients]}
                    for c in parsed]
        except Exception as exc:  # report every outcome
            kept = f"error: {type(exc).__name__}"
        raw = [r["choices"][0]["message"]["content"] for r in Capture.replies if "choices" in r]
        rows.append({"case": name, "call": i, "kept": kept, "raw": raw})
        print(name, i, json.dumps(kept, ensure_ascii=False))
Path(sys.argv[1]).write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
