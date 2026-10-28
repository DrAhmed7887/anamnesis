# ruff: noqa: E501  (the code as it ran on 28 Oct, kept as the record of the diagnostics)
"""Two diagnostics decided after the 28 Oct comparison run (not pre-registered), from the repo root:

    PYTHONPATH=.:scripts uv run python <this file> fireworks-text   # 5 crops, Fireworks with JSON mode off
    PYTHONPATH=.:scripts uv run python <this file> sam-concepts     # the 19 no-pack photos, other SAM concepts
"""

import json
import sys
from decimal import Decimal

import reader_eval as ev

from anamnesis.agent.crop import crop_region
from anamnesis.agent.media import prepare_image
from anamnesis.providers import SpendGuard
from anamnesis.providers.meta import MetaClient, MetaSegmenter
from anamnesis.providers.openweight import PRESETS, OpenWeightClient, OpenWeightLabelReader
from anamnesis.providers.spend import SessionGuard

DAY = ev.ROOT / "evidence/live/2026-10-28"
FW_PHOTOS = ["real-public/bjy2svvmn8/bjy2svvmn8_pk014_a.jpg", "real-public/bjy2svvmn8/bjy2svvmn8_pk002_b.jpg",
             "real-public/bjy2svvmn8/bjy2svvmn8_pk068_b.jpg", "public/gemini-commons/concor_5mg_china_retail.jpg",
             "public/gemini-commons/siofor_500mg_metformin_box.jpg"]
CONCEPTS = ("package", "box", "bottle", "blister pack")


def guard(usd: str) -> SessionGuard:
    return SessionGuard(SpendGuard(ev.LEDGER, cap_usd=Decimal("6.50")), max_usd=Decimal(usd), max_calls=100)


def prepared(rel: str) -> tuple[bytes, str]:
    path = ev.public_photo(rel)
    return prepare_image(path.read_bytes(), "image/png" if path.suffix.lower() == ".png" else "image/jpeg")


def fireworks_text() -> None:
    key = ev.secret("FIREWORKS_API_KEY", "FIREWORKS_API_KEY")
    client = OpenWeightClient(api_key=key, base_url=PRESETS["fireworks"]["base_url"], provider="fireworks")
    reader = OpenWeightLabelReader(client, guard("0.30"), model=PRESETS["fireworks"]["model"],
                                   price_key="muse-spark-open@fireworks", json_mode=False)
    with (DAY / "reader_eval_fireworks_textmode.jsonl").open("a", encoding="utf-8") as out:
        for rel in FW_PHOTOS:
            photo, mime = prepared(rel)
            for region in ev.regions_for(photo, mime, segmenter=None):  # cached: no SAM call
                line = {"photo": rel, "reader": "fireworks-text", "region": region.region_id}
                try:
                    reading, trace = reader.read(crop_region(photo, region), region, mime="image/png", cropped=True)
                    line |= {"reading": json.loads(reading.model_dump_json()), "cost_usd": str(trace.cost_usd),
                             "latency_ms": trace.latency_ms}
                except Exception as exc:
                    line["error"] = f"{type(exc).__name__}: {exc}"[:300]
                out.write(json.dumps(line, ensure_ascii=False) + "\n")
                print(rel[-34:], line.get("reading", {}).get("readability", "error"))


def sam_concepts() -> None:
    lines = [json.loads(line) for line in (DAY / "reader_eval.jsonl").read_text(encoding="utf-8").splitlines()]
    photos = sorted({line["photo"] for line in lines if line.get("no_region")})
    segmenter = MetaSegmenter(MetaClient(api_key=ev.secret("MODEL_API_KEY", "META_API_KEY")), guard("0.40"))
    with (DAY / "sam_concepts_diagnostic.jsonl").open("a", encoding="utf-8") as out:
        for rel in photos:
            photo, mime = prepared(rel)
            for concept in CONCEPTS:
                regions, trace = segmenter.segment(photo, concept, mime=mime)
                best = max((r.confidence or 0 for r in regions), default=None)
                out.write(json.dumps({"photo": rel, "concept": concept, "regions": len(regions), "best": best,
                                      "cost_usd": str(trace.cost_usd)}) + "\n")
                if regions:
                    break
            print(rel[-26:], concept, len(regions))


def package_read() -> None:
    """Spark 1.3 reads the crops SAM finds with "package" on the photos where the loop's concepts found none."""
    from anamnesis.providers.meta import MetaLabelReader
    lines = [json.loads(line) for line in (DAY / "reader_eval.jsonl").read_text(encoding="utf-8").splitlines()]
    photos = sorted({line["photo"] for line in lines if line.get("no_region")})
    meta = MetaClient(api_key=ev.secret("MODEL_API_KEY", "META_API_KEY"))
    session = guard("0.40")
    segmenter, reader = MetaSegmenter(meta, session), MetaLabelReader(meta, session)
    cache = ev.ROOT / "evidence/raw/eval/segments-package"  # apart from the pre-registered run's cache
    cache.mkdir(parents=True, exist_ok=True)
    with (DAY / "reader_eval_package.jsonl").open("a", encoding="utf-8") as out:
        for rel in photos:
            photo, mime = prepared(rel)
            found, _ = segmenter.segment(photo, "package", mime=mime)
            found = sorted(found, key=lambda region: -(region.confidence or 0))[:ev.TOP_K]
            (cache / f"{rel.split('/')[-1]}.json").write_text(
                json.dumps([region.model_dump(mode="json") for region in found], indent=1))
            for region in found:
                line = {"photo": rel, "reader": "spark-package", "region": region.region_id}
                try:
                    reading, trace = reader.read(crop_region(photo, region), region, mime="image/png", cropped=True)
                    line |= {"reading": json.loads(reading.model_dump_json()), "cost_usd": str(trace.cost_usd),
                             "latency_ms": trace.latency_ms}
                except Exception as exc:
                    line["error"] = f"{type(exc).__name__}: {exc}"[:300]
                out.write(json.dumps(line, ensure_ascii=False) + "\n")
                print(rel[-26:], line.get("reading", {}).get("readability", "error"))


if __name__ == "__main__":
    {"fireworks-text": fireworks_text, "sam-concepts": sam_concepts, "package-read": package_read}[sys.argv[1]]()
