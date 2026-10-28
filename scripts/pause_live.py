"""Live photo request: one intake, the clinician's request for its unreadable pack, then the new photo.

SPEC §8.

    PYTHONPATH=. uv run python scripts/pause_live.py --case U11 --voice v.wav --photo first.jpg \
        --rephoto second.jpg [--lang en] [--cap 5.00] [--session-usd 0.25]

The first photo goes through the intake exactly as in scripts/intake_live.py, and is saved as
<case>-before. The first `unreadable` target that `requestable` lists gets a photo request. The second
photo answers it through `add_photo`, under its own SessionGuard. If the intake leaves nothing
unreadable, the script stops there and sends no second photo.
Output, in evidence/live/<date>/: report_<case>-before.json and report_<case>-after.json, review_<case>.json
(the request, the message to the patient and the answered review), and a runs.jsonl line for the second half.
The two briefs go to evidence/raw/briefs/<date>/ (git-ignored: they embed the photos and the voice note).
"""

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import intake_live as il

from anamnesis.agent.loop import SAM_CONCEPTS
from anamnesis.brief import render_brief
from anamnesis.core.catalogue import load_catalogue
from anamnesis.providers import SpendGuard
from anamnesis.providers.meta import MetaClient, MetaLabelReader, MetaSegmenter
from anamnesis.providers.spend import SessionGuard
from anamnesis.review import add_photo, new_review, request_message, request_photo, requestable
from anamnesis.schema.review import RequestKind


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--voice", required=True, help="the case's voice note (16 kHz mono WAV)")
    parser.add_argument("--photo", required=True, help="the first photo, sent with the voice note")
    parser.add_argument("--rephoto", required=True, help="the new photo that answers the request")
    parser.add_argument("--lang", choices=sorted(il.LANGUAGES), default="en")
    parser.add_argument("--cap", default="5.00", help="total USD cap across all live runs (ledger)")
    parser.add_argument("--session-usd", default="0.25", help="USD cap per half")
    args = parser.parse_args()
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    run = il.Run(SpendGuard(il.LEDGER, cap_usd=Decimal(args.cap)),
                 MetaClient(api_key=os.environ.get("MODEL_API_KEY") or il.keychain("META_API_KEY")),
                 load_catalogue(), Decimal(args.session_usd), 3,
                 il.ROOT / "evidence/live" / day, il.ROOT / "evidence/raw/briefs" / day)
    run.reports.mkdir(parents=True, exist_ok=True)
    run.briefs.mkdir(parents=True, exist_ok=True)
    audio, images, rephoto = il.voice(Path(args.voice)), [il.photo(args.photo)], il.photo(args.rephoto)
    start = run.ledger.total_usd

    before = il.intake(run, f"{args.case}-before", audio, images, args.lang)
    targets = [target for kind, target in requestable(before) if kind is RequestKind.UNREADABLE]
    if not targets:
        sys.exit(f"{args.case}: nothing unreadable to request; the case is not triggered, "
                 "and no second photo is sent")
    review = request_photo(new_review(before), before, targets[0])
    request = review.requests[-1]
    message = request_message(before, request)
    print(f"request {request.request_id} for {targets[0]}: {message}")
    (run.briefs / f"{args.case}-before.html").write_text(
        render_brief(before, images, (audio, "audio/wav"), run.catalogue, review), encoding="utf-8")

    budget = len(SAM_CONCEPTS) + 2 * run.top_k  # add_photo's own default (SPEC §8)
    guard = SessionGuard(run.ledger, max_usd=run.session_usd, max_calls=2 * budget)
    clock = time.monotonic()
    after, answered = add_photo(before, review, request.request_id, rephoto, images, (audio, "audio/wav"),
                                segmenter=MetaSegmenter(run.client, guard),
                                reader=MetaLabelReader(run.client, guard),
                                catalogue=run.catalogue, top_k=run.top_k)
    wall_s = round(time.monotonic() - clock, 1)
    (run.reports / f"report_{args.case}-after.json").write_text(
        after.model_dump_json(indent=2) + "\n", "utf-8")
    record = {"request": json.loads(request.model_dump_json()), "message": message,
              "answered": json.loads(answered.model_dump_json())}
    (run.reports / f"review_{args.case}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    brief = render_brief(after, [*images, rephoto], (audio, "audio/wav"), run.catalogue, answered)
    (run.briefs / f"{args.case}-after.html").write_text(brief, encoding="utf-8")
    line = {"run": f"{args.case}-after", "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "reader": "spark", "calls": after.calls - before.calls,
            "spend_usd": str(after.spend_usd - before.spend_usd), "wall_s": wall_s,
            "superseded": after.superseded,
            "findings": [[f.type.value, f.claim_id, f.observation_id] for f in after.findings]}
    with (run.reports / "runs.jsonl").open("a", encoding="utf-8") as out:
        out.write(json.dumps(line) + "\n")
    print(f"after {args.case}: {line['calls']} calls, ${Decimal(line['spend_usd']):.5f}, {wall_s} s, "
          f"superseded {after.superseded}")
    for f in after.findings:
        print(f"      {f.finding_id:7} {f.type.value:34} {f.clinician_note}")
    print(f"spend this run ${run.ledger.total_usd - start:.5f} · ledger total ${run.ledger.total_usd:.5f}")


if __name__ == "__main__":
    main()
