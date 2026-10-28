# Batch 23.1: the independent supervisor's review

## Round 1 (Opus 5.5, high effort, 28 Oct). Builder: Muse Code (`muse-spark-1.3`)

SUPERVISOR: APPROVE

Nothing needs changing. Muse's change touches only `anamnesis/providers/spark.py` and `anamnesis/providers/spend.py`, plus a new `tests/unit/test_b23_1_extra.py`. pytest gives 1932 passed.

1. **minor, a fact for the record, no fix:** `scripts/muse_usage.py` writes the Muse ledger line even when a contributor model appears in the session; it only prints a warning. That ledger records the builder's own usage. It isn't a `SpendGuard` path, and recording what happened is right.

**What ran, and what came out:**
- **The `in`/`في` condition:** all of the supervisor's batch 23 round 9 #1 inputs are now null:
  - "250 mg = 1 tablet per 5 ml";
  - "capsule strength per 5 ml";
  - "250 mg tab/5 ml" and "Tabs/5ml";
  - «ما يعادل قرص لكل ٥ مل» and «أي قرص واحد لكل ٥ مل»;
  - "comprimido por 5 ml";
  - "capsules or suspension per 5 ml".

  "= one tablet in each 5 ml" stays kept, as expected.
- **The dissolving and dispersing lines stay kept:** Vitamin C, the Arabic effervescent line, prednisolone, Zithromax, Euthyrox, omeprazole, and "disperse in 10 ml of milk or juice".
- **Earlier rounds:** across 378 probe labels, the only change from round 9 is a contrived Concor line, now null. Every earlier fail-open stays null.
- **The new pins hold:**
  - three bracket groups before `/`, and two before `per`, are null;
  - the plural per-1-ml prints are kept;
  - the colloquial duals are null.
- **The contributor check comes before any ledger write:**
  - `SessionGuard` calls its parent before recording, so a refusal leaves its dollars and calls unchanged;
  - `_append` has three callers, and each is now checked: two through `ProviderTrace`'s validator, and `charge_estimate` directly;
  - no `model_construct` or `model_copy` bypasses it;
  - no script writes a Meta spend line.
- **Beyond the rule:** the step sums and the `add_photo` sum hold.
