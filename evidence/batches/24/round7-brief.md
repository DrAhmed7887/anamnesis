# Batch 24, round 7: round 6's rule, whatever closes the run

You are the builder for batch 24, round 7. Your round 1–6 code is still in the working tree, uncommitted: keep it and build on it. Keep each change surgical: no refactors, and nothing outside this brief.

## Goal
Make `tests/contract/test_b24_round7.py` pass, and keep every other test green, including all of `tests/contract/test_b24_*.py`. First read the SPEC.md lines marked "round 7".

## The fixes (`anamnesis/providers/stated.py`). Each one is pinned in `test_b24_round7.py`
1. **A Spanish or German number never joins an English number after it.** When a plain number under 100 comes right after a plain number under 100, with no `y` between, close the run if either of the two words is Spanish or German or an article. Round 5 checked only the second word.
   - **The failure:** "cinco five mg" stated 10, "diez thirty milligrams" 40 and "zwei two Tabletten" 4.
   - **What must keep working:** English "twenty five milligrams" is 25, and Spanish "treinta y cinco miligramos" is 35.
2. **Every close of a Spanish or German run applies round 6's amount rule.** Whatever closes the run, it states its values only when the token right after it is a unit or dose word. The closes include:
   - another number (the round 5 adjacency close);
   - a `y` that joins nothing;
   - an English multiplier such as "hundred";
   - the end of the part.

   **The failure:** "elf cinco miligramos" stated 11. The simplest way is one close helper that every path calls.
3. **A decimal with Spanish or German digits is a Spanish or German run.** When the digit words after an English "point" are Spanish or German, the decimal counts only before a unit or dose word, as `coma` and `komma` already do. "la point seis" and "al point sieben diez" state nothing; "point sieben Milligramm" is 0.7.

## Rules
- **Never create, modify or delete anything under `tests/contract/`, any `conftest.py`, `pyproject.toml` or `uv.lock`. A batch that touches them is rejected automatically.** A contract test that is skipped or xfailed fails the gate too.
- Don't edit `SPEC.md`, `scripts/`, `evidence/`, `docs/` or `finetune/`.
- Work only inside this repository. No network, no API keys, no git commits, no new dependencies.
- `uv` can't write its cache in your sandbox, so run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.
- **One test needs a local network socket that your sandbox forbids.** If it is the only failure, say so and close your goal. The gate runs outside the sandbox.
