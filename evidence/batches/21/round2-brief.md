# Batch 21, round 2: fix the supervisor's findings

You are the builder for batch 21 of Anamnesis, round 2. Your round-1 change is in the working tree, uncommitted. An independent supervisor reviewed it, in `evidence/batches/21/supervisor.md`. Fix the items below and keep everything else as it is.

The contract `tests/contract/test_b21_media_fixes.py` has new cases at the end, under "round 2". SPEC.md changed in §2: the reworded bullet "A second hundreds group starts a new number", one sentence under Digits, one sentence in the `IngredientAmount` aliases row, and one under Prompts. Read those first.

1. **A new number takes only a final units word** (`anamnesis/providers/stated.py`, `_word_amounts`). Replace the `last_and` logic with one rule, and keep it in a small helper.
   - **When to cut:** a hundred word comes when `_since_thousand(words) >= 100`.
   - **Where to cut:**
     - If the hundred word does not carry its own `و` **and** the last word so far is a plain worth 1–9, cut before that word, so it becomes the new number's multiplier.
     - Otherwise, cut after all words so far: nothing moves.
     - `and` no longer decides anything.
   - **What it gives:** "eight hundred seventy-five one hundred twenty-five" states 875 and 125. With "and" in it, the result is the same. «خمسمية وتلات مية» states 500 and 300. «… ومية خمسة وعشرين» moves nothing and gives 125. Contract: `test_round_2_a_second_hundreds_group_states_nothing_unsaid`.
2. **One-word Arabic hundreds start a new number too.** A plain worth 100 or more (`ميتين`, `تلتمية` … `تسعمية`, from `_combined_hundreds` or the plain table) closes the earlier number when it arrives with `_since_thousand(words) >= 100`. Nothing moves.
   - «خمسمية وميتين» states 500 and 200, never 700.
   - After a thousand it stays one number: «ألف وميتين» is 1200.
3. **Tidy the same function.** Keep it under 50 lines:
   - `_since_thousand` becomes `_run_value` on the slice after the last thousand word;
   - close the earlier part with `_close`;
   - use the literal `"و"`, as `_classify` does;
   - remove `_split_hundreds` and `last_and` if nothing uses them any more.
4. **A digit run never touches a digit of another set** (`_DIGIT_RUN`). Use the lookbehind `(?<![\d.,٬])` and add `(?!\d)` after the run. `\d` only blocks matches, so nothing new parses. "１5 mg", "5５ mg" and "५5 mg" state nothing.
5. **Aliases match NFC** (`anamnesis/schema/medication.py`, `_inn_and_salt`). Use `unicodedata.normalize("NFC", name).strip().casefold()`, so a decomposed "ácido clavulánico" resolves.
6. **Nothing else changes.** The prompts already keep their advice sentences, and the contract now pins them.

Add unit tests for your helper to `tests/unit/test_b21_extra.py`.

## Rules (same as round 1)
- **Never create, modify or delete anything under `tests/contract/`.**
- Don't edit `SPEC.md`, `scripts/`, `evidence/` or `docs/`. No network, no API keys, no git commits, no new dependencies.
- Run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass, and `git status --porcelain tests/contract` prints nothing. Reply with the files you changed, one line per numbered item, the final test count, and anything in this brief you think is wrong.
