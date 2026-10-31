# Why the hero's claims lost their amounts on 29 Oct (post-hoc diagnostic, 31 Oct)

**The question:** in the hero's ten live runs (28–29 Oct, `evidence/batches/21/u11-u12.md`), r01, r05 and r09 came back with both claims' amounts missing. r05's transcript is word for word r02's, and r02 kept both amounts, so the speech wasn't the cause.

**What ran:** `claims_diag.py` sent r05's transcript to Spark 1.3 ten times through the product's own `MetaClaimExtractor` on `main` at 87e572c (before batch 27), and kept the raw replies (`replies.json`). The transcript is the hero's invented script, as Voice Transcribe heard the synthetic voice. About $0.08 of Meta.

**What it shows:**
- **Calls 5 and 6** wrote an empty strength object (`"ingredients": []`) on both claims. Before batch 24, an empty strength counted as a dropped amount, and a dropped amount takes the other with it, so both claims lost their intakes: r01, r05 and r09's pattern.
- **Call 8** wrote each intake's label as the string "null". Before batch 24 an ungrounded label could cost the amount; batch 24 gives it the claim's name.
- **Today, all ten calls keep both amounts** (Concor 10 mg, Beloc-Zok 50 mg): batch 24's "an empty strength is no strength" and its label rule cover both.

**So:** the hero's 6 of 10 was measured before batch 24's fix. Three failures in ten matches the three empty or "null" replies in these ten. A fresh pre-registered run of the hero is the honest way to report it; this diagnostic is post hoc and is not that run.
