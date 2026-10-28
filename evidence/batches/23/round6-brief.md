# Batch 23, round 6: close the gaps in the own-unit rule

You are the builder for batch 23 of Anamnesis, round 6. Your round 1–5 changes are in the working tree, uncommitted. Your round 5 code matches SPEC §2 as it was written. Two reviews found gaps in the SPEC itself:
- **The supervisor's round 5 review** (`evidence/batches/23/supervisor.md`, Round 5). Its main finding: the refusal misses an amount after "B.P." or "approx." because the sentence ends at their `.`.
- **The CEO's differential check:** insulin pens written "3 ml pen, 100 U/ml" lost a correct strength.

Read SPEC §2 "A volume other than 1 ml" again. It was updated, and it holds every word list you need. The new contract is `tests/contract/test_b23_round6.py`; the round 1–5 contracts still hold.

1. **The refusal** (`_printed_beside_a_volume` and what it calls) changes in three ways:
   - **The sentence ends** at `;`, `!`, `?` or `؛`, and at a `.` only when a space and a capital or Arabic letter follow it, or at the end of the text. `B.P. 250 mg` and `approx. 250 mg` stay in the sentence. A line break still doesn't end it.
   - **The before-form takes up to three words** between the amount and the connector (`250 mg base/5 ml`, `250 milligrams per 5 ml`), then an optional `each`, `every`, `cada`, `chaque` or `كل` after the connector (`250 mg in each 5 ml`). Check every number before the volume, not only the nearest.
   - **The own print doesn't count.** For a reading per `ml` or `dose`, an amount that starts the reading's own print in that unit doesn't count in the later-in-its-sentence check: a per-1-ml print for `ml`; a per-1-ml or per-dose print for `dose`. A tablet or capsule print is never excused there.
2. **The per-volume rule:** for a reading per `tablet`, `capsule` or `dose`, a volume right after an amount (the always-counts form: a number, its unit if any, `/`, `∕`, `／`, `per`, `por`, `par` or `لكل`) nulls the strength outright.
3. **The tablet print:** a `,` or `،` between the amount and the tablet word now also blocks it.
4. **Water** changes in three ways:
   - **a bracket that closes after the volume** may come before the lead-in words (`a glass (200 ml) of water`);
   - **brackets after a water word** exempt only a volume alone inside them, optionally after `approx`, `aprox`, `about`, `ca`, `env`, `environ` or `حوالي`;
   - **only a hyphen joined to a word** makes `water-based`; a dash with spaces around it doesn't.
5. **Volumes and units:**
   - **volumes:** add `mililitro(s)`, `cm3` and `cm³`;
   - **`مل`:** excluded only where it starts `ملجم`, `ملغ` or `ملعقة`. This holds in a volume and in the per-1-ml print, and `ملي` still counts;
   - **units:** add the word forms (`milligram(s)`, `microgram(s)`, `gram(s)` and the Spanish and French forms).
6. **Your unit tests** (`tests/unit/test_b23_extra.py`):
   - `test_round5_capsule_print_right_after_the_amount_is_kept` ("500 mg capsules in 5 ml syrup") now drops on purpose: the before-form takes the words between the amount and `in`. Change it.
   - Your round 3 case "Syrup 250 mg/5 ملي" must keep dropping.
   - Add cases for each change above.

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
