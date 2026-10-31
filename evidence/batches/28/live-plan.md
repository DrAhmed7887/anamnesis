# Batch 28: the live check of the second reader, written before any call

## What runs
- **The cases:** U1–U8, batch 21's staged cases on public Commons photos, with their synthetic `say` voice notes (`evidence/raw/media/public/`). The expected results are the ones pre-registered in batch 21 (8b993ff), scored with `evidence/batches/22/intake_score.py`.
- **The column:** Spark 1.3 transcribes, extracts and reads, as on the default path. With `--second-reader fireworks`, Muse Spark Open on Fireworks (low effort) reads only the packs Spark 1.3 still reads as partial or unreadable after its zoom.
- **Two runs per case:** 16 intakes on the merged `main`, one commit, in one sitting.

## What is reported (every intake, misses included)
1. **The score with the second reader:** correct, failed safe, or harmful, per case and run.
2. **The paired score without it, from the same run:** a region whose `second_read` replaced the reading would have kept Spark 1.3's partial reading, so that pack would have given `unreadable_source`. Within one run that is exact, because the loop's earlier steps don't depend on the second reader.
3. **Every `second_read`:** the region, Spark 1.3's final readability, the second reader's outcome (readable, partial, unreadable, conflict, error), and whether a replacing reading's ingredients and strengths match the pack's printed ones in the manifest.

## Expectations, written down before any call
- **Harmful:** 0. A wrong reading from the second reader that leads to a wrong finding shown as fact counts as harmful, and stops the batch from going into the film.
- **Second reads happen only on abstentions:** a `second_read` step for a region Spark 1.3 read as readable is a defect.
- **The likely effect:** packs like U2, U3 and U7 recovered in runs where Spark 1.3 abstains; U6 (a Chinese-only pack that never prints the brand) stays `unresolved_name`; U8 may stay partial. n = 8 cases × 2 runs, so this is descriptive: never "better" or "beats".

## Spend
About $0.75 of Meta (16 intakes) and $0.25 of Fireworks. `scripts/spend_check.py` runs first.
