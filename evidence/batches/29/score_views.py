"""Batch 29's re-measure, scored two ways, both defined in `remeasure-plan.md` before any call (31 Oct):

- **as pre-registered:** `finetune/score.py` unchanged;
- **the second view:** test_real's three U2 notes key the strength amoxicillin 875 mg + clavulanic acid 125 mg
  (batch 29 makes it representable), and a kept ingredient name that the claim's brand contains, by the
  catalogue, isn't counted as harm (the product's own grounding rule, SPEC §2 batch 24). Applied to every
  system alike.

    PYTHONPATH=. uv run python evidence/batches/29/score_views.py
"""

import copy
from pathlib import Path

import finetune.score as fs
from anamnesis.core.catalogue import load_catalogue
from anamnesis.schema import canonical_inn
from finetune.common import DATA_DIR, read_jsonl
from finetune.glimmer import TEST_SPLITS

RUNS = Path("evidence/finetune/runs")
V2 = DATA_DIR.parent / "data_v2"
CAT = load_catalogue()
SYSTEMS = [("Spark 1.3, 29 Oct prompt", RUNS / "spark"),
           ("Spark 1.3, batch 29 prompt", RUNS / "spark-b29"),
           ("Glimmer + LoRA r1", RUNS / "r1/glimmer-lora"),
           ("Glimmer + LoRA r2", RUNS / "r2/glimmer-lora-r2"),
           ("Glimmer base", RUNS / "r1/glimmer-base")]
SPAIN = {"Spark 1.3, 29 Oct prompt": RUNS / "spark", "Spark 1.3, batch 29 prompt": RUNS / "spark-b29",
         "Glimmer + LoRA r1": RUNS / "r2/glimmer-lora-r1", "Glimmer + LoRA r2": RUNS / "r2/glimmer-lora-r2",
         "Glimmer base": RUNS / "r2/glimmer-base"}
U2_STRENGTH = {"ingredients": [{"inn": "amoxicillin", "salt": None, "amount": "875", "unit": "mg"},
                               {"inn": "clavulanic acid", "salt": None, "amount": "125", "unit": "mg"}],
               "per": "tablet", "release": "unknown"}
_original_unsupported = fs._unsupported


def _brand_aware_unsupported(raw: dict, turns: list, keep: tuple[bool, bool] | None) -> list[str]:
    found = _original_unsupported(raw, turns, keep)
    entry = CAT.resolve(raw["name_text"]) if isinstance(raw.get("name_text"), str) else None
    own = set(entry.inns) if entry else set()
    return [item for item in found
            if not (item.startswith("INN ") and canonical_inn(item.split("'")[1]) in own)]


def rekey(answers: list[dict]) -> list[dict]:
    out = copy.deepcopy(answers)
    for answer in out:
        if any("Augmentin" in turn["transcript"] and "875" in turn["transcript"] for turn in answer["turns"]):
            for claim in answer["claims"]:
                if claim["name_text"] == "Augmentin" and claim["strength"] is None:
                    claim["strength"] = copy.deepcopy(U2_STRENGTH)
    return out


def tally(folder: Path, data: Path, split: str, view: int) -> tuple[int, int, int] | None:
    path = folder / f"{split}.jsonl"
    if not path.exists():
        return None
    answers = read_jsonl(data / f"{split}.answers.jsonl")
    if view == 2 and split == "test_real":
        answers = rekey(answers)
    fs._unsupported = _brand_aware_unsupported if view == 2 else _original_unsupported
    replies = fs.load_predictions(path, len(answers))
    right = harm = 0
    for index, answer in enumerate(answers):
        result = fs.score_example(answer, replies.get(index))
        right += not result["problems"]
        harm += len(result["harm_after"])
    fs._unsupported = _original_unsupported
    return right, harm, len(answers)


def main() -> None:
    for view in (1, 2):
        print(f"### {'As pre-registered' if view == 1 else 'The second view'}\n")
        print("| System | " + " | ".join(TEST_SPLITS) + " | all four | test_spain |")
        print("|---|" + "---|" * (len(TEST_SPLITS) + 2))
        for name, folder in SYSTEMS:
            cells, total, harm_total, n_total, complete = [], 0, 0, 0, True
            for split in TEST_SPLITS:
                got = tally(folder, DATA_DIR, split, view)
                if got is None:
                    cells.append("not run")
                    complete = False
                    continue
                right, harm, n = got
                total, harm_total, n_total = total + right, harm_total + harm, n_total + n
                cells.append(f"{right}/{n} ({harm} harmful)")
            spain = tally(SPAIN[name], V2, "test_spain", view)
            spain_cell = "not run" if spain is None else f"{spain[0]}/{spain[2]} ({spain[1]} harmful)"
            all_cell = f"**{total}/{n_total}** ({harm_total} harmful)" if complete else "incomplete"
            print(f"| {name} | " + " | ".join(cells) + f" | {all_cell} | {spain_cell} |")
        print()


if __name__ == "__main__":
    main()
