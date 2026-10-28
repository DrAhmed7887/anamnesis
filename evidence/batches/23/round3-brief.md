# Batch 23, round 3: the volume rule's last forms, and the timeline total

You are the builder for batch 23 of Anamnesis, round 3. Your round 1 and round 2 changes are in the working tree, uncommitted. The reviews are in `evidence/batches/23/supervisor.md` (Round 2) and `evidence/grills/m6-timeline-r2/effect.md`. Fix the items below and keep everything else as it is.

The new contract is `tests/contract/test_b23_round3.py`. SPEC.md §2's bullet "A volume other than 1 ml" was rewritten again. Read it first: it defines a shared **volume**, the **amount-first** and **volume-first** forms, and what is **kept**.

1. **The volume rule** (`anamnesis/providers/spark.py`, `_per_other_volume`). Implement SPEC §2 exactly.
   - **The volume, shared by both forms:**
     - before the number there may be a `(`, or a spoon word with an optional `of`/`de` and an optional `(`;
     - the spoon words are `teaspoon`, `teaspoonful`, `tablespoon`, `spoonful`, `tsp`, `ملعقة`, `ملعقة صغيرة`, `cucharada`, `cucharadita` and `cuillère`;
     - then the number, an optional `-`, and `ml`, `cc`, `millilitre(s)`, `milliliter(s)` or `مل`, where `مل` is not followed by `جم` or `غ`.
   - **Amount first:** add the connectors `por` and `par`, as whole words. With `in` or `في`, skip the match when `water`, `ماء`, `agua` or `eau` comes within the three words after the volume.
   - **Volume first:**
     - the words are `each`, `every`, `كل`, `cada` and `chaque`, not inside a word, then a volume and an optional `)`;
     - it counts only when a contains word comes within the three words after it: `contains`, `contain`, `has`, `contiene`, `contient`, `تحتوي`, `يحتوي`, `:` or `=`;
     - and only with no container word (`bottle`, `pen`, `cartridge`, `vial`, `ampoule`, `cup`, `عبوة`, `زجاجة`, `قلم`) before that contains word.
   - **Unchanged:** the digit translation (both Arabic-Indic sets and `٫`), the case-insensitive matching, and the number comparison with `parse_amount_text`.
2. **The timeline total** (`anamnesis/brief_html.py`): the `<td>` in `<tfoot>` gets `colspan` equal to `len(TIMELINE_COLUMNS)`.
3. **Your unit tests** (`tests/unit/test_b23_extra.py`): update any case the new rule now answers differently. For example, a volume-first line with no contains word is now kept. Add cases for the new forms.

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
