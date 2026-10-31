# Batch 30, round 2: salts inside a combined `inn`, and a safer split

Round 1 passed the gate and does what SPEC §3's batch 30 bullet said. A fresh Muse audit and the Opus supervisor both found that the bullet was incomplete. The salt rules still read a combined `inn` whole, so a salt inside it was lost: "amoxicillin sodium" against a pack `inn` "amoxicillin trihydrate/potassium clavulanate" became a false `match`. They found smaller gaps in the split too. The SPEC bullet now settles each one, and new contract tests pin them at the end of `tests/contract/test_b30_combined_inn.py` ("round 2"). The contract commit is the latest `test(contract): batch 30`.

## Do
1. **Salts from each part** (`anamnesis/core/reconcile.py`, `_side_salts`): a combined `inn` adds one (ingredient, salt) pair per part, so the two-salts conflict and the different-salts rule see them.
2. **The split** (`_split_inn_parts`):
   - split on "/", "+", "&", a comma that isn't between two digits, a whole-word "and" (any case), and a spaced «و» only. An attached «و» doesn't split, because Arabic names can begin with it («وارفارين»).
   - no `\s*` around the separators: each part is stripped anyway, and the `\s*` backtracks badly on long runs of spaces (30,000 spaces took about 14 s).
3. **A stray separator:** when the split leaves one part ("amoxicillin/"), resolve that stripped part, not the raw string, in both branches of `_identity`.
4. **The second read** (`anamnesis/agent/loop.py`, step 5b): read a reading's `inn` through the same split, for its named ingredients and for its salts. Import the helper from `reconcile.py` rather than repeating it.

Update your own tests where they pinned the old behaviour. Everything else in the hard rules of `briefs/30.md` still holds, except that `anamnesis/agent/loop.py` may change for item 4.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass from the repo root, and `git status --porcelain tests/contract` prints nothing. Reply with a short report and the final test count.
