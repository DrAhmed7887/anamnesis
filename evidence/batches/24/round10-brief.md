# Batch 24, round 10: no English hour after `las`, and no article joins a number before it

You are the builder for batch 24, round 10. Your round 1–9 code is still in the working tree, uncommitted: keep it and build on it. Keep each change surgical: no refactors, and nothing outside this brief.

## Goal
Make `tests/contract/test_b24_round10.py` pass, and keep every other test green, including all of `tests/contract/test_b24_*.py`. First read the SPEC.md lines marked "round 10", and the round 8 and 9 lines they amend.

**One earlier contract test changed:** `test_b24_round8.py` no longer pins "a las eight y cuarenta y dos pastillas". After `las`, an English number word is no longer an hour, so that input now states 42.

## The fixes (`anamnesis/providers/stated.py`). Each one is pinned in `test_b24_round10.py`
1. **After `las`, only a Spanish number word up to 24, or digits up to 24, is a clock hour.** An English number word after `las` is no hour: it reads as English.
   - **The failure:** "Me tomo las two hundred fifty milligram tablets de Pregabalin" dropped "two" as an hour and stated 150, and Pregabalin 150 mg reached `match`.
   - **The same in English-only text:** "LAs", the English plural of the long-acting suffix, becomes `las` once lowercased. "I take two Cardizem LAs four hundred twenty milligrams each" stated 120.
   - **The target:** these inputs state exactly what the code before batch 24 states for them.
2. **An article counted as 1 joins no number before it, of any size, in any language.** Only Spanish `y` joins an article: "treinta y un miligramos" is still 31.
   - **The failure:** "zweihundert Ein-Gramm-Tabletten" stated 201, and "hundert Ein-Gramm-Tabletten" 101.
   - **Across languages:** "two hundred un miligramos" and "one thousand un gramo" must not state 201 or 1001. The article is a Spanish word, so it closes an English run as round 9's rule says.
   - **What must keep working:** the article still counts as 1 before its unit word.

**What must keep working:** English and Arabic read exactly as before batch 24, and every earlier round still holds.

## Rules
- **Never create, modify or delete anything under `tests/contract/`, any `conftest.py`, `pyproject.toml` or `uv.lock`. A batch that touches them is rejected automatically.** A contract test that is skipped or xfailed fails the gate too.
- Don't edit `SPEC.md`, `scripts/`, `evidence/`, `docs/` or `finetune/`.
- Work only inside this repository. No network, no API keys, no git commits, no new dependencies.
- `uv` can't write its cache in your sandbox, so run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.
- **One test needs a local network socket that your sandbox forbids.** If it is the only failure, say so and close your goal. The gate runs outside the sandbox.
