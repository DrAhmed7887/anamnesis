# Batch 23.1: the CEO's reference build

## Round 1 (28 Oct): the follow-ups to batch 23, pinned in `tests/contract/test_b23_1_followups.py`
- **Sources:**
  - the supervisor's batch 23 round 9 APPROVE, #1: the `in`/`في` hardening;
  - the Gemini 4 check of merged batch 23, `evidence/grills/m6-timeline-final/effect.md` #2–#4 and #6.
- **On main (batch 23 merged):** 14 of the 25 new tests fail:
  - the 8 tablet-word lines after `/`, `per`, `por` or `لكل`;
  - the 2 two-bracket-group lines;
  - the 2 plural per-1-ml prints;
  - the contributor check (3 ids).

  The 11 that pass are the dissolving keeps with `in`/`في` and the nominative dual, which batch 23 already handles.
- **Reference build** (batch 23's final reference, plus the `in`/`في` condition in `spark.py` and the contributor check in `spend.py`): all **1407** contract tests pass. Batch 23's reference already allowed any number of bracket groups and the plural targets.
- **Mutants,** each applied alone to the reference and run against every contract test. All 6 were caught:
  - the carve-out after any connector, and no carve-out at all;
  - one bracket group only;
  - a singular per-1-ml target;
  - no nominative dual;
  - an estimate that takes a contributor model.
