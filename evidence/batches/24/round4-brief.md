# Batch 24, round 4: the supervisor's review of round 3

You are the builder for batch 24, round 4. Your round 1–3 code is still in the working tree, uncommitted: keep it and build on it. Keep each change surgical: no refactors, and nothing outside this brief.

## Goal
Make `tests/contract/test_b24_round4.py` pass, and keep every other test green, including all of `tests/contract/test_b24_*.py`. First read the SPEC.md lines marked "round 4".

## The fixes. Each one is pinned in `test_b24_round4.py`
**Every one of these idioms stated a number nobody said, and an invented amount of that number reached a false `match`.**

1. **A Spanish or German half ends its run** (`anamnesis/providers/stated.py`).
   - **The failure:** "um halb zwei" (1:30) stated 2.5; "halb zwölf" 12.5; "eine halbe Zehn-Milligramm-Tablette" 10.5; "uno y medio diez miligramos" 11.5.
   - **The rule:** after a Spanish or German half word joins a run, the run closes.
   - **What must keep working:** "uno y medio" 1.5, "dos y media" 2.5, "eine halbe Tablette" 0.5, and the one-word "zweieinhalb" 2.5.
2. **`por ciento` and `por cien` are a percent.** `cien` and `ciento` right after `por` state nothing, so "un veinte por ciento" states 20, never 100.
3. **Tighter contexts for `medio` and `media`.** They are a half only:
   - after a Spanish number word followed by `y`, but not when `la` or `las` comes before that number (a clock time: "a las dos y media" is 2:30, never 2.5);
   - after a Spanish number word;
   - or before a Spanish unit or dose word.
   - **What changes:** `un` and `una` no longer count as contexts, and `sobre` and `sobres` leave the dose words.
   - **The phrases this closes:** "en un medio sobre salud", "una media de dos al día", "es un medio para dormir", "trabajo y medio ambiente" and "un nivel medio sobre el tema".
4. **A field word under 3 letters is grounded only as a whole word of the turn, never as a prefix** (`anamnesis/providers/claims.py`). "vitamin d" is not grounded by "de".

## Rules
- **Never create, modify or delete anything under `tests/contract/`, any `conftest.py`, `pyproject.toml` or `uv.lock`. A batch that touches them is rejected automatically.** A contract test that is skipped or xfailed fails the gate too.
- Don't edit `SPEC.md`, `scripts/`, `evidence/`, `docs/` or `finetune/`.
- Work only inside this repository. No network, no API keys, no git commits, no new dependencies.
- `uv` can't write its cache in your sandbox, so run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.
- **One test needs a local network socket that your sandbox forbids.** If it is the only failure, say so and close your goal. The gate runs outside the sandbox.
