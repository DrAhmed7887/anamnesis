"""Zero-shot label reading: Spark 1.3 against Meta's open-weight Spark Open, on public photos.

    PYTHONPATH=. uv run python scripts/reader_eval.py --key evidence/batches/22/preregistration.json \
        --key evidence/batches/22/preregistration-gemini.json --readers spark,fireworks [--cap 4.00]
    PYTHONPATH=. uv run python scripts/reader_eval.py --key ... --score-only <reader_eval.jsonl>

Each photo is prepared as the loop prepares it (SPEC §4 step 0). SAM 3.1 segments it once, with
"medicine box" and then "label" as the loop does, keeping the 3 most confident regions, and the result
is cached in evidence/raw/eval/. Every reader then reads the same crops (SPEC §4, "Open-weight label
reader"). Before any call, the script refuses a photo outside media/public/ and media/real-public/:
Ahmed's own media never go to these providers (docs/DATA_HANDLING.md).
Output: evidence/live/<date>/reader_eval.jsonl, one line per photo, reader and region, then a score
table by the rules in evidence/batches/22/preregistration-notes.md.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from anamnesis.agent.crop import crop_region
from anamnesis.agent.media import prepare_image
from anamnesis.providers import SpendGuard
from anamnesis.providers.meta import MetaClient, MetaLabelReader, MetaSegmenter
from anamnesis.providers.openweight import PRESETS, OpenWeightClient, OpenWeightLabelReader
from anamnesis.providers.spend import SessionGuard, SpendCapExceeded
from anamnesis.schema import ImageRegion
from anamnesis.schema.medication import canonical_inn

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "evidence/raw/media"
PUBLIC = (MEDIA / "public", MEDIA / "real-public")  # the only photos that may go to Fireworks or Baseten
LEDGER = ROOT / "evidence/spend/ledger.jsonl"
CACHE = ROOT / "evidence/raw/eval/segments"
TOP_K = 3
TO_MG = {"mg": Decimal(1), "g": Decimal(1000), "mcg": Decimal("0.001")}
PER_UNIT = {None, "tablet", "capsule", "dose"}
COMBINED = re.compile(r"\s*(?:\+|/|&|\band\b|\bwith\b)\s*", re.IGNORECASE)  # "loratadine + pseudoephedrine"
# Scored without these words, so "rosuvastatin calcium" counts as rosuvastatin (preregistration notes).
SALT_WORDS = {
    "hydrochloride", "hcl", "hydrobromide", "calcium", "sodium", "potassium", "magnesium", "phosphate",
    "sulfate", "sulphate", "succinate", "tartrate", "fumarate", "maleate", "besylate", "besilate",
    "mesylate", "mesilate", "citrate", "acetate", "cilexetil", "medoxomil", "monohydrate", "dihydrate",
    "trihydrate", "hemihydrate",
}
Reader = MetaLabelReader | OpenWeightLabelReader


def secret(env: str, service: str) -> str:
    value = os.environ.get(env) or subprocess.run(
        ["security", "find-generic-password", "-s", service, "-w"], capture_output=True, text=True
    ).stdout.strip()
    if not value:
        sys.exit(f"No {service} in the environment or the Keychain.")
    return value


def public_photo(rel: str) -> Path:
    path = (MEDIA / rel).resolve()
    if not any(path.is_relative_to(folder.resolve()) for folder in PUBLIC):
        sys.exit(f"{rel} is not a public test photo. Ahmed's own media never go to Fireworks or Baseten.")
    return path


def readers(names: list[str], meta: MetaClient, guard: SessionGuard) -> dict[str, Reader]:
    built: dict[str, Reader] = {}
    for name in names:
        if name == "spark":
            built[name] = MetaLabelReader(meta, guard)
            continue
        preset, service = PRESETS[name], f"{name.upper()}_API_KEY"
        client = OpenWeightClient(api_key=secret(service, service), base_url=preset["base_url"],
                                  provider=name)
        price_key = f"muse-spark-open@{name}"
        built[name] = OpenWeightLabelReader(client, guard, model=preset["model"], price_key=price_key,
                                            json_mode=preset["json_mode"])
    return built


def regions_for(photo: bytes, mime: str, segmenter: MetaSegmenter) -> list[ImageRegion]:
    cached = CACHE / f"{hashlib.sha256(photo).hexdigest()}.json"
    if cached.exists():
        return [ImageRegion(**region) for region in json.loads(cached.read_text())]
    found: list[ImageRegion] = []
    for concept in ("medicine box", "label"):
        found, _ = segmenter.segment(photo, concept, mime=mime)
        if found:
            break
    found = sorted(found, key=lambda region: -(region.confidence or 0))[:TOP_K]
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps([region.model_dump(mode="json") for region in found], indent=1))
    return found


def read_photo(rel: str, path: Path, segmenter: MetaSegmenter, built: dict[str, Reader]) -> Iterator[dict]:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    photo, mime = prepare_image(path.read_bytes(), mime)
    regions = regions_for(photo, mime, segmenter)
    if not regions:
        yield from ({"photo": rel, "reader": name, "region": None, "no_region": True} for name in built)
        return
    for region in regions:
        crop = crop_region(photo, region)
        for name, reader in built.items():
            line: dict = {"photo": rel, "reader": name, "region": region.region_id}
            try:
                reading, trace = reader.read(crop, region, mime="image/png", cropped=True)
                line |= {"reading": json.loads(reading.model_dump_json()), "cost_usd": str(trace.cost_usd),
                         "latency_ms": trace.latency_ms}
            except SpendCapExceeded:
                raise
            except Exception as exc:  # a failed read is a result too
                line["error"] = f"{type(exc).__name__}: {exc}"[:300]
            print(f"{rel[-40:]:40} {name:9} {line.get('reading', {}).get('readability', 'error')}")
            yield line


def run(key: list[dict], names: list[str], cap: str) -> Path:
    photos = [public_photo(case["photo"]) for case in key]  # every path is checked before the first call
    ledger = SpendGuard(LEDGER, cap_usd=Decimal(cap))
    guard = SessionGuard(ledger, max_usd=Decimal(cap), max_calls=10_000)
    meta = MetaClient(api_key=secret("MODEL_API_KEY", "META_API_KEY"))
    segmenter, built = MetaSegmenter(meta, guard), readers(names, meta, guard)
    out = ROOT / "evidence/live" / datetime.now(UTC).strftime("%Y-%m-%d") / "reader_eval.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        for case, path in zip(key, photos, strict=True):
            for line in read_photo(case["photo"], path, segmenter, built):
                fh.write(json.dumps(line, ensure_ascii=False) + "\n")
                fh.flush()
    print(f"ledger total ${ledger.total_usd:.5f}")
    return out


def moiety(name: str) -> str:
    inn = canonical_inn(name)
    words = [word for word in inn.split() if word not in SALT_WORDS]
    return canonical_inn(" ".join(words)) if words else inn


def amount(value: object, unit: str, per: str | None = None) -> object:
    """Milligrams per dosage unit, or the raw text for anything else, which never equals a key strength."""
    rate = TO_MG.get(unit)
    if rate is None or per not in PER_UNIT:
        return f"{value} {unit} per {per}"
    return Decimal(str(value)) * rate


def key_strengths(rows: list) -> dict[str, object]:
    # A unit outside the schema (mg/5 ml, %) means that strength null is the right reading.
    return {moiety(inn): amount(value, unit) for inn, value, unit in rows if unit in TO_MG}


def outcome(case: dict, reading: dict) -> str:
    """correct, harmful or miss, for one readable reading of one crop."""
    expected_inns = {moiety(inn) for inn in case["expected_inns"]}
    options = [key_strengths(case["expected_strengths"])]
    if case.get("also_accepted_strengths"):
        options.append(key_strengths(case["also_accepted_strengths"]))
    strength = reading.get("strength") or {}
    parts = {moiety(part["inn"]): amount(part["amount"], part["unit"], strength.get("per"))
             for part in strength.get("ingredients") or []}
    inns = set(parts) | {moiety(name) for name in COMBINED.split(reading.get("inn") or "") if name.strip()}
    if inns - expected_inns or not any(all(option.get(inn) == value for inn, value in parts.items())
                                       for option in options):
        return "harmful"  # an INN or a strength shown as fact that is not printed, or is wrong
    return "correct" if inns == expected_inns and parts in options else "miss"


def verdict(case: dict, lines: list[dict]) -> str:
    """One photo and reader, its crops together: harmful beats correct beats miss."""
    if all(line.get("no_region") for line in lines):
        return "no pack found"
    readings = [line["reading"] for line in lines if "reading" in line]
    if not readings:
        return "error"
    outcomes = {outcome(case, reading) for reading in readings if reading.get("readability") == "readable"}
    if not outcomes:
        return "correct" if case["abstain_is_correct"] else "abstained"
    return next(result for result in ("harmful", "correct", "miss") if result in outcomes)


def score(key: list[dict], results: Path) -> None:
    lines = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines() if line.strip()]
    names = sorted({line["reader"] for line in lines})
    print(f"{'photo':42} " + " ".join(f"{name:14}" for name in names))
    totals: dict[str, dict[str, int]] = {name: {} for name in names}
    for case in key:
        row = []
        for name in names:
            mine = [line for line in lines if line["photo"] == case["photo"] and line["reader"] == name]
            result = verdict(case, mine) if mine else "not run"
            totals[name][result] = totals[name].get(result, 0) + 1
            row.append(f"{result:14}")
        print(f"{case['photo'][-42:]:42} " + " ".join(row))
    for name in names:
        spent = sum(Decimal(line.get("cost_usd", "0")) for line in lines if line["reader"] == name)
        print(f"{name}: {json.dumps(totals[name])}, ${spent:.4f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True, action="append", help="a pre-registered key (repeatable)")
    parser.add_argument("--readers", default="spark,fireworks")
    parser.add_argument("--cap", default="4.00", help="USD cap on the ledger's total")
    parser.add_argument("--score-only", help="score an existing reader_eval.jsonl, with no call")
    args = parser.parse_args()
    key = [case for path in args.key for case in json.loads(Path(path).read_text(encoding="utf-8"))]
    names = args.readers.split(",")
    if unknown := set(names) - {"spark", *PRESETS}:
        sys.exit(f"Unknown reader: {', '.join(sorted(unknown))}")
    results = Path(args.score_only) if args.score_only else run(key, names, args.cap)
    score(key, results)


if __name__ == "__main__":
    main()
