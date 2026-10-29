# ruff: noqa: E501
"""Harmful claims after the checks, counted on the product's parsed claims instead of the raw reply (29 Oct).

    PYTHONPATH=. .venv/bin/python evidence/batches/24/harm_parsed.py evidence/finetune/runs

The parser is whichever anamnesis/ is first on the path. A parsed INN string counts as harmful when it doesn't occur in
the transcript; an alias stored under its canonical name ("acetaminophen" said, "paracetamol" stored) shows up too.
"""
import json
import sys
from pathlib import Path

from anamnesis.core.catalogue import normalise
from anamnesis.providers.base import ProviderError
from anamnesis.providers.claims import parse_claims_json
from finetune.common import read_jsonl, turns_from_records
from finetune.score import score_example

RUNS = Path(sys.argv[1])
DATA, DATA_V2 = Path("finetune/data"), Path("finetune/data_v2")
SPLITS = ("test_iid", "test_shift", "test_codeswitch", "test_real")
SETS = [("Spark 1.3", RUNS / "spark", DATA, SPLITS), ("Glimmer base", RUNS / "r1/glimmer-base", DATA, SPLITS),
        ("Glimmer + LoRA r1", RUNS / "r1/glimmer-lora", DATA, SPLITS),
        ("Spark 1.3", RUNS / "spark", DATA_V2, ("test_spain",)),
        ("Glimmer base", RUNS / "r2/glimmer-base", DATA_V2, ("test_spain",)),
        ("Glimmer + LoRA r2", RUNS / "r2/glimmer-lora-r2", DATA_V2, ("test_spain",))]
for system, folder, data, splits in SETS:
    raw_after = parsed_after = 0
    kinds: dict[str, int] = {}
    for split in splits:
        answers = read_jsonl(data / f"{split}.answers.jsonl")
        replies = {json.loads(line)["index"]: json.loads(line)["reply"] for line in (folder / f"{split}.jsonl").read_text().splitlines()}
        for index, answer in enumerate(answers):
            raw_after += len(score_example(answer, replies.get(index))["harm_after"])
            turns = turns_from_records(answer["turns"])
            texts = [normalise(t.transcript) for t in turns]
            try:
                claims = parse_claims_json(replies.get(index) or "", turns)
            except (ProviderError, TypeError):
                continue
            for claim in claims:
                inns = [claim.inn] + ([claim.intake_amount.inn] if claim.intake_amount else []) + (
                    [p.inn for p in claim.strength.ingredients] if claim.strength else [])
                bad = [i for i in inns if isinstance(i, str) and normalise(i) and not any(normalise(i) in t for t in texts)]
                if bad:
                    parsed_after += 1
                    for i in bad:
                        kinds[i] = kinds.get(i, 0) + 1
    top = sorted(kinds.items(), key=lambda kv: -kv[1])[:6]
    print(f"{system:18} {'+'.join(splits)[:30]:30} raw-string metric {raw_after:3}  on parsed claims {parsed_after:3}  {top}")
