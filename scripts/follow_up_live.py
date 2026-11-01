"""Live follow-up: one intake, then Anamnesis asks the patient for every missing photo by itself.

SPEC §8, "The follow-up by itself" (batch 31).

    PYTHONPATH=. uv run python scripts/follow_up_live.py --case U11 --voice v.wav --photo first.jpg \
        --reply second.jpg [--lang en] [--cap 5.00] [--session-usd 0.25] [--max-rounds 2]

The first photo goes through the intake exactly as in scripts/intake_live.py, saved as <case>-fu-before.
Then `follow_up` runs. There is no patient app: the staged patient is this script, which answers the first
request with the --reply photo and sends nothing for any later one. The approved brief is made offline with
`approve` (no model call), and only when no request is left open.
Output, in evidence/live/<date>/: report_<case>-fu-before.json, report_<case>-fu-after.json,
followup_<case>.json (each request, the message the patient got, the log and the review) and a runs.jsonl
line. The briefs go to evidence/raw/briefs/<date>/ (git-ignored: they embed the photos and the voice note).
"""

import argparse
import json
import os
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
from anamnesis.review import approve, follow_up, new_review, requestable
from anamnesis.schema.review import ReviewStatus


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--voice", required=True, help="the case's voice note (16 kHz mono WAV)")
    parser.add_argument("--photo", required=True, help="the first photo, sent with the voice note")
    parser.add_argument("--reply", required=True,
                        help="the photo the staged patient sends for the first request")
    parser.add_argument("--lang", choices=sorted(il.LANGUAGES), default="en")
    parser.add_argument("--cap", default="5.00", help="total USD cap across all live runs (ledger)")
    parser.add_argument("--session-usd", default="0.25", help="USD cap for the follow-up")
    parser.add_argument("--max-rounds", type=int, default=2)
    args = parser.parse_args()
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    run = il.Run(SpendGuard(il.LEDGER, cap_usd=Decimal(args.cap)),
                 MetaClient(api_key=os.environ.get("MODEL_API_KEY") or il.keychain("META_API_KEY")),
                 load_catalogue(), Decimal(args.session_usd), 3,
                 il.ROOT / "evidence/live" / day, il.ROOT / "evidence/raw/briefs" / day)
    run.reports.mkdir(parents=True, exist_ok=True)
    run.briefs.mkdir(parents=True, exist_ok=True)
    audio, images, answer = il.voice(Path(args.voice)), [il.photo(args.photo)], il.photo(args.reply)
    media = (audio, "audio/wav")
    start = run.ledger.total_usd

    before = il.intake(run, f"{args.case}-fu-before", audio, images, args.lang)
    print(f"requestable after the intake: {requestable(before)}")
    (run.briefs / f"{args.case}-fu-before.html").write_text(
        render_brief(before, images, media, run.catalogue, new_review(before)), encoding="utf-8")

    asked, replies = [], [answer]

    def reply(request, message):
        """The staged patient: the --reply photo for the first request, nothing after it."""
        given = replies.pop(0) if replies else None
        asked.append({"request_id": request.request_id, "kind": request.kind.value,
                      "target_id": request.target_id, "message": message, "replied": given is not None})
        print(f"asked {request.request_id} ({request.kind.value} {request.target_id}): {message}")
        return given

    budget = len(SAM_CONCEPTS) + 2 * run.top_k  # add_photo's own default (SPEC §8)
    guard = SessionGuard(run.ledger, max_usd=run.session_usd, max_calls=2 * budget)
    clock = time.monotonic()
    after, review, given, log = follow_up(
        before, new_review(before), images, media, reply=reply, segmenter=MetaSegmenter(run.client, guard),
        reader=MetaLabelReader(run.client, guard), catalogue=run.catalogue, top_k=run.top_k,
        max_rounds=args.max_rounds)
    wall_s = round(time.monotonic() - clock, 1)

    (run.reports / f"report_{args.case}-fu-after.json").write_text(
        after.model_dump_json(indent=2) + "\n", "utf-8")
    record = {"asked": asked, "log": [json.loads(step.model_dump_json()) for step in log],
              "review": json.loads(review.model_dump_json())}
    (run.reports / f"followup_{args.case}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run.briefs / f"{args.case}-fu-after.html").write_text(
        render_brief(after, given, media, run.catalogue, review, follow_up=log), encoding="utf-8")
    if review.status is ReviewStatus.DRAFT:
        approved = approve(review, after)  # the clinician's sign-off, rendered offline: no model call
        (run.briefs / f"{args.case}-fu-approved.html").write_text(
            render_brief(after, given, media, run.catalogue, approved, follow_up=log), encoding="utf-8")

    line = {"run": f"{args.case}-fu-after", "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "reader": "spark", "calls": after.calls - before.calls,
            "spend_usd": str(after.spend_usd - before.spend_usd), "wall_s": wall_s,
            "log": [[s.round, s.request_id, s.target_id, s.outcome.value] for s in log],
            "review": review.status.value, "superseded": after.superseded,
            "findings": [[f.type.value, f.claim_id, f.observation_id] for f in after.findings]}
    with (run.reports / "runs.jsonl").open("a", encoding="utf-8") as out:
        out.write(json.dumps(line) + "\n")
    print(f"follow-up {args.case}: {len(log)} asked, {line['calls']} calls, "
          f"${Decimal(line['spend_usd']):.5f}, {wall_s} s, review {review.status.value}")
    for f in after.findings:
        print(f"      {f.finding_id:7} {f.type.value:34} {f.clinician_note}")
    print(f"spend this run ${run.ledger.total_usd - start:.5f} · ledger total ${run.ledger.total_usd:.5f}")


if __name__ == "__main__":
    main()
