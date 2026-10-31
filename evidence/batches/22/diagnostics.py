# ruff: noqa: E501  (the code as it ran on 28 Oct, kept as the record of the diagnostics)
"""Diagnostics decided after the 28 Oct comparison run (not pre-registered), from the repo root:

    PYTHONPATH=.:scripts uv run python <this file> fireworks-text   # 5 crops, Fireworks with JSON mode off
    PYTHONPATH=.:scripts uv run python <this file> sam-concepts     # the 19 no-pack photos, other SAM concepts
    PYTHONPATH=.:scripts uv run python <this file> package-read     # Spark 1.3 on those photos' "package" crops
    PYTHONPATH=.:scripts uv run python <this file> baseten-cap      # Baseten's 2 length stops, max_tokens 8,000
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
CAP_PHOTOS = ["public/gemini-commons/augmentin_1g_gsk_box.jpg", "public/gemini-commons/bloxazoc_50mg_krka_box.jpg"]
CAP_TOKENS = 8000


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


def baseten_cap() -> None:
    """Baseten's two length stops in the run, re-read once the same evening with max_tokens 8,000 instead of
    4,000. The request is otherwise byte for byte the run's, and the pre-check estimate covers the cap."""
    import anamnesis.providers.openweight as ow
    estimate, post = ow.spark_call_estimate, OpenWeightClient.post
    ow.spark_call_estimate = lambda body: estimate({**body, "max_tokens": CAP_TOKENS})
    OpenWeightClient.post = lambda self, path, **kw: post(self, path, json={**kw["json"], "max_tokens": CAP_TOKENS})
    key = ev.secret("BASETEN_API_KEY", "BASETEN_API_KEY")
    client = OpenWeightClient(api_key=key, base_url=PRESETS["baseten"]["base_url"], provider="baseten")
    reader = OpenWeightLabelReader(client, guard("0.15"), model=PRESETS["baseten"]["model"],
                                   price_key="muse-spark-open@baseten", json_mode=False)
    with (DAY / "reader_eval_baseten_cap8k.jsonl").open("a", encoding="utf-8") as out:
        for rel in CAP_PHOTOS:
            photo, mime = prepared(rel)
            for region in ev.regions_for(photo, mime, segmenter=None):  # cached: no SAM call
                line = {"photo": rel, "reader": "baseten-8k", "region": region.region_id, "max_tokens": CAP_TOKENS}
                try:
                    reading, trace = reader.read(crop_region(photo, region), region, mime="image/png", cropped=True)
                    line |= {"reading": json.loads(reading.model_dump_json()), "cost_usd": str(trace.cost_usd),
                             "latency_ms": trace.latency_ms, "output_tokens": trace.output_tokens}
                except Exception as exc:
                    line["error"] = f"{type(exc).__name__}: {exc}"[:300]
                    if (spent := getattr(exc, "attempt_trace", None)) is not None:
                        line |= {"cost_usd": str(spent.cost_usd), "output_tokens": spent.output_tokens}
                out.write(json.dumps(line, ensure_ascii=False) + "\n")
                print(rel[-34:], line.get("reading", {}).get("readability", "error"), line.get("output_tokens"))


if __name__ == "__main__":
    {"fireworks-text": fireworks_text, "sam-concepts": sam_concepts, "package-read": package_read,
     "baseten-cap": baseten_cap}[sys.argv[1]]()
