# Batch 24, round 3: the supervisor's review of round 2

You are the builder for batch 24, round 3. Your round 1 and round 2 code is still in the working tree, uncommitted: keep it and build on it. Keep each change surgical: no refactors, and nothing outside this brief.

## Goal
Make `tests/contract/test_b24_round3.py` pass, and keep every other test green, including all of `tests/contract/test_b24_*.py`. First read the SPEC.md lines marked "round 3".

## The fixes. Each one is pinned in `test_b24_round3.py`
1. **`medio` and `media` are a half only in Spanish** (`anamnesis/providers/stated.py`). This is the safety one.
   - **The failure:** "I read about it on social media" stated 0.5, so an invented 0.5 mg intake reached `match`. "por medio de" and "medio ambiente" also stated 0.5.
   - **Give them the same kind of rule as `mil`.** They are a half only:
     - after `y`, `un`, `una` or a Spanish number word;
     - or before a Spanish unit or dose word: `comprimido(s)`, `pastilla(s)`, `cápsula(s)` (with and without the accent), `tableta(s)`, `gragea(s)`, `sobre(s)`, `miligramo(s)`, `gramo(s)`, `microgramo(s)`, `mililitro(s)`.
   - **Anywhere else they are not a number.**
   - **What must keep working:** "medio comprimido", "media pastilla", "uno y medio" and "dos y media".
2. **After `mil`, only a Spanish unit word makes it a thousand.** The Spanish unit words are `miligramo(s)`, `gramo(s)`, `microgramo(s)` and `mililitro(s)`, not `mg`, `ml` or `g`. Without this, "five mil ml" and "ten mil mg" stated 5000 and 10000.
3. **The amount-only label check** (`anamnesis/providers/claims.py`).
   - **The rule:** a word also counts as an amount word when the number reader gives it any role (a number, a multiplier, a half, a joiner, an article or a decimal word, even one that needs a neighbour), or when it is German `null`.
   - **How:** add one small public helper in `stated.py`.
   - **What it closes:** "mil miligramos", "ein Gramm", "cero coma cinco", "zero point five" and "null Komma fünf" were kept as labels; they must take the claim's name.

## Rules
- **Never create, modify or delete anything under `tests/contract/`, any `conftest.py`, `pyproject.toml` or `uv.lock`. A batch that touches them is rejected automatically.** A contract test that is skipped or xfailed fails the gate too.
- Don't edit `SPEC.md`, `scripts/`, `evidence/`, `docs/` or `finetune/`.
- Work only inside this repository. No network, no API keys, no git commits, no new dependencies.
- `uv` can't write its cache in your sandbox, so run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.
- **One test needs a local network socket that your sandbox forbids.** If it is the only failure, say so and close your goal. The gate runs outside the sandbox.
