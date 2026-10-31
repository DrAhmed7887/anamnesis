# U2's claim after batch 30 (post-hoc diagnostic, 31 Oct)

**The question:** in batch 30's live check, the pack side of U2 was right in 3 of 3 runs, but the claim lost its amounts in 2 of 3. Was that the transcripts, our checks, or Spark?

**What ran:** Spark 1.3 through the product's `MetaClaimExtractor` on `main` 3bbc770, which has batch 29's prompt. The raw replies are kept.
- **`claims_diag.py`:** 5 calls on the first diagnostic's transcript. Raw replies in `replies.json`; $0.05689.
- **`claims_diag_live.py`:** 3 calls on each missed run's exact transcript. Raw replies in `replies_live_transcripts.json`; $0.07972.

**What it shows:** all 11 calls kept amoxicillin 875 mg + clavulanic acid 125 mg. The live misses are Spark's extraction varying between calls. The full write-up is in `evidence/batches/30/live-results.md`.
