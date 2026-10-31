"""U2 diagnostic after batch 30 (31 Oct, post hoc): Spark 1.3's raw claim replies, with batch 29's prompt,
three calls on each missed run's exact transcript, to see
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
# The exact transcripts of the two live runs that missed (report_U2-b30_r02 and _r03).
TEXTS = ["I take take Augmentin, 875 875 and 125 milligrams twice a day",
         "I take Augmentin, 875 and 125 milligrams, twice a day,"]


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
for i, TEXT in enumerate([t for t in TEXTS for _ in range(3)]):
    TURNS = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=5580, transcript=TEXT, lang_hint="en")]
    Capture.replies.clear()
    try:
        claims, _ = extractor.extract(TURNS)
        kept = [(c.name_text, c.strength and [(p.inn, str(p.amount)) for p in c.strength.ingredients],
                 c.intake_amount and str(c.intake_amount.amount)) for c in claims]
    except Exception as exc:  # report every outcome
        kept = f"error: {type(exc).__name__}"
    raw = []
    for reply in Capture.replies:
        try:
            raw.append(reply["choices"][0]["message"]["content"])
        except Exception:
            raw.append(str(reply)[:500])
    rows.append({"call": i, "transcript": TEXT, "kept": kept, "raw": raw})
    print(i, kept)
OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
