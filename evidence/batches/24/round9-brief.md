# Batch 24, round 9: no mixed runs, and `la` is an hour only in `la una`

You are the builder for batch 24, round 9. Your round 1–8 code is still in the working tree, uncommitted: keep it and build on it. Keep each change surgical: no refactors, and nothing outside this brief.

## Goal
Make `tests/contract/test_b24_round9.py` pass, and keep every other test green, including all of `tests/contract/test_b24_*.py`. First read the SPEC.md lines marked "round 9", and the round 8 lines it amends.

## The fixes (`anamnesis/providers/stated.py`). Each one is pinned in `test_b24_round9.py`
1. **A run never mixes languages.** There are two groups: English and Arabic, and Spanish and German. A number word of the other group closes the open run first, then starts its own run.
   - **What counts:** plain numbers as well as the multipliers, halves and points of round 8.
   - **Both directions:** a Spanish or German run followed by an English number, and an English run followed by a Spanish number.
   - **The failure:** in "zweihundertfünfzig two hundred fifty Milligramm" (a German strength repeated in English), "two" joined the German run, so "hundred fifty" stated 150, and Pregabalin 150 mg reached `match`. Round 7's pair check only covered two numbers under 100.
   - **The target:** the English words now state what the code before batch 24 states for them: 250, 2, 100 and 50.
2. **`la` is an hour only before `una`; `las` only before a number up to 24.** The number can be a word or digits.
   - **The failure:** "Cardizem LA four hundred twenty milligrams" read "LA four" as four o'clock, stated 120, and Cardizem LA 120 mg reached `match`. "Adalat LA 30 ملغ" lost its 30.
   - **What must keep working:** "a la una y cuarenta y dos pastillas" still states 2, never 40 or 42. "tomo las cuarenta y dos pastillas" states 42.
3. **Digit hours:** digits up to 24 right after `las` state nothing unless a unit or dose word follows them. Digits after `la`, or above 24, state as before: "Adalat LA 1 tablet" states 1, and "tomo las 500 de paracetamol" states 500.
4. **Minutes:**
   - `menos` takes minutes as `y` does.
   - After the minutes, a `y` and a 1–9 are minutes too, unless a unit or dose word follows them. "a la una y treinta y cinco mil doscientos miligramos" states 1200, never 5 or 5200.
5. **`y` joins a ten only to a Spanish number or to `un`/`una`,** not to German `ein`: "treinta y ein mg" never states 31.

**What must keep working:** English and Arabic read exactly as before batch 24, and every earlier round still holds.

## Rules
- **Never create, modify or delete anything under `tests/contract/`, any `conftest.py`, `pyproject.toml` or `uv.lock`. A batch that touches them is rejected automatically.** A contract test that is skipped or xfailed fails the gate too.
- Don't edit `SPEC.md`, `scripts/`, `evidence/`, `docs/` or `finetune/`.
- Work only inside this repository. No network, no API keys, no git commits, no new dependencies.
- `uv` can't write its cache in your sandbox, so run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.
- **One test needs a local network socket that your sandbox forbids.** If it is the only failure, say so and close your goal. The gate runs outside the sandbox.
