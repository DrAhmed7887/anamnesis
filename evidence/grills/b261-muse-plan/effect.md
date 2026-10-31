# Muse's plan for batch 26.1: what it changed

**What ran:** Muse Code (muse-spark-1.3) planned batch 26.1 read-only (`scripts/grill.sh b261-muse-plan`) on 30 Oct at 23:25 CET, before the contract. It cost $0.18 and read nothing held out.

**The script's "WARNING: contributor model in session" was a false positive.** The word matched the product's own refusal code, the `-contributor` checks in `openweight.py`, `claims.py` and `meta.py`, which Muse read. The session's billing records show only `muse-spark-1.3`, and so do b26-muse-plan's. `scripts/grill.sh` now passes `--contributor-mode off` explicitly, as `scripts/batch.sh` does.

**Verdict:** "Accept: add opt-in `reasoning_effort`, default None, live Fireworks passes `low`".

| # | Muse's risk | Outcome |
|---|---|---|
| 1 | The estimate is built from the body | Checked: `spark_call_estimate` reads `response_format`, the messages, the images and `max_tokens`, not other keys. The contract pins the same estimate with and without the option |
| 2 | Batch 22 pins the body | Kept: None sends today's exact body, pinned |
| 3 | A cut-short reply | Unchanged: a length stop stays non-retryable, pinned under `low` |
| 4 | The malformed-reply retry | Unchanged: one retry, both attempts charged, pinned under `low` |
| 5 | Live runs with JSON mode off, the eval with the preset | Decided in batch 26 and pinned there. The live `low` result covers `low` with JSON mode off only, and the write-up says so |
| 6 | Baseten and an unknown field | The script never passes an effort to Baseten, and the contract pins None there |
| 7 | Validating values | Taken: anything but `low`, `medium`, `high` and `xhigh` raises `ValueError` when the reader is built |

**Its open questions:** the timeout stays at 60 s, since the low-effort reads took 16–24 s. The effort lives at the call site, so `PRESETS` stays as the comparison ran. `reader_eval.py` stays at None, the pre-registered comparison. `runs.jsonl` doesn't record the effort, because the SPEC fixes it per reader. Streaming isn't needed at these latencies.
