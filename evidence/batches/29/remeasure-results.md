# Batch 29's re-measure (31 Oct, 15:30–16:29 CET), as `remeasure-plan.md` set out before any call

Spark 1.3 with the batch 29 prompt, one call per note, on `main` at 12025aa, into `evidence/finetune/runs/spark-b29/`; the 29 Oct baseline (`runs/spark/`) is unchanged. 363 replies, no errors. Scored by `score_views.py`.

## Fully right (harmful after the product's checks)
| | test_iid | test_shift | test_codeswitch | test_real | **all four** | test_spain |
|---|---|---|---|---|---|---|
| **As pre-registered:** 29 Oct prompt | 67/100 (0) | 80/120 (0) | 31/50 (0) | 25/33 (0) | **203/303 (0)** | 40/60 (0) |
| **As pre-registered:** batch 29 prompt | 69/100 (0) | 76/120 (0) | 32/50 (0) | 23/33 (3) | **200/303 (3)** | 37/60 (0) |
| **Second view:** 29 Oct prompt | 67/100 (0) | 80/120 (0) | 31/50 (0) | 22/33 (0) | **200/303 (0)** | 40/60 (0) |
| **Second view:** batch 29 prompt | 69/100 (0) | 76/120 (0) | 32/50 (0) | 26/33 (0) | **203/303 (0)** | 37/60 (0) |

- **The pre-registered scoring counts the fix against Spark,** as the supervisor predicted: test_real's three U2 notes are keyed with no amounts, and their new replies name amoxicillin and clavulanic acid, which the patient didn't say, so they count as "harmful" (3). The product's own checks keep those names, because the brand contains them (SPEC §2, batch 24).
- **The second view** (defined before any call) keys those notes with the strength and doesn't count a brand's own ingredient as harm: then the batch 29 prompt gets all three U2 notes right, 0 harmful.
- **A fix to the second view's script, before it was read for the batch 29 runs:** its first version filtered brand ingredients only from the raw-reply harm count; the definition covers the count after the product's checks too, which `score.py` computes in a separate function. Fixed to match the definition.

## Which notes changed (`flips.txt`)
- **64 notes that aren't combinations flipped, both ways:** 31 gained and 33 lost (net −2). The commonest cause is `as_needed` written as false where the key wants null (22 lost, 11 gained), a field the sentence doesn't touch; strength problems are balanced (6 lost, 4 gained). Both runs are one call per note, so this is Spark's run-to-run variation, as the plan said it would be reported: no pattern points at the sentence.
- **The combination notes that changed** are test_real's three U2 notes (right under the second view) and one test_iid note whose only problem is `as_needed`.

## U2, three live runs
- **The claim side is fixed:** all three runs gave the strength amoxicillin 875 mg + clavulanic acid 125 mg per tablet, from transcripts that repeated words ("875 875", "milligrams, milligrams").
- **The finding is still `insufficient_information`,** in all three. The pack was read right (875/125 per tablet), but the reader wrote its `inn` as one string, "amoxicillin/clavulanic acid"; the reconciler requires a reading's `inn` to be one of its strength's ingredients, so it calls an extraction conflict and abstains. The claim-side miss had hidden this until now. **Batch 30** reads such a string as the set of ingredients it names.

## Against what was written before the runs
- "Harmful after the checks: 0": held under the second view; under the pre-registered scoring the 3 are the brand-ingredient names above.
- "No other systematic change": held (above).
- "U2: `match` in at least two of three runs": **not met**, for the pack-side reason above.

## Spend
$4.27 of Meta for the 363 notes (the script's own totals) and $0.09 for U2's three runs.
