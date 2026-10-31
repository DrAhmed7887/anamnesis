# Batch 23, round 9: keep tablet strengths beside a dissolving line

You are the builder for batch 23 of Anamnesis, round 9. Your round 1–8 changes are in the working tree, uncommitted. The supervisor approved round 8 (`evidence/batches/23/supervisor.md`, Round 8). Its two minors are taken here. Read SPEC §2 "A volume other than 1 ml" again; two bullets changed. The new contract is `tests/contract/test_b23_round9.py`. The round 1–8 contracts still hold.

1. **The before-form doesn't refuse when its gap holds a tablet or capsule word.** The gap is the text between the amount and the connector, after brackets are stripped. Use the same tablet and capsule words as the tablet print. With such a word there, the volume is for dissolving, so "Vitamin C 1000 mg effervescent tablet, dissolve in 200 ml" keeps its strength. A tablet word inside brackets is stripped first, so "250 mg (equivalent to half a tablet) per 5 ml" still refuses.
2. **The colloquial dual:** add `معلقتين` and `معلقتان` to the colloquial spoons. They follow the same whole-word rule, with or without `ال`.
3. **Your unit tests** (`tests/unit/test_b23_extra.py`):
   - `test_round5_capsule_print_right_after_the_amount_is_kept` ("500 mg capsules in 5 ml syrup") keeps its strength again. Change it back to expect a strength.
   - Add cases for both changes.

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
