"""U2 diagnostic after batch 30 (31 Oct, post hoc): Spark 1.3's raw claim replies, with batch 29's prompt, five calls, to see
why both claims sometimes lose their amounts. Keys from the Keychain, never printed."""
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

from anamnesis.providers import SpendGuard
from anamnesis.providers.claims import MetaClaimExtractor
from anamnesis.providers.meta import MetaClient
from anamnesis.schema import AudioTurn

OUT = Path(sys.argv[1])
TEXT = "I take Augmentin, 875 and 125 milligrams, twice a day"
TURNS = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=5200, transcript=TEXT)]


class Capture(MetaClient):
    replies: list = []

    def post(self, path, **kwargs):  # noqa: D102
        payload, latency_ms = super().post(path, **kwargs)
        Capture.replies.append(payload)
        return payload, latency_ms


key = subprocess.run(["security", "find-generic-password", "-s", "META_API_KEY", "-w"],
                     capture_output=True, text=True, check=True).stdout.strip()
guard = SpendGuard(Path("evidence/spend/ledger.jsonl"), cap_usd=Decimal("20.00"))
extractor = MetaClaimExtractor(Capture(api_key=key), guard)
rows = []
for i in range(5):
    Capture.replies.clear()
    try:
        claims, _ = extractor.extract(TURNS)
        kept = [(c.name_text, c.strength and [(p.inn, str(p.amount)) for p in c.strength.ingredients], c.intake_amount and str(c.intake_amount.amount)) for c in claims]
    except Exception as exc:  # report every outcome
        kept = f"error: {type(exc).__name__}"
    raw = []
    for reply in Capture.replies:
        try:
            raw.append(reply["choices"][0]["message"]["content"])
        except Exception:
            raw.append(str(reply)[:500])
    rows.append({"call": i, "kept": kept, "raw": raw})
    print(i, kept)
OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
