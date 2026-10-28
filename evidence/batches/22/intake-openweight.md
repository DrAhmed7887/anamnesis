# The full intake with Muse Spark Open as its label reader (U1–U8), 28 Oct

**Why:** Ahmed entered the Best Build on Meta Open Weight Models bonus (`evidence/decisions.md`:150). The comparison (`comparison.md`) read crops outside the loop. This run makes Muse Spark Open the label reader inside the full intake.

## Plan, committed before the first call
- **Cases:** U1–U8 from `evidence/batches/21/manifest.md`, unchanged: the same voice notes, photos and pre-registered expected results (8b993ff). U9 and U10 are left out, because their DailyMed photos may not go to Baseten (`docs/DATA_HANDLING.md`).
- **Runs:** each case runs once with each reader, on the same code: `main` at the commit that adds this file. That commit holds the script flag, and `anamnesis/` is unchanged since batch 23.1 (0549fd3).
  - **Spark 1.3 reads the labels** (`<case>-b231`). This is the control. Batch 21's "after" column ran on older code (ea5a705), so without this column a difference could come from batches 22–23.1, not from the reader.
  - **Muse Spark Open on Baseten reads the labels** (`<case>-b231-open`), via `scripts/intake_live.py --reader baseten`.
  - **Everything else is the same in both:** Voice Transcribe, Spark 1.3 for the claims, SAM 3.1 and the caps.
- **Scoring:** the manifest's rules. The primary finding decides correct or miss. A second region of the same product is noise. A harmful miss is a false `match`, or a wrong strength or ingredient shown as fact.
- **Reporting:** both columns go beside batch 21's, with every miss and its cause. n = 8 and each case runs once, so a difference of a case or two can be chance. Batch 21's two columns are never replaced (claims row 4.11).
- **Spend:** about $0.03 a Meta intake, so about $0.50 on Meta and $0.20 on Baseten. `scripts/spend_check.py` runs first.

## Results
Filled in after the run.
