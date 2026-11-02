# Batch 27.1's live check (31 Oct, 14:35 CET), as `live-plan.md` set out before any call

The relation audit's ten traps, once each on Spark 1.3 and the tuned Glimmer on Modal, through `probe_after.py`, on merged `main` (9d9bb89). Output: `probe_after.json`.

- **20 calls, no wrong finding shown as fact.**
- **Trap J on the tuned Glimmer now fails safe:** its claims came back with neither the intake nor the tablet count, and the finding is `insufficient_information`, where the probe after batch 27 gave a false `strength_mismatch`. The probe keeps parsed claims, not raw replies, so whether Glimmer wrote the same reply as then can't be told from here; the expectation ("should now fail safe") held.
- **Spark 1.3** got every trap right or failed safe; on J it found the right `match`.
- **As before:** C and F add the expected `missing_modality` for the unphotographed Panadol; E fails safe on both models (neither wrote the combination's two parts as a strength).
- **A first attempt** at 14:27 stopped after one call: the probe script's own runaway cap ($11.00 on the live-call ledger, then at $10.93) refused the next estimate before any spend. The cap was raised to $14.00, as for the day's other live runs, and the probe re-ran in full.
- **Spend:** $0.134 of Meta for the eleven Spark calls, and $0.048 of Modal per-call estimates on a server still warm from the first attempt (ledger lines 13:27–13:37 UTC).
