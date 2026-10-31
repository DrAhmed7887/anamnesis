"""Batch 27, check 3: every saved live report re-parsed with the merged relation checks. Its stored claims
(the parse of their day) are rebuilt as a reply, parsed again, and any amount that changes is listed. $0,
offline.

    PYTHONPATH=. uv run python evidence/batches/27/recheck_reports.py
"""

import glob
import json

from anamnesis.providers.base import ProviderError
from anamnesis.providers.claims import parse_claims_json
from anamnesis.schema import AudioTurn


def raw_reply(report: dict) -> list[dict]:
    claims = []
    for c in report["claims"]:
        intake, strength = c["intake_amount"], c["strength"]
        claims.append({
            "name_text": c["name_text"], "inn": c["inn"],
            "strength": None if strength is None else {
                "ingredients": [{"inn": p["inn"], "amount": p["amount"], "unit": p["unit"]}
                                for p in strength["ingredients"]],
                "per": strength["per"], "release": strength["release"]},
            "intake_amount": None if intake is None else {
                "inn": intake["inn"], "amount": intake["amount"], "unit": intake["unit"]},
            "regimen": c["regimen"], "status": c["status"], "turn_ids": c["audio_evidence"]})
    return claims


def amounts(claim) -> tuple:
    intake = None if claim["intake_amount"] is None else str(claim["intake_amount"]["amount"])
    strength = (None if claim["strength"] is None
                else [str(p["amount"]) for p in claim["strength"]["ingredients"]])
    return intake, strength


def main() -> None:
    files = claims = changed = 0
    for path in sorted(set(glob.glob("evidence/**/report_*.json", recursive=True))):
        report = json.load(open(path, encoding="utf-8"))
        if not report.get("claims"):
            continue
        turns = [AudioTurn(**{k: t[k] for k in ("turn_id", "start_ms", "end_ms", "transcript")})
                 for t in report["turns"]]
        try:
            parsed = parse_claims_json(json.dumps({"claims": raw_reply(report)}), turns)
        except ProviderError as exc:
            print(f"| {path} | the whole reply is now refused: {str(exc)[:80]} |")
            changed += len(report["claims"])
            continue
        files += 1
        for before, after in zip(report["claims"], parsed, strict=True):
            claims += 1
            new = amounts(after.model_dump(mode="json"))
            if amounts(before) != new:
                changed += 1
                print(f"| {path} | {before['name_text']} | {amounts(before)} | {new} |")
    print(f"\n{files} report files, {claims} claims, {changed} changed")


if __name__ == "__main__":
    main()
