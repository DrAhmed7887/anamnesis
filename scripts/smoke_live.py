"""Live smoke test: one real call per Meta model, on synthetic media, behind the SpendGuard cap.

    PYTHONPATH=. uv run python scripts/smoke_live.py [--cap 5.00]

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
from anamnesis.core.reconcile import reconcile_all
from anamnesis.providers import ProviderError, SpendCapExceeded, SpendGuard, top_regions
from anamnesis.providers.claims import MetaClaimExtractor
from anamnesis.providers.meta import MetaClient, MetaLabelReader, MetaSegmenter, MetaTranscriber
from anamnesis.schema import PackObservation

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
    claims_by_lang: dict = {}

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
            got = step(f"spark claims {lang}", lambda ts=turns: MetaClaimExtractor(client, guard).extract(ts))
            if got:
                claims_by_lang[lang], ctrace = got
                save(out, f"claims_{lang}", {"trace": ctrace.model_dump() if ctrace else None,
                                             "claims": [c.model_dump() for c in claims_by_lang[lang]]})
                for c in claims_by_lang[lang]:
                    amount = c.intake_amount or c.strength
                    print(f"      {c.claim_id} {c.name_text!r} status={c.status.value} amount={amount}")

    image = (MEDIA / "packs.png").read_bytes()
    segmenter = MetaSegmenter(client, guard)
    res = None
    # "label" found the packs when "medicine box" found none (27 Oct)
    for concept in ("medicine box", "label"):
        res = step(f"sam {concept!r}", lambda c=concept: segmenter.segment(image, c, mime="image/png"))
        if res and res[0]:
            break
    if not res or not res[0]:
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
            readings.append({"trace": trace.model_dump(), "reading": reading})
            print(f"      {reading.readability.value}: {reading.label_text!r} inn={reading.inn} "
                  f"strength={reading.strength.model_dump() if reading.strength else None}")
    save(out, "labels", [{"trace": r["trace"], "reading": r["reading"].model_dump()} for r in readings])
    for lang, claims in claims_by_lang.items():
        reconcile(out, lang, claims, readings)
    finish(guard, start)


def reconcile(out: Path, lang: str, claims: list, readings: list[dict]) -> None:
    """Offline step: claims Spark extracted from one voice note against the live pack readings."""
    packs = [PackObservation(observation_id=f"o{i}", label_text=r["reading"].label_text, inn=r["reading"].inn,
                             strength=r["reading"].strength, readability=r["reading"].readability,
                             country=r["reading"].country, visual_evidence=[r["reading"].region_id])
             for i, r in enumerate(readings)]
    findings = reconcile_all(claims, packs, load_catalogue())
    save(out, f"findings_{lang}", {"claims_source": f"extracted by muse-spark-1.3 from voice_{lang}",
                                   "findings": [f.model_dump() for f in findings]})
    print(f"      findings ({lang}):")
    for f in findings:
        print(f"      {f.finding_id:7} {f.type.value:34} {f.clinician_note}")


def finish(guard: SpendGuard, start: Decimal) -> None:
    print(f"spend this run ${guard.total_usd - start:.5f} · ledger total ${guard.total_usd:.5f} "
          f"of ${guard.cap_usd} cap")


if __name__ == "__main__":
    main()
