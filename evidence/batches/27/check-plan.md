# Batch 27: the checks after the merge, written before the build finished (31 Oct, 11:00 CET)

All on the merged `main`, from the main checkout. Every result is reported, misses included.

## Offline ($0)
1. **The relation audit's ten traps** (`evidence/audits/relation-provenance/audit.py`): expected, no wrong reply shown as fact (0 of 10), and every right reply keeps the careful listener's findings.
2. **The committed replies, re-scored** (`evidence/finetune/summarize.py`, both tables): expected, every system's fully-right count and harmful count unchanged on every split. Any reply that changes is listed with its cause.
3. **Every saved live report re-parsed** with the merged checks (its claims rebuilt as a reply): expected, no claim's amounts change.

## Live
4. **The audit's live probe** (`probe_live.py`, ten traps × Spark 1.3 and the tuned Glimmer): expected, no wrong finding shown as fact. J on Glimmer, a false disagreement on 31 Oct, should now fail safe. About $0.10 of Meta, and one Modal cold start (about $1.5 of credit).
5. **One default-path column, U1–U8** (Spark 1.3 extracts and reads, `scripts/intake_live.py`), scored against batch 21's pre-registered expected results (d5f0606) with `evidence/batches/22/intake_score.py`. One run per case, about $0.35 of Meta. It is a smoke test of the merged code, not a comparison: label reading varies from run to run.

## Then
- `demo-freeze` moves to the merge after a fresh clone passes the suite.
- The judge session's pointer (`evidence/grills/m9-freeze/clean_checkout.md`) gets the README's new limits sentence.
