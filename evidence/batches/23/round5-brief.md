# Batch 23, round 5: keep a strength beside a dose volume only when it is printed in its own unit

You are the builder for batch 23 of Anamnesis, round 5. Your round 1–4 changes are in the working tree, uncommitted. The supervisor's round 4 review (`evidence/batches/23/supervisor.md`, Round 4) found that the clause rule's exemptions still keep the fivefold error: a water word anywhere in a clause ("Amoxicillin 250 mg/5 ml when reconstituted with water"), and a spoon with no ml number ("Each teaspoonful contains 125 mg"). So the CEO replaced the clause rule in the SPEC. Read SPEC §2 "A volume other than 1 ml" first. It was rewritten, and it holds every word list you need.

The new contract is `tests/contract/test_b23_round5.py`. The round 1–4 contracts still hold, except two keeps that now fail closed on purpose. They are marked in `test_b23_coverage.py` and `test_b23_round4.py`.

1. **Replace the clause code** in `anamnesis/providers/spark.py` with the round 5 rule. Remove `_CLAUSE_SPLIT_RE`, `_WATER_NOT_RES`, `_is_water_clause`, `_clause_has_volume` and `_clause_has_amount_with_unit`. Keep the digit translation. Then:
   - **Find each volume and each spoon** in the whole text; there are no clauses any more. `measure` counts only after `per`, `each`, `every`, `a`, `one` or `1`.
   - **Decide whether each one counts.**
     - It always counts when it comes right after an amount through `/`, `∕`, `／`, `per`, `por`, `par` or `لكل` (an optional `(` between).
     - Otherwise, for a reading per `tablet`, `capsule` or `dose` only, it doesn't count when it is water to dissolve in. That means it is followed by a water word, with only the SPEC's short list of words between and text in brackets skipped. Or it sits inside brackets that open right after a water word.
     - For a reading per `ml`, water never stops it counting.
   - **When any one counts, the strength becomes null, unless both of these hold:**
     - each ingredient's amount is printed in the reading's own unit: per 1 ml, per dose, or a tablet or capsule word at most three words after the amount and its unit;
     - no amount of the reading is also printed beside any volume or spoon, either right before it through a connector (`in` and `في` included), or later in its sentence.
   - **Two places treat a line break differently, on purpose:**
     - the tablet print may not cross a line break, a `.`, `;`, `!`, `?` or `؛`;
     - the "later in its sentence" check ends only at a `.` (not between two digits), `;`, `!`, `?` or `؛`. A line break doesn't end it, so "Per 5 ml\nParacetamol 250 mg\n250 mg/ml drops" still drops.
   - **The units now include** `UI`, `U`, `unidades`, `unités` and `وحدة دولية`. The water and tablet words take `ال` and the Arabic suffixes. See SPEC for the full lists.
   - Keep the rule in a few small helpers, keep `_per_other_volume(label_text, strength)` as the entry point, and change nothing else.
2. **Rewrite your unit tests** (`tests/unit/test_b23_extra.py`). These 9 cases pin round 3–4 behaviour that round 5 changes on purpose:
   - "Tablets 500 mg, bottle 100 ml" (the tablet word comes before the amount);
   - the six "Syrup 250 mg in 5 ml of water" lines read per ml (water never exempts a reading per ml);
   - "5 ml syrup\n500 mg capsules" (the amount is later in the volume's sentence);
   - "500 mg capsules in 5 ml syrup" (now kept: the capsule print is right after the amount).

   Rewrite them to the new rule, and add cases for it: spoons, the refusal both ways, the water lead-in words, brackets, and the line-break difference above.

## Rules
- **Never create, modify or delete anything under `tests/contract/`, any `conftest.py`, `pyproject.toml` or `uv.lock`. A batch that touches them is rejected automatically.** A contract test that is skipped or xfailed fails the gate too.
- Don't edit `SPEC.md`, `scripts/`, `evidence/` or `docs/`. Work only inside this repository. No network, no API keys, no git commits, no new dependencies.
- `uv` can't write its cache in your sandbox, so run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass from the repo root, and `git status --porcelain tests/contract` prints nothing.

Reply with a short report:
- the files you changed;
- what you did for each numbered item;
- the final test count;
- anything in this brief you think is wrong.
