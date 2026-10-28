# Batch 23, round 7: tighten the SPEC's loose wording

You are the builder for batch 23 of Anamnesis, round 7. Your round 1–6 changes are in the working tree, uncommitted. Your round 6 code matches SPEC §2 as written. Two things showed where the SPEC was loose:
- **The supervisor's round 6 review** (`evidence/batches/23/supervisor.md`, Round 6). A `.` in "Ph. Eur." or "B. P." still ends the sentence and keeps the fivefold error.
- **A differential check by the CEO,** which found two loose wordings.

Read SPEC §2 "A volume other than 1 ml" again. It was updated. The new contract is `tests/contract/test_b23_round7.py`; the round 1–6 contracts still hold.

1. **The refusal's sentence end.** A `.` never ends a sentence when it comes right after a word of one to three Latin letters (`Ph.`, `Eur.`, `B.`, `P.`, `mg.`). Your round 6 rule otherwise stays as it is: spaces, not a line break, then a capital, accented or Arabic letter.
2. **Brackets.**
   - The refusal's before-form doesn't count text in brackets toward its three words. "250 mg (as amoxicillin trihydrate)/5 ml" is the amount, one word, then the connector.
   - The always-counts form (`_AFTER_AMOUNT_RE`) allows any bracketed text between the amount, or its unit, and the connector. So the per-volume rule also fires on "125 mg (as trihydrate) per 5 ml".
3. **Arabic.**
   - The spoon is the stem `ملعق` with any letters after it, so the dual `ملعقتين` counts.
   - `مل` is excluded where it starts `ملجم`, `ملغ`, `ملعق`, or a spelled-out milligram: `مللي جرام`, `ملي جرام` or `ملليجرام`. This applies in a volume and in the per-1-ml print. `ملي` alone still counts.
   - Add `مللي جرام`, `ملي جرام`, `ملليجرام`, `ميكروجرام` and `جرام` to the units. The space in the two-word forms is optional.
4. **Dose words:** add `drop`, `gota`, `goutte` and `نقطة` to the per-dose print.
5. **Your unit tests** (`tests/unit/test_b23_extra.py`): all of them still pass on the CEO's reference. Add cases for each change above.

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
