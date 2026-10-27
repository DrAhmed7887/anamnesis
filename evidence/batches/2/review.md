# Batch 2 review: catalogue, reconciler, guardrails

Reviewer: Claude Code (Opus 5.5). Builder: codex `gpt-6-sol`, 35,940 tokens. Gate: pass, 81 tests (80 from the builder plus 1 regression test from the reviewer).

Verdict: PASS

## Checked against SPEC.md §3, the decision order
- `reconcile_pair` applies the 7 rules in SPEC order: unreadable, then unresolved, then ingredients, then discontinued, then strength, then intake, then match. ✅
- Units are converted to mg with `Decimal`. Ratios are compared exactly (`ratio_mismatch` vs a scaled `strength_mismatch`). Combinations are compared by INN, so ingredient order doesn't matter. ✅
- `reconcile_all` pairs claims by overlapping INN sets. Leftovers become one-sided findings, with an empty list for the missing side. ✅
- All 10 adversarial cases pass. The templates and questions are fixed text and pass `assert_no_advice`. ✅
- Pure functions: no network calls, no LLM. ✅
- The worker preamble worked: the raw log shows no reads outside the repo.

## Reviewer fix (on this branch)
- **Defect:** `Catalogue.resolve` treated `country` as a hard filter. A pack photographed in a country missing from the catalogue (for example `EG`, our core Egypt-to-Spain case) came back `unresolved_name` even with a clearly readable brand.
- **Fix:** the country is now a preference. `resolve` tries the local entries first, then falls back to any entry.
- Regression test: `test_country_outside_catalogue_still_resolves`. It failed before the fix (gate red) and passes after it (gate green).

## Notes for milestone 1 (not blocking)
- `assert_no_advice` is a blocklist: a minimum check, not a guarantee. It misses rephrasings ("it's best to use two"). All patient-facing text comes from fixed templates, which is the real control. The blocklist only catches template regressions.
- Rule 7 ("nothing to compare → `match`") means a readable pack with no strength read counts as a match on the INN alone. Decide in M1 whether that should be `match` with a note or a separate "unverified" status.
