# Batch 23: the CEO's reference build, 28 Oct

- **Contract:** `test_b23_timeline.py` (part 1), `test_b23_m5_fixes.py` (part 2) and `test_b23_coverage.py` (parts 3–4): 56 tests.
- **On the code before the batch:**
  - part 1 fails at import, because the templates don't exist yet;
  - part 2: 9 of 13 fail; the 4 that pass are the #5 pin and the standard models;
  - parts 3–4: 17 of 23 fail; the 6 that pass are the earlier-concept cases and the strengths that must be kept.
- **Reference build** (a scratch copy with all nine items done by the CEO): **1178 passed**, ruff clean.
- **Older tests that counted two SAM concepts:** `test_b15_m3_blockers.py::test_the_report_counts_spend_of_a_failed_call` (contract) now counts three, updated by the CEO in this lock commit. `tests/unit/test_agent_extra.py::test_provider_error_becomes_a_step_without_prose` (unit) is listed in the brief for Muse to update.
- **One mutant per part**, each applied alone to the reference, is caught by the contract:
  - a failed call's cost recorded as 0: 1 failure;
  - `package` dropped from the concepts: 2 failures;
  - the volume rule weakened to volumes over 5 ml: 15 failures;
  - `ProviderTrace` back to the exact `-contributor` suffix: 4 failures.
- **The #5 pin:** an unstated units count of "two", "2" or «اتنين» gives `intake_differs_from_unit_strength` on today's code, never `match`, as SPEC §2 Known limits says. My first version of that test failed only because its regimen lacked the `as_needed` key.
