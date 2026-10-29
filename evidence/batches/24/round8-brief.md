# Batch 24, round 8: Spanish clock times, and no join across languages

You are the builder for batch 24, round 8. Your round 1–7 code is still in the working tree, uncommitted: keep it and build on it. Keep each change surgical: no refactors, and nothing outside this brief.

## Goal
Make `tests/contract/test_b24_round8.py` pass, and keep every other test green, including all of `tests/contract/test_b24_*.py`. First read the SPEC.md lines marked "round 8".

## The fixes (`anamnesis/providers/stated.py`). Each one is pinned in `test_b24_round8.py`
1. **A Spanish clock time states no amount.**
   - **The hour:** a number right after `la` or `las` is an hour and states nothing. It can be a Spanish or English number word, `una`, or digits.
   - **The minutes:** a Spanish number after the hour and `y`, or a Spanish number from 10 to 59 right after the hour, states nothing either.
   - **Before an amount:** neither applies when the very next token is a unit or dose word. "tomo las dos pastillas" (the two pills) still states 2, and "a las ocho veinte miligramos" 20.
   - **The failure:** "a las cinco mil miligramos" stated 5 and 5000, and "a las ocho y cuarenta y dos pastillas" stated 40 and 42. Concor 5 mg and Lipitor 40 mg reached `match`.
   - **No German clock rule:** German numbers already never combine, and a number after `um` states only before a unit or dose word.
2. **An English or Arabic hundred, thousand, half or point closes an open Spanish or German run first.** The closed run then follows round 7's rule.
   - **The failure:** "sechs hundred Milligramm" stated 600, and Ibuprofen 600 mg reached `match`. "zwei thousand Milligramm" stated 2000 and "cinco and a half mg" 5.5.
   - **A decimal begun in Spanish or German with an English point states nothing at all:** "siete point five milligrams" and "dos point cinco miligramos" state nothing.
3. **`y` joins a ten only to a Spanish number or an article after it:** "treinta y five mg" states 5, never 35.
4. **`coma` and `komma` are a decimal point only after a Spanish or German number word.** "GCS eight coma three" states 8 and 3, as English did before batch 24.
5. **German `null` right before `komma` is 0,** and it makes its run German: "null Komma fünf Milligramm" is 0.5.
6. **Remove any helper your changes leave unused,** such as `_close` if nothing calls it.

**What must keep working:** English and Arabic read exactly as before batch 24. Round 6's amount rule, round 7's closes, and every earlier round still hold.

## Rules
- **Never create, modify or delete anything under `tests/contract/`, any `conftest.py`, `pyproject.toml` or `uv.lock`. A batch that touches them is rejected automatically.** A contract test that is skipped or xfailed fails the gate too.
- Don't edit `SPEC.md`, `scripts/`, `evidence/`, `docs/` or `finetune/`.
- Work only inside this repository. No network, no API keys, no git commits, no new dependencies.
- `uv` can't write its cache in your sandbox, so run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.
- **One test needs a local network socket that your sandbox forbids.** If it is the only failure, say so and close your goal. The gate runs outside the sandbox.
