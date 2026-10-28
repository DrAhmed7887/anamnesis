# Batch 23, round 8: a longer before-form and the colloquial spoon

You are the builder for batch 23 of Anamnesis, round 8. Your round 1–7 changes are in the working tree, uncommitted. Your round 7 code matches SPEC §2 as written. The supervisor's round 7 review (`evidence/batches/23/supervisor.md`, Round 7) found one gap in the SPEC. A salt phrase of four or five words without brackets ("250 mg as amoxicillin trihydrate per 5 ml") escapes the refusal's before-form. Read SPEC §2 "A volume other than 1 ml" again; two bullets changed. The new contract is `tests/contract/test_b23_round8.py`. The round 1–7 contracts still hold.

1. **The before-form** (`_BEFORE_SLASH_RE`, `_BEFORE_WORD_RE`, or what you use):
   - **the limit:** up to five words, not three, still not counting text in brackets;
   - **sentence ends:** the words may not cross one, as the refusal's sentence end defines it (`;`, `!`, `?`, `؛`, or a `.` that ends a sentence). So "Euthyrox 50 µg tablets; crush and suspend in 10 ml of liquid" keeps its strength.
2. **The colloquial spoon:** `معلقة`, `معلقه` and `معالق` count as spoons when they stand as a whole word, with or without `ال`. The stem `معلق` alone is "suspension" and must not count.
3. **Your unit tests** (`tests/unit/test_b23_extra.py`): all 204 still pass on the CEO's reference. Add cases for both changes, including the Euthyrox line and «مسحوق لتحضير معلق» not counting as a spoon.

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
