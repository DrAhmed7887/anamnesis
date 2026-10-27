"""Live intake: the bounded agent loop on real Meta models, synthetic media, one report per voice note.

    PYTHONPATH=. uv run python scripts/intake_live.py [--cap 5.00] [--session-usd 0.25]

The key is read from the macOS Keychain (service META_API_KEY) and never printed or saved.
Each intake runs inside a SessionGuard (per-intake $ and call caps) in front of evidence/spend/ledger.jsonl.
Output: evidence/live/<date>/report_<lang>.json (the ReconciliationReport).
Media: scripts/make_synthetic_media.sh.
"""

import argparse
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from anamnesis.agent import run_intake
from anamnesis.core.catalogue import load_catalogue
from anamnesis.providers import SpendGuard
from anamnesis.providers.claims import MetaClaimExtractor
from anamnesis.providers.meta import MetaClient, MetaLabelReader, MetaSegmenter, MetaTranscriber
from anamnesis.providers.spend import SessionGuard

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "evidence/raw/media"
LEDGER = ROOT / "evidence/spend/ledger.jsonl"
MAX_CALLS = 12


def keychain(service: str) -> str:
    key = subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                         capture_output=True, text=True).stdout.strip()
    if not key:
        sys.exit(f"No {service} in the Keychain.")
    return key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cap", default="5.00", help="total USD cap across all live runs (ledger)")
    parser.add_argument("--session-usd", default="0.25", help="USD cap per intake")
    args = parser.parse_args()
    ledger = SpendGuard(LEDGER, cap_usd=Decimal(args.cap))
    out = ROOT / "evidence/live" / datetime.now(UTC).strftime("%Y-%m-%d")
    out.mkdir(parents=True, exist_ok=True)
    client = MetaClient(api_key=keychain("META_API_KEY"))
    catalogue = load_catalogue()
    keywords = [name for entry in catalogue.entries for name in (entry.brand, *entry.aliases)]
    image = (MEDIA / "packs.png").read_bytes()
    start = ledger.total_usd

    for lang, bias in [("en", ["English"]), ("ar", ["Arabic", "English"])]:
        guard = SessionGuard(ledger, max_usd=Decimal(args.session_usd), max_calls=MAX_CALLS)
        report = run_intake(
            (MEDIA / f"voice_{lang}.wav").read_bytes(), [(image, "image/png")],
            transcriber=MetaTranscriber(client, guard), extractor=MetaClaimExtractor(client, guard),
            segmenter=MetaSegmenter(client, guard), reader=MetaLabelReader(client, guard),
            catalogue=catalogue, language_bias=bias, keywords=keywords, lang_hint=lang,
            max_provider_calls=MAX_CALLS,
        )
        (out / f"report_{lang}.json").write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
        print(f"intake {lang}: {report.calls} calls, ${report.spend_usd:.5f}")
        for step in report.steps:
            print(f"      {step.n:2} {step.action.value:16} {step.target[:28]:28} {step.outcome}")
        for f in report.findings:
            print(f"      {f.finding_id:7} {f.type.value:34} {f.clinician_note}")
    spent = ledger.total_usd - start
    print(f"spend this run ${spent:.5f} · ledger total ${ledger.total_usd:.5f} of ${ledger.cap_usd} cap")


if __name__ == "__main__":
    main()
