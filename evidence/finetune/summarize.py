# ruff: noqa: E501
"""The comparison's tables, from the committed replies, by finetune/score.py's own score(). From the repo root:

    PYTHONPATH=. .venv/bin/python evidence/finetune/summarize.py [--run r1]

Writes each system's miss list to runs/<system dir>/<split>.score.txt and prints the tables in Markdown. For
Glimmer it also counts the replies that never opened an answer and the answers that stopped at the token limit,
read from the eval's own fields (first_finish, answer_finish).
"""

import argparse
import json
from pathlib import Path

from finetune.common import DATA_DIR, read_jsonl
from finetune.glimmer import TEST_SPLITS
from finetune.score import FIELDS, load_predictions, render, score

RUNS = Path(__file__).resolve().parent / "runs"


def systems(run: str) -> dict[str, Path]:
    return {"Spark 1.3": RUNS / "spark", "Glimmer base": RUNS / run / "glimmer-base",
            "Glimmer + LoRA": RUNS / run / "glimmer-lora"}


def glimmer_counts(path: Path) -> dict[str, int]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {"no_answer": sum(not row.get("opened_answer", True) for row in rows),
            "hit_limit": sum(row.get("answer_finish") == "length" for row in rows)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="r1")
    args = parser.parse_args()
    head = ("| System | Split | n | Valid JSON | Dropped by checks | Invalid JSON | No reply | Fully right "
            "| Missing / extra | Harmful before / after |")
    print(head)
    print("|" + "---|" * (head.count("|") - 1))
    fields: dict[str, dict[str, list[int]]] = {}
    extra: dict[str, dict[str, int]] = {}
    for system, folder in systems(args.run).items():
        totals = dict.fromkeys(("n", "valid", "dropped", "invalid", "none", "right", "missing", "extra", "hb", "ha"), 0)
        claims = 0
        fields[system] = {field: [0, 0] for field in FIELDS}
        for split in TEST_SPLITS:
            answers = read_jsonl(DATA_DIR / f"{split}.answers.jsonl")
            path = folder / f"{split}.jsonl"
            report = score(answers, load_predictions(path, len(answers)))
            (folder / f"{split}.score.txt").write_text(render(split, report) + "\n", encoding="utf-8")
            outcomes = report["outcomes"]
            row = {"n": report["examples"], "valid": outcomes["parsed"] + outcomes["dropped"],
                   "dropped": outcomes["dropped"], "invalid": outcomes["invalid_json"], "none": outcomes["no_reply"],
                   "right": report["all_correct"], "missing": report["missing"], "extra": report["extra"],
                   "hb": report["harm"]["before"]["claims"], "ha": report["harm"]["after"]["claims"]}
            totals = {key: totals[key] + row[key] for key in totals}
            claims += report["claims"]
            for field in FIELDS:
                fields[system][field][0] += report["fields"][field]
                fields[system][field][1] += report["claims"]
            if system != "Spark 1.3":
                counts = glimmer_counts(path)
                extra[system] = {key: extra.get(system, {}).get(key, 0) + value for key, value in counts.items()}
            print(f"| {system} | {split} | {row['n']} | {row['valid']} | {row['dropped']} | {row['invalid']} | "
                  f"{row['none']} | {row['right']} | {row['missing']} / {row['extra']} | {row['hb']} / {row['ha']} |")
        print(f"| **{system}** | **all** | **{totals['n']}** | **{totals['valid']}** | **{totals['dropped']}** | "
              f"**{totals['invalid']}** | **{totals['none']}** | **{totals['right']}** | **{totals['missing']} / "
              f"{totals['extra']}** | **{totals['hb']} / {totals['ha']}** |")
    print()
    print("| System | " + " | ".join(FIELDS) + " |")
    print("|---|" + "---|" * len(FIELDS))
    for system, by_field in fields.items():
        print(f"| {system} | " + " | ".join(f"{right}/{total}" for right, total in by_field.values()) + " |")
    print()
    for system, counts in extra.items():
        print(f"{system}: never opened an answer {counts['no_answer']}, answer stopped at the token limit "
              f"{counts['hit_limit']}")


if __name__ == "__main__":
    main()
