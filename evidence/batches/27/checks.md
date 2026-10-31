# Batch 27: the checks after the merge (31 Oct), as pre-registered in `check-plan.md`

All on merged `main` (3d3a30e). Every result is reported.

## Offline ($0)
1. **The relation audit's ten traps** (`audit.py`, output in `checks-offline.md`): no wrong reply shown as fact (0 of 10), and every right reply keeps the careful listener's findings. Before batch 27, seven of the ten passed, three as false `match`es.
2. **The committed replies, re-scored** (`evidence/finetune/summarize.py`, both tables):
   - **Unchanged, byte for byte:** every score file of Spark 1.3, r1 and r2, so their headline numbers stand: Spark 1.3 203 of 303, r1 290, r2 295; on `test_spain` Spark 40, r1 55, r2 56. Harmful claims after the checks: 0 for every system.
   - **Base Glimmer's files changed, and its fully-right counts did not** (51 of 303; 11 on `test_spain`). The untuned model writes amounts the value check couldn't catch. Across its five changed files, comparing each miss line before and after:
     - **52 wrong amounts no longer shown:** 34 became no amount (mostly "mg" said and "ml" written: "got 80 ml, want 80 mg"; also "got 150 mcg, want 150 mg", "got 2 mg, want 1 mg"); 18 became right, where the answer had no amount (counts written as milligrams: "got 2 mg, want null");
     - **2 right strengths dropped,** each because the same claim's wrong intake was dropped and SPEC §2's pairing rule drops the other amount with it (`test_iid` #1 and #11). Both end as `insufficient_information`.
   - Post hoc and descriptive: these replies were committed on 29 Oct, before the rules existed, and base Glimmer is not a model the product uses.
3. **Every saved live report re-parsed** (`recheck_reports.py`): 97 report files, 120 claims, **0 changed**.

## Live
Items 4 (the audit's live probe, `probe_after.py`) and 5 (one default-path U1–U8 column) follow below when they have run.
