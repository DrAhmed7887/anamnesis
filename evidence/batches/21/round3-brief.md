# Batch 21, round 3: fix the supervisor's round 2 findings

You are the builder for batch 21 of Anamnesis, round 3. Your round 1 and round 2 changes are in the working tree, uncommitted. Read the "Round 2" section of `evidence/batches/21/supervisor.md`. The contract `tests/contract/test_b21_media_fixes.py` has new cases at the end, under "round 3". SPEC §2 has new lines: "Thousands and the filler "a"" under the new-number bullet, and "matched as a whole" under Digits.

1. **«ألفين» closes the thousands part** (`anamnesis/providers/stated.py`). The change goes in two places, and both are needed:
   - in `_run_value`, a plain worth 1000 or more is added to the thousands total, and `current` resets, as a thousand word does;
   - in `_since_thousand`, start after the last thousand word **or** the last plain worth 1000 or more.

   Results: «ألفين وخمسمية» is 2500, «ألفين و ميتين» is 2200, «ألفين ومية» is 2100 (not 200000), and «ألفين وخمسمية وخمسين» is 2550, never 550.
2. **After the filler "a", nothing moves** (`_word_amounts`). When the token before the hundred word is the filler `a`, cut after all words so far. "eight hundred seventy-five and a hundred twenty-five" then states 875 and 125, never 870 or 525.
3. **A digit run is atomic** (`_DIGIT_RUN`): `(?<![\d.,٬])(?>[0-9٠-٩۰-۹]+(?:[.,٬][0-9٠-٩۰-۹]+)?)(?!\d)`. The project runs Python 3.12, so the atomic group is available. "1.5５ mg", "2,5５ mg" and "٢٫٥५" state nothing. "I take 5." still states 5.
4. **Tests:** add to `tests/unit/test_b21_extra.py` cases for «ألفين» and for "and a hundred". Rename any `_` loop variable whose value is now read.

Nothing else changes.

## Rules (same as before)
- **Never create, modify or delete anything under `tests/contract/`.**
- Don't edit `SPEC.md`, `scripts/`, `evidence/` or `docs/`. No network, no API keys, no git commits, no new dependencies.
- Run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass, and `git status --porcelain tests/contract` prints nothing. Reply with the files you changed, one line per numbered item, the final test count, and anything in this brief you think is wrong.
