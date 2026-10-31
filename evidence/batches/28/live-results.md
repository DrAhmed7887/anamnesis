# Batch 28's live check (31 Oct, 13:35–13:46 CET), as `live-plan.md` set out before any call

U1–U8, two runs each, on `main` at b0833c2 (batch 28 merged, the live script carried in): Spark 1.3 transcribes, extracts and reads; Muse Spark Open on Fireworks, at low effort, reads only what Spark 1.3 still reads as partial or unreadable after its zoom. Scored with `score_paired.py` (with and without the second reader, on the same runs) and `evidence/batches/22/intake_score.py` (against 8b993ff).

## The result
| | Correct | Harmful |
|---|---|---|
| **With the second reader** | **10 of 16** (5 of 8 in each run) | 0 |
| The same 16 runs without it (each recovered pack put back to partial) | 8 of 16 | 0 |

- **U7 is the difference, in both runs.** Spark 1.3 read the Sortis 40 mg box as unreadable even after its zoom (in every earlier column too); Spark Open read it from the same crop as atorvastatin 40 mg, and the case gave the expected `strength_mismatch` against "Lipitor twenty milligrams". The second region of that photo stayed abstaining for both models (`kept the first`).
- **U2, run 1:** Spark 1.3 read the Augmentin pack as partial and Spark Open read it correctly (amoxicillin 875 mg + clavulanic acid 125 mg), but the case still missed: the claim came back with no amounts, as on the default path earlier today. In run 2 Spark 1.3 read the pack itself.
- **U8:** both models read the Betaloc ZOK pack as partial, so the first reading was kept and the pack stays requestable for a re-photo.
- **U6:** `unresolved_name`, as in every column (a Chinese-only pack that never prints the brand).
- **Every second read was an abstention by Spark 1.3,** and every recovered reading printed the pack's real strength. No conflict was logged in these runs.

## Against what was written before the runs
- "Harmful: 0" held.
- "Packs like U2, U3 and U7 recovered in runs where Spark 1.3 abstains": U7 and U2 were recovered; U3 never needed it. "U6 stays `unresolved_name`; U8 may stay partial": both held.
- n = 8 cases × 2 runs, so this describes these runs: never "better" or "beats". The paired column is exact within a run, because nothing before step 5b depends on the second reader.

## Spend
Meta $0.50 and Fireworks $0.05, from the ledger (the runs' own totals: $0.54937).
