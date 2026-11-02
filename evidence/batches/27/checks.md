# Batch 27: the checks after the merge (31 Oct), as pre-registered in `check-plan.md`

All on merged `main` (3931b42). Every result is reported.

## Offline ($0)
1. **The relation audit's ten traps** (`audit.py`, output in `checks-offline.md`): no wrong reply shown as fact (0 of 10), and every right reply keeps the careful listener's findings. Before batch 27, seven of the ten passed, three as false `match`es.
2. **The committed replies, re-scored** (`evidence/finetune/summarize.py`, both tables):
   - **Unchanged, byte for byte:** every score file of Spark 1.3, r1 and r2, so their headline numbers stand: Spark 1.3 203 of 303, r1 290, r2 295; on `test_spain` Spark 40, r1 55, r2 56. Harmful claims after the checks: 0 for every system.
   - **Base Glimmer's files changed, and its fully-right counts did not** (51 of 303; 11 on `test_spain`). The untuned model writes amounts the value check couldn't catch. Across its five changed files, comparing each miss line before and after:
     - **52 wrong amounts no longer shown:** 34 became no amount (mostly "mg" said and "ml" written: "got 80 ml, want 80 mg"; also "got 150 mcg, want 150 mg", "got 2 mg, want 1 mg"); 18 became right, where the answer had no amount (counts written as milligrams: "got 2 mg, want null");
     - **2 right strengths dropped,** each because the same claim's wrong intake was dropped and SPEC §2's pairing rule drops the other amount with it (`test_iid` #1 and #11). Both end as `insufficient_information`.
   - Post hoc and descriptive: these replies were committed on 29 Oct, before the rules existed, and base Glimmer is not a model the product uses.
3. **Every saved live report re-parsed** (`recheck_reports.py`): 97 report files, 120 claims, **0 changed**.

## Live (31 Oct, 12:35–12:54 CET, `main` at 54adcee)
4. **The audit's live probe, again** (`probe_after.py`, `probe_after.json`): ten traps × Spark 1.3 and the tuned Glimmer.
   - **19 of 20 calls show no wrong finding as fact.** Spark 1.3 got all ten right or failed safe, as on 31 Oct at 00:07.
   - **J on the tuned Glimmer is still wrong as fact, and the pre-registered expectation ("should now fail safe") did not hold.** Batch 27 dropped Glimmer's 10 mg intake (rule 6), but its reply also put 5 in `units_per_intake` ("five in the morning" read as five tablets), a field the relation checks don't cover (SPEC §2, "Known limits": `regimen` numbers aren't checked). So the false `intake_differs_from_unit_strength` of 00:07 became a false `strength_mismatch`: a false disagreement, not a false match.
   - **The fix goes into batch 27.1:** when the relation checks drop a claim's amount, its `units_per_intake` goes too, unless a count mention (rule 3) grounds that value. J then fails safe.
5. **One default-path U1–U8 column** (`intake_score.py`, against d5f0606): **3 of 8 correct, 0 harmful.**
   - U1, U3 and U5 correct.
   - **U4, U7 and U8: Spark 1.3 read the pack as partial, even after its zoom** (`unreadable_source`), so the claim stood alone. U4 was read in full on 30 Oct: the reader varies from run to run. These are batch 28's target.
   - **U2:** the claim came back with no amounts, so the pair with the correctly read Augmentin pack is `insufficient_information`. The merged checks keep every plausible shape of that reply (a strength of 875/125, an intake of 875, or both: tested offline), so the amounts were missing from Spark's reply itself; the adapter doesn't keep raw replies.
   - **U6:** `unresolved_name`, as in every column: the Chinese-only pack never prints the brand.

**The hero's ten fresh runs** are reported in `evidence/diagnostics/hero-claims-2026-10-31/results.md`.

**Spend:** Meta $0.80 from the ledger: the probe's ten Spark calls $0.14, the column $0.26 and the hero $0.40. Modal: ten calls at $0.043 estimated, plus one cold start, to reconcile from Modal's billing.
