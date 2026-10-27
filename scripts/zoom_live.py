"""Live crop-zoom check on staged hard photos (batch 15.5): what the loop does, and whether the zoom helps.

    PYTHONPATH=. uv run python scripts/zoom_live.py --tag before [--compare] [--cap 5.00] [--session-usd 0.15]

Images only, no audio. Each photo goes through run_intake as an intake would: segment, read a crop of each
top region (since batch 18), one zoom per unreadable or partial reading. Recording wrappers keep the frame SAM
reported and the size, tokens and readability of every read. --compare also reads the full photo for every
region, with the box given as text (the read before batch 18), so a full-photo and a crop reading of the same
pack sit side by side. The expected reading of each pack
comes from evidence/raw/media/hard/manifest.json (scripts/make_hard_media.sh), written before any model saw
the images.
The key is read from the macOS Keychain (service META_API_KEY) and never printed or saved.
Output: evidence/live/<date>/zoom_<tag>/<photo>.json and summary.md.
"""

import argparse
import io
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from PIL import Image

from anamnesis.agent import run_intake
from anamnesis.core.catalogue import load_catalogue
from anamnesis.providers import SpendGuard
from anamnesis.providers.meta import MetaClient, MetaLabelReader, MetaSegmenter
from anamnesis.providers.spend import SessionGuard

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "evidence/raw/media/hard"
LEDGER = ROOT / "evidence/spend/ledger.jsonl"
MAX_CALLS = 10
COMPARE_CALLS = 3  # one full-photo read per region the loop read (top_k = 3)


def keychain(service: str) -> str:
    key = subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                         capture_output=True, text=True).stdout.strip()
    if not key:
        sys.exit(f"No {service} in the Keychain.")
    return key


class RecordingSegmenter:
    def __init__(self, inner) -> None:
        self.inner, self.calls = inner, []

    def segment(self, image, concept, *, mime):
        regions, trace = self.inner.segment(image, concept, mime=mime)
        self.calls.append({"concept": concept, "regions": len(regions),
                           "frames": sorted({(r.frame_w, r.frame_h) for r in regions})})
        return regions, trace


class RecordingReader:
    def __init__(self, inner) -> None:
        self.inner, self.calls = inner, []

    def read(self, image, region, *, mime, cropped=False):
        reading, trace = self.inner.read(image, region, mime=mime, cropped=cropped)
        self.calls.append({
            "region_id": region.region_id, "cropped": cropped,
            "sent_size": Image.open(io.BytesIO(image)).size,
            "input_tokens": trace.input_tokens, "output_tokens": trace.output_tokens,
            "readability": reading.readability.value, "label_text": reading.label_text,
        })
        return reading, trace


def pack_for(region, item):
    """The staged pack whose box holds the region's centre, in the frame the region declares."""
    stored = Image.open(MEDIA / item["file"]).size
    frame = (region.frame_w, region.frame_h)
    key = ("box_displayed" if list(frame) == item["frame_displayed"]
           else "box_stored" if frame == stored else None)
    if key is None:
        return None
    cx, cy = (region.x1 + region.x2) / 2, (region.y1 + region.y2) / 2
    hits = [p for p in item["packs"] if p[key][0] <= cx <= p[key][2] and p[key][1] <= cy <= p[key][3]]
    return hits[0] if hits else None


def verdict(observation, pack) -> str:
    if pack is None:
        return "no staged pack under this region"
    if observation.readability.value != "readable":
        return f"abstained ({observation.readability.value})"
    text = re.sub(r"\s+", " ", (observation.label_text or "").lower())
    brand, strength = pack["label"].lower().split(" ", 1)
    return "correct" if brand.split("-")[0] in text and strength.replace(" ", "") in text.replace(" ", "") \
        else "WRONG"


def prepared_bytes(data: bytes) -> bytes:
    from anamnesis.agent import prepare_image  # batch 15.5

    return prepare_image(data, "image/jpeg")[0]


def first_and_zoom(calls: list[dict], region_id: str) -> tuple[dict | None, dict | None]:
    """A region's first read and its zoom. Since batch 18 both are crops, so they are told apart by order."""
    reads = [c for c in calls if c["region_id"] == region_id] + [None, None]
    return reads[0], reads[1]


def compare_reads(report, reader, image: bytes) -> dict:
    """Read the full photo for every region the loop read; returns region_id -> (call record, reading)."""
    regions = {r.region_id: r for r in report.regions}
    forced = {}
    for obs in report.observations:
        region = regions[obs.visual_evidence[0]]
        reading, _ = reader.read(image, region, mime="image/jpeg")
        forced[region.region_id] = (reader.calls[-1], reading)
    return forced


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True, help="before or after (the output folder name)")
    parser.add_argument("--cap", default="5.00", help="total USD cap across all live runs (ledger)")
    parser.add_argument("--session-usd", default="0.15", help="USD cap per photo")
    parser.add_argument("--compare", action="store_true", help="also read a crop of every region")
    args = parser.parse_args()
    manifest = json.loads((MEDIA / "manifest.json").read_text(encoding="utf-8"))
    ledger = SpendGuard(LEDGER, cap_usd=Decimal(args.cap))
    out = ROOT / "evidence/live" / datetime.now(UTC).strftime("%Y-%m-%d") / f"zoom_{args.tag}"
    out.mkdir(parents=True, exist_ok=True)
    client = MetaClient(api_key=keychain("META_API_KEY"))
    catalogue = load_catalogue()
    start = ledger.total_usd
    rows = ["| photo | region | staged pack | first read | zoom read | final | verdict | full-photo read |",
            "|---|---|---|---|---|---|---|---|"]

    for item in manifest:
        data = (MEDIA / item["file"]).read_bytes()
        guard = SessionGuard(ledger, max_usd=Decimal(args.session_usd),
                             max_calls=MAX_CALLS + (COMPARE_CALLS if args.compare else 0))
        segmenter = RecordingSegmenter(MetaSegmenter(client, guard))
        reader = RecordingReader(MetaLabelReader(client, guard))
        report = run_intake(None, [(data, "image/jpeg")], transcriber=None, extractor=None,
                            segmenter=segmenter, reader=reader, catalogue=catalogue,
                            max_provider_calls=MAX_CALLS)
        loop_reads = len(reader.calls)  # the loop's own reads; full-photo reads come after
        forced = compare_reads(report, reader, prepared_bytes(data)) if args.compare else {}
        record = {"photo": item["file"], "orientation": item["orientation"], "loop_reads": loop_reads,
                  "stored_size": Image.open(io.BytesIO(data)).size, "segment_calls": segmenter.calls,
                  "reads": reader.calls, "report": report.model_dump(mode="json")}
        target = out / item["file"].replace(".jpg", ".json")
        target.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"{item['file']}: {report.calls} calls, ${report.spend_usd:.5f}, SAM frames "
              f"{[c['frames'] for c in segmenter.calls]}")
        for step in report.steps:
            print(f"      {step.n:2} {step.action.value:12} {step.target[:30]:30} {step.outcome}")
        regions = {r.region_id: r for r in report.regions}
        for obs in report.observations:
            region = regions[obs.visual_evidence[0]]
            pack = pack_for(region, item)
            first, zoom = first_and_zoom(reader.calls[:loop_reads], region.region_id)

            def cell(call):
                return "-" if call is None else f"{call['readability']}, {call['input_tokens']} tok"

            final = (obs.label_text or "-").splitlines()[0]
            staged = pack["label"] if pack else "-"
            crop_read = forced.get(region.region_id)
            crop_cell = "-" if crop_read is None else f"{cell(crop_read[0])}, {verdict(crop_read[1], pack)}"
            rows.append(f"| {item['file']} | {region.region_id} | {staged} | {cell(first)} | "
                        f"{cell(zoom)} | {final} | {verdict(obs, pack)} | {crop_cell} |")
        missed = [p["label"] for p in item["packs"]
                  if not any(pack_for(regions[o.visual_evidence[0]], item) is p for o in report.observations)]
        if missed:
            rows.append(f"| {item['file']} | - | {', '.join(missed)} | not read | - | - | missed | - |")

    spent = ledger.total_usd - start
    summary = "\n".join([f"# Crop-zoom live check ({args.tag})", "", *rows, "",
                         f"Spend this run ${spent:.5f}; ledger total ${ledger.total_usd:.5f} "
                         f"of ${ledger.cap_usd} cap.",
                         ""])
    (out / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
