"""Live intake: the bounded agent loop on real Meta models, one report per voice note.

    PYTHONPATH=. uv run python scripts/intake_live.py [--cap 5.00] [--session-usd 0.25]
    PYTHONPATH=. uv run python scripts/intake_live.py --case R1 --voice v1.wav --photo p1.jpg --lang ar \
        [--repeat 10] [--top-k 3] [--reader baseten]

With no --case it runs the two synthetic notes (media: scripts/make_synthetic_media.sh). With --case it runs
one staged case (evidence/batches/21/manifest.md): that voice note and those photos, in order, --repeat times.
--reader baseten makes Meta's open-weight Muse Spark Open on Baseten the label reader (key: BASETEN_API_KEY);
everything else stays on Meta. It refuses any photo outside the public folders that docs/DATA_HANDLING.md lets
go to Baseten, before the first call. Every voice note is re-written to its audio frames alone before any
call, so no metadata chunk is sent or embedded in a brief.
The key comes from MODEL_API_KEY in the environment or the macOS Keychain (service META_API_KEY), and is never
printed or saved. Each intake runs inside a SessionGuard (per-intake $ and call caps) in front of
evidence/spend/ledger.jsonl.
Output, per run:
- evidence/live/<date>/report_<name>.json, the ReconciliationReport (<name>: the language, or case and run);
- one summary line in evidence/live/<date>/runs.jsonl: findings, calls, spend, wall-clock time, and the
  latency of each claim-extraction request against the client's 30 s timeout;
- the brief, evidence/raw/briefs/<date>/<name>.html (git-ignored: it embeds the photos and the voice note).
"""

import argparse
import io
import json
import os
import subprocess
import sys
import time
import wave
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from anamnesis.agent import run_intake
from anamnesis.agent.loop import SAM_CONCEPTS
from anamnesis.brief import render_brief
from anamnesis.core.catalogue import load_catalogue
from anamnesis.providers import SpendGuard
from anamnesis.providers.claims import MetaClaimExtractor
from anamnesis.providers.meta import MetaClient, MetaLabelReader, MetaSegmenter, MetaTranscriber
from anamnesis.providers.openweight import PRESETS, OpenWeightClient, OpenWeightLabelReader
from anamnesis.providers.spend import SessionGuard
from anamnesis.schema import ReconciliationReport

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "evidence/raw/media"
# The only photos that may go to Baseten: Wikimedia Commons and the Cairo CC BY set (docs/DATA_HANDLING.md).
OPEN_WEIGHT_PHOTOS = (MEDIA / "public/commons", MEDIA / "public/gemini-commons", MEDIA / "real-public")
LEDGER = ROOT / "evidence/spend/ledger.jsonl"
LANGUAGES = {"en": ["English"], "ar": ["Arabic", "English"]}
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def keychain(service: str) -> str:
    key = subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                         capture_output=True, text=True).stdout.strip()
    if not key:
        sys.exit(f"No {service} in the Keychain.")
    return key


class TimedClient:
    """The same client, recording how long each request took, a timeout included."""

    def __init__(self, client: MetaClient) -> None:
        self.client, self.latencies_ms = client, []

    def post(self, *args, **kwargs):
        start = time.monotonic()
        try:
            return self.client.post(*args, **kwargs)
        finally:
            self.latencies_ms.append(int((time.monotonic() - start) * 1000))

    def __getattr__(self, name):
        return getattr(self.client, name)


@dataclass
class Run:
    ledger: SpendGuard
    client: MetaClient
    catalogue: object
    session_usd: Decimal
    top_k: int
    reports: Path
    briefs: Path
    open_client: OpenWeightClient | None = None  # set: Muse Spark Open on Baseten reads the labels


def intake(run: Run, name: str, audio: bytes, images: list[tuple[bytes, str]],
           lang: str) -> ReconciliationReport:
    # The loop's own default budget (SPEC §4 Budget): every call it can make. The dollar cap bounds the spend;
    # a fixed 12 dropped a sent pack on a four-photo intake (supervisor 23, round 2 #1).
    calls = 2 + (len(SAM_CONCEPTS) + 2 * run.top_k) * len(images)
    # The guard counts every charged attempt and a call charges at most two (one retry), so twice the loop's
    # budget keeps --session-usd the real bound (supervisor 23 round 3 #6).
    guard = SessionGuard(run.ledger, max_usd=run.session_usd, max_calls=2 * calls)
    timed = TimedClient(run.client)
    keywords = [n for entry in run.catalogue.entries for n in (entry.brand, *entry.aliases)]
    if run.open_client is None:
        reader = MetaLabelReader(run.client, guard)
    else:
        reader = OpenWeightLabelReader(run.open_client, guard, model=PRESETS["baseten"]["model"],
                                       price_key="muse-spark-open@baseten",
                                       json_mode=PRESETS["baseten"]["json_mode"])
    start = time.monotonic()
    report = run_intake(
        audio, images,
        transcriber=MetaTranscriber(run.client, guard), extractor=MetaClaimExtractor(timed, guard),
        segmenter=MetaSegmenter(run.client, guard), reader=reader,
        catalogue=run.catalogue, language_bias=LANGUAGES[lang], keywords=keywords, lang_hint=lang,
        max_provider_calls=calls, top_k=run.top_k,
    )
    wall_s = round(time.monotonic() - start, 1)
    (run.reports / f"report_{name}.json").write_text(report.model_dump_json(indent=2) + "\n", "utf-8")
    brief = render_brief(report, images, (audio, "audio/wav"), run.catalogue)
    (run.briefs / f"{name}.html").write_text(brief, encoding="utf-8")
    line = {"run": name, "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "reader": "spark" if run.open_client is None else "baseten", "calls": report.calls,
            "spend_usd": str(report.spend_usd), "wall_s": wall_s, "claim_request_ms": timed.latencies_ms,
            "findings": [[f.type.value, f.claim_id, f.observation_id] for f in report.findings]}
    with (run.reports / "runs.jsonl").open("a", encoding="utf-8") as out:
        out.write(json.dumps(line) + "\n")
    print(f"intake {name}: {report.calls} calls, ${report.spend_usd:.5f}, {wall_s} s, "
          f"claim requests {timed.latencies_ms} ms (timeout 30000)")
    for step in report.steps:
        print(f"      {step.n:2} {step.action.value:16} {step.target[:28]:28} {step.outcome}")
    for f in report.findings:
        print(f"      {f.finding_id:7} {f.type.value:34} {f.clinician_note}")
    return report


def photo(path: str) -> tuple[bytes, str]:
    file = Path(path)
    if file.suffix.lower() not in MIME:
        sys.exit(f"{file}: PNG or JPEG only (convert HEIC with sips first)")
    return file.read_bytes(), MIME[file.suffix.lower()]


def voice(path: Path) -> bytes:
    """The WAV's audio frames alone, re-written so no metadata chunk reaches a model or a brief (M8 #7)."""
    try:
        with wave.open(io.BytesIO(path.read_bytes())) as source:
            params, frames = source.getparams(), source.readframes(source.getnframes())
    except (wave.Error, EOFError) as exc:
        sys.exit(f"{path}: not a PCM WAV ({exc}); convert it with ffmpeg -map_metadata -1 first")
    out = io.BytesIO()
    with wave.open(out, "wb") as clean:
        clean.setparams(params)
        clean.writeframes(frames)
    return out.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cap", default="5.00", help="total USD cap across all live runs (ledger)")
    parser.add_argument("--session-usd", default="0.25", help="USD cap per intake")
    parser.add_argument("--case", help="a staged case id from the batch 21 manifest")
    parser.add_argument("--voice", help="the case's voice note (16 kHz mono WAV)")
    parser.add_argument("--photo", action="append", default=[], help="a photo of the case, in order")
    parser.add_argument("--lang", choices=sorted(LANGUAGES), default="en")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--top-k", type=int, default=3, help="SAM regions kept per photo")
    parser.add_argument("--reader", choices=("spark", "baseten"), default="spark",
                        help="label reader: Spark 1.3, or Muse Spark Open on Baseten (public photos only)")
    args = parser.parse_args()
    if args.case and not (args.voice and args.photo):
        sys.exit("--case needs --voice and at least one --photo")
    if args.top_k < 0:  # SAM's top_regions refuses it, but only mid-run, after spend (M8 #1)
        sys.exit("--top-k must be 0 or more")
    if args.reader == "baseten":
        if not args.case:
            sys.exit("--reader baseten needs --case: the synthetic notes' pack image may not go to Baseten")
        for path in args.photo:  # checked before any call
            resolved = Path(path).resolve()
            if not any(resolved.is_relative_to(folder.resolve()) for folder in OPEN_WEIGHT_PHOTOS):
                sys.exit(f"{path} is not a public photo that may go to Baseten (docs/DATA_HANDLING.md). "
                         "Ahmed's own media never go there.")
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    run = Run(SpendGuard(LEDGER, cap_usd=Decimal(args.cap)),
              MetaClient(api_key=os.environ.get("MODEL_API_KEY") or keychain("META_API_KEY")),
              load_catalogue(), Decimal(args.session_usd), args.top_k,
              ROOT / "evidence/live" / day, ROOT / "evidence/raw/briefs" / day)
    if args.reader == "baseten":
        run.open_client = OpenWeightClient(
            api_key=os.environ.get("BASETEN_API_KEY") or keychain("BASETEN_API_KEY"),
            base_url=PRESETS["baseten"]["base_url"], provider="baseten")
    run.reports.mkdir(parents=True, exist_ok=True)
    run.briefs.mkdir(parents=True, exist_ok=True)
    start = run.ledger.total_usd
    if args.case:
        audio, images = voice(Path(args.voice)), [photo(p) for p in args.photo]
        for i in range(1, args.repeat + 1):
            name = args.case if args.repeat == 1 else f"{args.case}_r{i:02d}"
            intake(run, name, audio, images, args.lang)
    else:
        image = [((MEDIA / "packs.png").read_bytes(), "image/png")]
        for lang in ("en", "ar"):
            intake(run, lang, voice(MEDIA / f"voice_{lang}.wav"), image, lang)
    ledger = run.ledger
    spent = ledger.total_usd - start
    print(f"spend this run ${spent:.5f} · ledger total ${ledger.total_usd:.5f} of ${ledger.cap_usd} cap")


if __name__ == "__main__":
    main()
