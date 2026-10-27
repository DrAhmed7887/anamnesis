"""Live smoke test: one real call per Meta model, on synthetic media, behind the SpendGuard cap.

    uv run python scripts/smoke_live.py [--cap 5.00]

The key is read from the macOS Keychain (service META_API_KEY) and never printed or saved.
Outputs: evidence/live/<date>/*.json (provider results only) and the ledger evidence/spend/ledger.jsonl.
Media: scripts/make_synthetic_media.sh -> evidence/raw/media/.
"""

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from anamnesis.core.catalogue import load_catalogue
from anamnesis.providers import ProviderError, SpendCapExceeded, SpendGuard, top_regions
from anamnesis.providers.meta import MetaClient, MetaLabelReader, MetaSegmenter, MetaTranscriber

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "evidence/raw/media"
LEDGER = ROOT / "evidence/spend/ledger.jsonl"


def keychain(service: str) -> str:
    key = subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                         capture_output=True, text=True).stdout.strip()
    if not key:
        sys.exit(f"No {service} in the Keychain.")
    return key


def save(out: Path, name: str, data) -> None:
    (out / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n",
                                      encoding="utf-8")


def step(label: str, fn):
    try:
        result = fn()
        print(f"ok    {label}")
        return result
    except SpendCapExceeded as exc:
        sys.exit(f"STOP  {label}: spend cap reached ({exc})")
    except ProviderError as exc:
        print(f"FAIL  {label}: [{exc.provider}, retryable={exc.retryable}] {exc}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cap", default="5.00", help="total USD cap across all live runs (ledger)")
    args = parser.parse_args()
    guard = SpendGuard(LEDGER, cap_usd=Decimal(args.cap))
    start = guard.total_usd
    out = ROOT / "evidence/live" / datetime.now(UTC).strftime("%Y-%m-%d")
    out.mkdir(parents=True, exist_ok=True)

    client = MetaClient(api_key=keychain("META_API_KEY"))
    brands = [e.brand for e in load_catalogue().entries]

    for lang, bias in [("en", ["English"]), ("ar", ["Arabic", "English"])]:
        wav = (MEDIA / f"voice_{lang}.wav").read_bytes()
        res = step(f"voice {lang}", lambda w=wav, b=bias, lg=lang: MetaTranscriber(client, guard).transcribe(
            w, language_bias=b, keywords=brands, lang_hint=lg))
        if res:
            turns, trace = res
            turn_dumps = [t.model_dump() for t in turns]
            save(out, f"voice_{lang}", {"trace": trace.model_dump(), "turns": turn_dumps})
            for t in turns:
                print(f"      {t.turn_id} {t.start_ms}-{t.end_ms} ms: {t.transcript}")

    image = (MEDIA / "packs.png").read_bytes()
    segmenter = MetaSegmenter(client, guard)
    res = step("sam medicine box", lambda: segmenter.segment(image, "medicine box", mime="image/png"))
    if not res:
        return finish(guard, start)
    regions, trace = res
    save(out, "sam", {"trace": trace.model_dump(), "regions": [r.model_dump() for r in regions]})
    print(f"      {len(regions)} regions: " + ", ".join(
        f"#{r.object_id} ({r.x1},{r.y1})-({r.x2},{r.y2}) c={r.confidence}" for r in regions))

    readings = []
    for region in top_regions(regions):
        res = step(f"spark label {region.region_id}",
                   lambda r=region: MetaLabelReader(client, guard).read(image, r, mime="image/png"))
        if res:
            reading, trace = res
            readings.append({"trace": trace.model_dump(), "reading": reading.model_dump()})
            print(f"      {reading.readability.value}: {reading.label_text!r} inn={reading.inn} "
                  f"strength={reading.strength.model_dump() if reading.strength else None}")
    save(out, "labels", readings)
    finish(guard, start)


def finish(guard: SpendGuard, start: Decimal) -> None:
    print(f"spend this run ${guard.total_usd - start:.5f} · ledger total ${guard.total_usd:.5f} "
          f"of ${guard.cap_usd} cap")


if __name__ == "__main__":
    main()
