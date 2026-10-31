# Batch 27, round 2: the unit rule holds for every claim

Your round 1 passed the gate. Thank you for flagging three conflicts and the brief's wrong line about labels (the SPEC was right: labels are never own names).

## The CEO's decisions on your three conflicts
1. **Rule 2 for claims outside the catalogue: reversed.** Your hook skips the unit check when `name_text` resolves to no catalogue entry (`match_unit = entry is not None` in `anamnesis/providers/claims.py`). Most real medicines aren't in the 12-entry catalogue, so that switches rule 2 off where it matters most. The batch 24 row that pinned 1 mg for "Farxiga ein Gramm" carried "mg" only as its test's default; the CEO changed that row to `g`, and the contract now pins rule 2 for a medicine outside the catalogue (`test_units_hold_for_a_medicine_outside_the_catalogue`).
2. **Rule 5, a past marker stopped by another medicine's name: accepted.** It is now in SPEC §2 rule 5.
3. **Rule 6, a splitter blocked when its clause names another medicine, with the 4-letter prefix match: accepted.** It is now in SPEC §2 rule 6.

## Do
1. Apply rule 2 to every claim: drop `match_unit` from the hook and from `is_amount_grounded`, or always pass True. Update its docstring.
2. Update your own tests if any relied on the exemption.

Everything else in the hard rules of `briefs/27.md` still holds.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass from the repo root, and `git status --porcelain tests/contract` prints nothing. Reply with a short report and the final test count.
