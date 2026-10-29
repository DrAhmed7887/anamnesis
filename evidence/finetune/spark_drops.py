# ruff: noqa: E501
"""Post-hoc diagnostic, not pre-registered (29 Oct): how many of Spark 1.3's misses on the fine-tune's test splits
are amounts Spark did send that the product's parser then dropped. From the repo root:

    PYTHONPATH=. .venv/bin/python evidence/finetune/spark_drops.py

parse_claims_json drops both of a claim's amounts when one of them is dropped (SPEC §2). Some shapes of Spark's
reply set that rule off with no unverified amount in them. Each reply is scored as sent, then again with only
these shapes rewritten, by the same finetune/score.py:
- "labels": an empty strength object ({"ingredients": [], ...}) becomes null, and an intake whose ingredient label
  is empty, or is neither the claim's name or INN nor in the turns it cites, gets the claim's name_text as label;
- "labels+ranges": the same, and a units_per_intake that isn't one plain number ("1-2") becomes null too.
"""

import json
import re
from pathlib import Path

from anamnesis.core.catalogue import normalise
from finetune.common import DATA_DIR, read_jsonl
from finetune.score import FIELDS, score_example

RUNS = Path(__file__).resolve().parent / "runs" / "spark"
SPLITS = ("test_iid", "test_shift", "test_codeswitch", "test_real")
PLAIN_COUNT = re.compile(r"^\s*\d+(\.\d+)?\s*$")
VARIANTS = ("labels", "labels+ranges")


def grounded(label: str, claim: dict, turns: dict[str, str]) -> bool:
    cited = " ".join(turns[turn_id] for turn_id in claim["turn_ids"] if turn_id in turns)
    names = {normalise(claim["name_text"]), normalise(claim.get("inn") or "")}
    return bool(label.strip()) and (normalise(label) in names or normalise(label) in normalise(cited))


def rewrite(reply: str, turns: dict[str, str], ranges: bool) -> tuple[str, dict[str, int]]:
    """The reply with only those shapes rewritten, and how many of each it had."""
    found = {"empty_strength": 0, "empty_label": 0, "ungrounded_label": 0, "units_range": 0}
    data = json.loads(reply)
    for claim in data["claims"]:
        strength, intake, regimen = claim.get("strength"), claim.get("intake_amount"), claim.get("regimen")
        if isinstance(strength, dict) and strength.get("ingredients") == []:
            claim["strength"] = None
            found["empty_strength"] += 1
        if isinstance(intake, dict) and not grounded(intake.get("inn") or "", claim, turns):
            found["empty_label" if not (intake.get("inn") or "").strip() else "ungrounded_label"] += 1
            intake["inn"] = claim["name_text"]
        if ranges and isinstance(regimen, dict) and isinstance(regimen.get("units_per_intake"), str) \
                and not PLAIN_COUNT.match(regimen["units_per_intake"]):
            regimen["units_per_intake"] = None
            found["units_range"] += 1
    return json.dumps(data, ensure_ascii=False), found


def fully_right(result: dict) -> bool:
    return result["outcome"] == "parsed" and not result["problems"]


def main() -> None:
    for variant in VARIANTS:
        tally = {"examples": 0, "all_correct_as_sent": 0, "all_correct_rewritten": 0, "harmful_after_as_sent": 0,
                 "harmful_after_rewritten": 0, "gained": {}, "lost": {}, "shapes": {}, "lost_at": []}
        for split in SPLITS:
            answers = read_jsonl(DATA_DIR / f"{split}.answers.jsonl")
            rows = [json.loads(line) for line in (RUNS / f"{split}.jsonl").read_text(encoding="utf-8").splitlines()]
            replies = {row["index"]: row["reply"] for row in rows}
            for answer in answers:
                turns = {turn["turn_id"]: turn["transcript"] for turn in answer["turns"]}
                fixed, found = rewrite(replies[answer["index"]], turns, ranges=variant == "labels+ranges")
                for shape, count in found.items():
                    tally["shapes"][shape] = tally["shapes"].get(shape, 0) + count
                before, after = score_example(answer, replies[answer["index"]]), score_example(answer, fixed)
                tally["examples"] += 1
                tally["all_correct_as_sent"] += fully_right(before)
                tally["all_correct_rewritten"] += fully_right(after)
                tally["harmful_after_as_sent"] += len(before["harm_after"])
                tally["harmful_after_rewritten"] += len(after["harm_after"])
                for field in FIELDS:
                    change = after["correct"][field] - before["correct"][field]
                    if change:
                        side = "gained" if change > 0 else "lost"
                        tally[side][field] = tally[side].get(field, 0) + abs(change)
                        if change < 0:
                            tally["lost_at"].append(f"{split}#{answer['index']} {field}")
        print(variant, json.dumps(tally, ensure_ascii=False))


if __name__ == "__main__":
    main()
