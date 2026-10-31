# Why U2 misses on the claim side (post-hoc diagnostic, 31 Oct)

**The question:** U2 ("I take Augmentin, 875 and 125 milligrams, twice a day") missed in all three of today's live runs (batch 27's column, and both runs of batch 28's): the pack was read correctly (amoxicillin 875 mg + clavulanic acid 125 mg), but the claim came back with no amounts, so the pair was `insufficient_information`. The merged checks keep every plausible reply shape (tested offline in `evidence/batches/27/checks.md`), so the question was what Spark writes.

**What ran:** `claims_diag.py` sent U2's transcript to Spark 1.3 five times through the product's `MetaClaimExtractor` on `main` (4334037) and kept the raw replies (`replies.json`). $0.062 of Meta (five ledger lines, 13:39 UTC).

**What it shows:**
- **3 of 5 calls wrote no amount at all:** `intake_amount` null, `strength` null.
- **2 of 5 wrote the intake as the text "875 and 125"** (one with an empty strength). That isn't one amount, so it doesn't parse and is dropped, as SPEC §2 says.
- **So the miss is Spark's:** the claim schema's `intake_amount` holds one amount, and the claim prompt allows a `strength` (which can hold two) only when the patient describes the tablet. A combination's two spoken amounts fit neither, and the claim fails safe.

**Not changed before the hackathon:** the fix is the claim prompt (a combination said with two amounts is its strength), which means re-measuring Spark 1.3 on the 363 scored notes (about $4) and changes the headline Spark number. It's a known limit, and it fails safe.
