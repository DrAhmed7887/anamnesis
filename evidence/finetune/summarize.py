# ruff: noqa: E501
"""The comparison's tables, from the committed replies, by finetune/score.py's own score(). From the repo root:

    PYTHONPATH=. .venv/bin/python evidence/finetune/summarize.py [--table r1|r2]

r1 (the default): Spark 1.3, base Glimmer and r1 on the four test splits. r2 (plan.md, amended 29 Oct (2)):
Spark 1.3, base Glimmer, r1 and r2 on test_spain, then r1 and r2 on the four test splits.
Writes each system's miss list to its folder as <split>.score.txt and prints the tables in Markdown. For
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
DATA_V2 = DATA_DIR.parent / "data_v2"


def glimmer_counts(path: Path) -> dict[str, int]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {"no_answer": sum(not row.get("opened_answer", True) for row in rows),
            "hit_limit": sum(row.get("answer_finish") == "length" for row in rows)}


def table(entries: list[tuple[str, Path, Path, tuple[str, ...]]]) -> None:
    """One table row per system and split, a total per system, then field accuracy: entries are
    (system, folder of replies, folder of the split's answers, splits)."""
    head = ("| System | Split | n | Valid JSON | Dropped by checks | Invalid JSON | No reply | Fully right "
            "| Missing / extra | Harmful before / after |")
    print(head)
    print("|" + "---|" * (head.count("|") - 1))
    fields: dict[str, dict[str, list[int]]] = {}
    extra: dict[str, dict[str, int]] = {}
    for system, folder, data, splits in entries:
        totals = dict.fromkeys(("n", "valid", "dropped", "invalid", "none", "right", "missing", "extra", "hb", "ha"), 0)
        fields[system] = {field: [0, 0] for field in FIELDS}
        for split in splits:
            answers = read_jsonl(data / f"{split}.answers.jsonl")
            path = folder / f"{split}.jsonl"
            report = score(answers, load_predictions(path, len(answers)))
            (folder / f"{split}.score.txt").write_text(render(split, report) + "\n", encoding="utf-8")
            outcomes = report["outcomes"]
            row = {"n": report["examples"], "valid": outcomes["parsed"] + outcomes["dropped"],
                   "dropped": outcomes["dropped"], "invalid": outcomes["invalid_json"], "none": outcomes["no_reply"],
                   "right": report["all_correct"], "missing": report["missing"], "extra": report["extra"],
                   "hb": report["harm"]["before"]["claims"], "ha": report["harm"]["after"]["claims"]}
            totals = {key: totals[key] + row[key] for key in totals}
            for field in FIELDS:
                fields[system][field][0] += report["fields"][field]
                fields[system][field][1] += report["claims"]
            if system != "Spark 1.3":
                counts = glimmer_counts(path)
                extra[system] = {key: extra.get(system, {}).get(key, 0) + value for key, value in counts.items()}
            print(f"| {system} | {split} | {row['n']} | {row['valid']} | {row['dropped']} | {row['invalid']} | "
                  f"{row['none']} | {row['right']} | {row['missing']} / {row['extra']} | {row['hb']} / {row['ha']} |")
        if len(splits) > 1:
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", choices=("r1", "r2"), default="r1")
    args = parser.parse_args()
    if args.table == "r1":
        table([("Spark 1.3", RUNS / "spark", DATA_DIR, TEST_SPLITS),
               ("Glimmer base", RUNS / "r1" / "glimmer-base", DATA_DIR, TEST_SPLITS),
               ("Glimmer + LoRA", RUNS / "r1" / "glimmer-lora", DATA_DIR, TEST_SPLITS)])
        return
    spain = ("test_spain",)
    print("### test_spain: 19 Spanish brands neither run trained on\n")
    table([("Spark 1.3", RUNS / "spark", DATA_V2, spain),
           ("Glimmer base", RUNS / "r2" / "glimmer-base", DATA_V2, spain),
           ("Glimmer + LoRA r1", RUNS / "r2" / "glimmer-lora-r1", DATA_V2, spain),
           ("Glimmer + LoRA r2", RUNS / "r2" / "glimmer-lora-r2", DATA_V2, spain)])
    print("\n### r1's four test splits: r1 as scored on 29 Oct (f07e273), and r2\n")
    table([("Glimmer + LoRA r1", RUNS / "r1" / "glimmer-lora", DATA_DIR, TEST_SPLITS),
           ("Glimmer + LoRA r2", RUNS / "r2" / "glimmer-lora-r2", DATA_DIR, TEST_SPLITS)])


if __name__ == "__main__":
    main()
