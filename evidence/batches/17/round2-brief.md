# Batch 17, round 2: fix the supervisor's findings

You are the builder for batch 17 of Anamnesis, round 2. Your round-1 change is in the working tree, uncommitted (`anamnesis/core/catalogue.py`, `anamnesis/core/reconcile.py`, `anamnesis/providers/claims.py`, `anamnesis/schema/templates.py`, `tests/unit/test_reconciler_extra.py`). An independent supervisor reviewed it; your C8 deviation was right, and SPEC now says so. Fix the items below and keep everything else as it is. The contract `tests/contract/test_b17_reconciler.py` has new cases, and SPEC.md §3 rule 8 ("Units per intake") and the C8 line changed: read both first.

1. **Blocker (SPEC rule 8, "Units per intake").** The units mapping must also run when the claim has an `intake_amount` whose comparison came out at r = 1. A model often copies the tablet strength into `intake_amount` for "half of the 20 mg", so "intake 20 mg, units 0.5" against non-splittable Lipitor 20 must give `strength_mismatch`, not `match`. Drop the `claim.intake_amount is None` condition; the units step still runs only after rule 7 found equal strengths (or there is no claim strength). Contract: `test_units_still_count_when_the_intake_came_out_even`.
2. **Arabic release words with clitics.** `ممتد` and `بطيء` must also be recognised with the attached clitics `ال`, `وال`, `بال`, `فال`, `لل`, `و`, `ف`, `ب`, `ل` (as `Catalogue._matches` accepts them for Arabic names): `"ميتوبرولول الممتد"` with an explicit modified release counts as said. Contract: the new C8 case.
3. **Shape.** `_pair_type` grew to about 68 lines. Move the units block into a small helper (for example `_units_check(claim, pack, catalogue) -> DiscrepancyType | None`) so `_pair_type` stays under about 50 lines and needs no second "comparison happened" flag.

## Rules (same as round 1)
- **Never create, modify or delete anything under `tests/contract/`.**
- Don't edit `SPEC.md`, `scripts/`, `evidence/` or `docs/`. No network, no API keys, no git commits, no new dependencies.

## Done when
`uv run ruff check .` and `uv run pytest -q` both pass (if `uv` can't use its cache, run the repo's `.venv` directly). Reply with the files you changed, one line per numbered item, and the final test count.
