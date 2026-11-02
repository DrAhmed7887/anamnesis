# The full intake with Muse Spark Open as its label reader (U1–U8), 28 Oct

**Why:** Ahmed entered the Best Build on Meta Open Weight Models bonus (`evidence/decisions.md`:150). The comparison (`comparison.md`) read crops outside the loop. This run makes Muse Spark Open the label reader inside the full intake.

## Plan, committed before the first call
- **Cases:** U1–U8 from `evidence/batches/21/manifest.md`, unchanged: the same voice notes, photos and pre-registered expected results (d5f0606). U9 and U10 are left out, because their DailyMed photos may not go to Baseten (`docs/DATA_HANDLING.md`).
- **Runs:** each case runs once with each reader, on the same code: `main` at the commit that adds this file. That commit holds the script flag, and `anamnesis/` is unchanged since batch 23.1 (4834df3).
  - **Spark 1.3 reads the labels** (`<case>-b231`). This is the control. Batch 21's "after" column ran on older code (1171009), so without this column a difference could come from batches 22–23.1, not from the reader.
  - **Muse Spark Open on Baseten reads the labels** (`<case>-b231-open`), via `scripts/intake_live.py --reader baseten`.
  - **Everything else is the same in both:** Voice Transcribe, Spark 1.3 for the claims, SAM 3.1 and the caps.
- **Scoring:** the manifest's rules. The primary finding decides correct or miss. A second region of the same product is noise. A harmful miss is a false `match`, or a wrong strength or ingredient shown as fact.
- **Reporting:** both columns go beside batch 21's, with every miss and its cause. n = 8 and each case runs once, so a difference of a case or two can be chance. Batch 21's two columns are never replaced (claims row 4.11).
- **Spend:** about $0.03 a Meta intake, so about $0.50 on Meta and $0.20 on Baseten. `scripts/spend_check.py` runs first.

## Results, 28 Oct evening
- **Code:** `main` at 24b1180, with `anamnesis/` as merged in batch 23.1.
- **Files:** 16 intakes, each case once with each reader. The reports are `report_<case>-b231.json` and `report_<case>-b231-open.json` in `evidence/live/2026-10-28/`, and each intake has a line in `runs.jsonl`.
- **Scoring:** `intake_score.py` (this folder). On batch 21's reports it gives batch 21's recorded verdicts.

| Case | Expected | Batch 21 (1171009), Spark 1.3 reads | Today, Spark 1.3 reads | Today, Spark Open reads |
|---|---|---|---|---|
| U1 Concor, Russia | `match` | `match` ✓ | `insufficient_information` | `match` ✓ |
| U2 Augmentin, Belgium | `match` | `insufficient_information` | `unreadable_source`: read as partial | `insufficient_information` |
| U3 Panadol, Australia | `match` | `match` ✓ | `match` ✓ | `match` ✓ |
| U4 Panadol, Finland, two tablets | `intake_differs_from_unit_strength` | ✓ | ✓ | ✓ |
| U5 Norvasc 5 mg and 10 mg, Israel | claim ↔ the 5 mg box: `match` | the 10 mg box, `insufficient_information` | the 5 mg box, `match` ✓ | the 5 mg box, `match` ✓ |
| U6 Glucophage, China | `match` | `unresolved_name` | `unresolved_name` | `unresolved_name` |
| U7 Sortis 40 mg vs "Lipitor twenty milligrams" | `strength_mismatch` | `unreadable_source` | `unreadable_source` | `unreadable_source` |
| U8 Betaloc ZOK 100 | `match` | `unreadable_source` | `unreadable_source` | `unreadable_source` |
| **Correct** | | **3 of 8** | **3 of 8** | **4 of 8** |

- **Harm check:** neither column tonight has a false `match`, or a wrong strength or ingredient shown as fact.
- **The one-case gap isn't the reader's.** U1 decides it, and both readers read the pack as bisoprolol 5 mg. The claim extraction is Spark 1.3 in both columns. It dropped the spoken "five milligrams" in the Spark 1.3 column and kept it in the Spark Open column. So the gap is run-to-run variation on the claim side.
- **U2 is the one case where the readers differ.**
  - Spark 1.3 read the pack as partial, so the intake called it unreadable.
  - Spark Open read it as readable: amoxicillin 875 mg + clavulanic acid 125 mg. It still misses, because the claim came back without its amounts, as in batch 21. The Spark 1.3 column's claim had no amounts either.
- **U5:** the claim paired with the 5 mg box in both columns tonight, on today's code. That is one run per reader, so it isn't proof the cause is fixed.
- **So:** with Muse Spark Open as its label reader, the full intake ran end to end on these eight cases. It gave the same correct-or-miss verdict as Spark 1.3 on seven of them, and no harmful reading. n = 8 with one run each, so this is never "better", and never "4 vs 3" without the U1 note.

**Cost and time:**
- **16 intakes:** $0.56319 (`runs.jsonl`). Meta took $0.36822: Spark 1.3 $0.31492, SAM 3.1 $0.05000 and Voice Transcribe $0.00330. Baseten took $0.19497 for the 15 Spark Open reads.
- **Per intake:** $0.022–0.041 with Spark 1.3 reading, and $0.024–0.055 with Spark Open.
- **Time:** 28.9–45.7 s per intake with Spark 1.3 reading, and 31.7–63.4 s with Spark Open.
