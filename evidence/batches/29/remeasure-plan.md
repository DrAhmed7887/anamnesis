# Batch 29: re-measuring Spark 1.3 with its new prompt, written before any call (31 Oct)

## What runs, after batch 29 merges
1. **Spark 1.3 with the batch 29 prompt on the fine-tune's four test splits** (303 notes: test_iid, test_shift, test_codeswitch, test_real), through `finetune/spark_eval.py --out evidence/finetune/runs/spark-b29`, so the 29 Oct baseline replies in `runs/spark/` stay as they are. One call per note.
2. **test_spain** (60 notes) the same way, only if Ahmed allows the spend past the $75 line (below).
3. **U2 on the default path, three live runs** (`scripts/intake_live.py`, public photo, synthetic voice), scored with `evidence/batches/22/intake_score.py` against 8b993ff.

## What is reported (every note that changes, misses included)
- Fully right and harmful-after-checks for both prompts, per split, scored with `finetune/score.py`'s `score()` on today's checks.
- **Each note whose score changed, with its cause:** a combination said with two amounts (the sentence's target), or anything else. Both runs are one call per note, so a change on a note the sentence doesn't touch is run-to-run variation, not the prompt; it is reported as that.

## Expectations
- **Harmful after the checks: 0.**
- **Notes with a combination said as two amounts get their strength.**
- **No other systematic change.** If the prompt shifts Spark's behaviour elsewhere (for example strengths where intakes are wanted), it shows as a pattern across notes, and the sentence is reworded before the hackathon or reverted.
- **U2:** `match` in at least two of three runs.

## Spend
About $3.50 for the 303 notes, $0.70 for test_spain and $0.10 for U2, all Meta. The ledgers put Meta at $67.7 of $150; with Muse's read-only grills (in neither ledger, about $2.7), real use is about $70.4, so the full set would end near $75–76, around Ahmed's 50% stop line. Step 2 waits for his word.
