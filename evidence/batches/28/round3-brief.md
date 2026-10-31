# Batch 28, round 3: a release or salt the first reading gave must be repeated

Round 2 passed the gate and closed the four round 1 cases. The Opus supervisor's re-check found the false `match` still happens when the second reader drops the release instead of contradicting it. A step-5 reading "Concor 5 retard" (bisoprolol 5 mg, modified release) was replaced by a readable "Concor 5 mg" with release `unknown`; the catalogue then filled in immediate release, and the finding was `match`. Salt does the same.

The SPEC now settles it (§4 step 5b): when the step-5 reading gives a release other than `unknown`, the second must give the same release; when it names an ingredient's salt (an amount's `salt`, or the salt in `inn`), the second must name the same salt or salts for that ingredient. A missing one is a conflict too. A step-5 `unknown`, or an ingredient without a salt, can still be completed. New contract tests pin it (the latest `test(contract): batch 28`).

## Do, in `anamnesis/agent/loop.py`'s second-read check
1. **Release:** conflict when the step-5 release isn't `unknown` and the second's differs, including when the second's is `unknown` or it has no strength.
2. **Salt:** gather each ingredient's salts from both sources (the amounts' `salt` and the salt in `inn`) as a set, for each reading. Conflict when, for any ingredient where the step-5 reading has salts, the second's set isn't the same.

Update your own tests where they pinned the old behaviour. Everything else in the hard rules of `briefs/28.md` still holds.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass from the repo root, and `git status --porcelain tests/contract` prints nothing. Reply with a short report and the final test count.
