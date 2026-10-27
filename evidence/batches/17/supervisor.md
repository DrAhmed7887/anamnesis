# Batch 17 supervisor (Claude Opus 5.5, high effort, read-only)

Prompt: `evidence/grills/BATCH_SUPERVISOR_PROMPT.md`. The builder was Muse Code (`muse-spark-1.3`); the supervisor is a different model family and was not told the CEO's opinion.

## Round 1: SUPERVISOR: CHANGES

1. **blocker** `anamnesis/core/reconcile.py` (the `claim.intake_amount is None` guard) with SPEC §3 rule 8, "Units per intake". Ran it: "Half of the Lipitor 20 mg every night", extracted as `intake_amount` atorvastatin 20 mg plus `units_per_intake` 0.5 (the extraction prompt tells the model to put an amount spoken with a frequency in `intake_amount`), against non-splittable Lipitor 20 mg gives **match**. So do intake 5 mg + units 2, and strength 5 + intake 5 + units 2, against Concor 5 mg. A harmful false agreement of exactly the C1 kind; not a regression, and the builder followed the SPEC wording. Fix: a SPEC edit and dropping the guard, so the units mapping also runs after the intake ratio came out at 1; consistent cases don't get worse.
2. **minor** `_RELEASE_WORDS`: `"ميتوبرولول الممتد"` (with the article) isn't recognised, giving `insufficient_information`; errs toward review, not agreement. Fix: accept the Arabic clitics before the Arabic release words.
3. **minor** `_pair_type` grew to about 68 lines with a second "comparison happened" flag. Fix: a `_units_check` helper.
4. **minor** tests that prove nothing: 15 of 33 contract and new unit tests already pass before the change (the QM #2 and #3 pins, brand-plus-ingredient, units = 1, the trusted C8 cases, the frozen demo). They work as regression guards; no "was: match" case passes without the change. QM #2 and #3 needed no code in this batch.

Checked and safe: the builder's C8 deviation matches the reworded SPEC; C4 flags no brand-plus-ingredient label (Panadol Extra, Augmentin, Beloc-Zok succinate, Lipitor with its Arabic alias) and catches two products in Arabic or a brand beside a different ingredient; the C1 parser nulls the claim's amounts for "1-2", "1 or 2", "2 tablets", "two", "½", "1/2" and "2.000"; nothing touches provenance, spend or model prose; the new `match` note passes `assert_no_advice`.

**CEO triage:** all accepted. #1 and #2 went into SPEC and the contract (second `test(contract): batch 17` commit, `ce05389`); #1–#3 went back to Muse as round 2 (`round2-brief.md`); #4 is recorded as intended regression guards.

## Round 2: SUPERVISOR: APPROVE
All three round-1 findings fixed; the widened units rule makes no consistent case worse (probes, offline).
- **#1:** intake 20 + u 0.5 against Lipitor 20 → `strength_mismatch`; intake 5 + u 2, and strength 5 + intake 5 + u 2, against Concor 5 → `intake_differs_from_unit_strength`. Unchanged: intake 10 + u 2 and intake 2.5 + u 0.5 against Concor 5 (`intake_differs`), intake 10 + u 0.5 against Lipitor 20 (`strength_mismatch`), intake 5 + u 1 (`match`); unequal strengths flag at the strength step; combinations, capsules and liquids as expected (liquid + units → `insufficient_information`).
- **#2:** `_says_release` accepts `الممتد`, `فالممتد`, `وبطيء`; Latin words stay whole-word (`er` counts, `erm` doesn't).
- **#3:** the units block is `_units_check`; the second flag is gone.
- Residual, not blocking: the feminine `الممتدة` isn't recognised, giving `insufficient_information` (errs toward review, never a false `match`).
