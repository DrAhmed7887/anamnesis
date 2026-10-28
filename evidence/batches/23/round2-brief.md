# Batch 23, round 2: fix the supervisor's and the Gemini check's findings

You are the builder for batch 23 of Anamnesis, round 2. Your round-1 change is in the working tree, uncommitted. The reviews are in `evidence/batches/23/supervisor.md` and `evidence/grills/m6-timeline/effect.md`. Fix the items below and keep everything else as it is.

The new contract is `tests/contract/test_b23_round2.py`. SPEC.md changed in three places. Read them first:
- §2: the bullet "A volume other than 1 ml", now with sub-bullets;
- §4: the Budget bullet;
- §8: the `add_photo` signature line.

1. **The volume rule** (`anamnesis/providers/spark.py`, `_per_other_volume`). Implement the two forms in SPEC §2 exactly.
   - **First, translate the text:** both Arabic-Indic digit sets and the Arabic decimal sign `٫` become ASCII (`٫` → `.`).
   - **Amount first:**
     - the amount;
     - optionally its unit: `mcg`, `µg`, `μg`, `mg`, `g`, `iu`, `unit`, `units`, `ملجم`, `مجم`, `ملغ`, `مغ`, `جم`, `غ` or `وحدة`;
     - a connector: `/`, `∕` (U+2215), `／` (U+FF0F), `per`, `in`, `لكل` or `في`, with `per`, `in` and `في` as whole words;
     - optionally `each`, `every` or `كل`;
     - optionally a spoon word (`teaspoon`, `teaspoonful`, `spoon`, `spoonful`, `tsp`, `ملعقة`, `ملعقة صغيرة`) with an optional `(`;
     - then the volume: a number, and `ml`, `cc` or `مل`, where `مل` must not be followed by `جم` or `غ`.

     When the amount is one of the reading's amounts and the volume isn't 1, the strength becomes null.
   - **Volume first:** `each`, `every` or `كل`, not inside a word, then such a volume, anywhere in the text. A volume other than 1 makes the strength null, whatever the amount.
   - **Both:** case-insensitive, and compare numbers with `parse_amount_text`.
2. **The call budget** (`anamnesis/agent/loop.py`, `run_intake`): `max_provider_calls: int | None = None`. When it's None, the budget is `2 + (len(concepts) + 2 * top_k) * len(images)`. An explicit value is used as given.
3. **One shared concepts default:** a module constant `SAM_CONCEPTS = ("medicine box", "label", "package")` in `loop.py`, the default `concepts` of both `run_intake` and `add_photo` (`anamnesis/review.py`).
4. **`add_photo`'s budget:** `max_provider_calls: int | None = None`. When it's None, use `len(concepts) + 2 * top_k`.
5. **Unit tests** for items 1–4 in `tests/unit/test_b23_extra.py`.

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
