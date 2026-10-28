# Batch 23, round 4: one clause rule for a strength printed per a volume other than 1 ml

You are the builder for batch 23 of Anamnesis, round 4. Your round 1–3 changes are in the working tree, uncommitted. The supervisor's round 3 review (`evidence/batches/23/supervisor.md`, Round 3) found that the wording patterns of rounds 1–3 keep missing standard carton wordings. One example is "Each 5 ml of reconstituted suspension contains amoxicillin 250 mg", still read as 250 mg per ml. So the CEO replaced them in the SPEC with one clause rule. Read SPEC §2 "A volume other than 1 ml" first. It was rewritten.

The new contract is `tests/contract/test_b23_round4.py`. The round 1–3 contracts still hold.

1. **Replace the volume code** in `anamnesis/providers/spark.py` with the clause rule. That code is the two volume regexes, the spoon, contains, container and water word sets, `_has_water_after` and `_volume_first_counts`.
   - **First, translate the digits:** both Arabic-Indic sets, and `٫` to `.`.
   - **Cut the text into clauses** at `.` and `,` (not between two digits), `;`, `!`, `?`, `،`, `؛` and line breaks.
   - **A volume** is a number other than 1, an optional `-`, and `ml`, `cc`, `millilitre(s)`, `milliliter(s)` or `مل`, where `مل` must not be followed by `جم` or `غ`. Matching ignores case.
   - **A water clause** names `water`, `ماء`, `agua` or `eau`. It is not one when it says purified, distilled or sterile water, water for injection, `ماء مقطر`, `agua purificada`, `agua destilada`, `eau purifiée`, `eau distillée`, or `water-based`. A volume in a water clause doesn't count.
   - **The strength becomes null** when a clause that isn't a water clause holds a volume, and either:
     - the reading is per `ml` or per `dose`, unless every ingredient's amount is also printed per 1 ml. That means the amount, its unit if any, one of `/`, `∕`, `／`, `per`, `por`, `par`, `لكل`, `in` or `في`, an optional `1` or `1.0`, then `ml` or `مل`.
     - Or the reading is per `tablet` or `capsule`, and either one of its amounts is printed with a unit in that same clause, or the text never names a tablet or capsule.
       - The units are `mg`, `mcg`, `µg`, `μg`, `g`, `IU`, `unit(s)`, `مجم`, `ملجم`, `ملغ`, `مغ`, `جم`, `غ` and `وحدة`.
       - The tablet and capsule words are `tablet`, `tab`, `capsule`, `caps`, `comprimido`, `cápsula`, `comprimé`, `gélule`, `قرص`, `أقراص` and `كبسول`, with their plurals.
   - **The helper now needs the reading's `per`,** so pass it the whole strength. Keep the rule in a few small helpers, and change nothing else.
2. **Rewrite your unit tests** (`tests/unit/test_b23_extra.py`). Some round 2–3 cases pin the old patterns; rewrite them to the new rule. For example:
   - the container exemption;
   - `each` inside `peach`;
   - "within";
   - kept lines with a dose volume in another clause and no tablet word.

   Add cases for the clause rule.

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
