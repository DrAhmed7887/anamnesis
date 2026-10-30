# The full intake with the open weights inside it (U1–U8), batch 26

**Why:** batch 26 makes the tuned Muse Glimmer on Modal an optional claim extractor, and Muse Spark Open on Fireworks an optional label reader (SPEC §4). This run puts both inside the full intake, on cases whose expected results were committed before any model saw them.

## Plan, committed before the first call
- **Cases:** U1–U8 from `evidence/batches/21/manifest.md`, unchanged: the same synthetic voice notes, the same Commons photos and the same pre-registered expected results (8b993ff). They are scored by `evidence/batches/22/intake_score.py`, unchanged.
- **Code:** `main` after batch 26 merges. Each case runs once in each column, all on that one commit.
- **The columns:**
  - **`<case>-b26`, the control:** the default path. Spark 1.3 extracts the claims and reads the labels.
  - **`<case>-b26-glimmer`:** the tuned Glimmer extracts the claims, and Spark 1.3 reads the labels. It shows what the claim step alone changes. Cut first if time runs short.
  - **`<case>-b26-open`:** the tuned Glimmer extracts, and Muse Spark Open on Fireworks reads (JSON mode off).
  - **The same in all three:** Voice Transcribe and SAM 3.1 on Meta's API, `--top-k 3`, and the caps.
- **Known risks, written before any call:**
  - **U2:** the tuned model read "Augmentin 875 and 125" as one 875 mg intake on test_real #13–15 (`evidence/finetune/results.md`), so U2's claim may come out the same way.
  - **U6, U7 and U8** missed on the photo side on 28 Oct, in every column (an unresolved name, and unreadable sources twice). The claim extractor can't change those.
  - **The Fireworks reader** took 16 to 52 s a read in batch 22, so the open column will be the slowest.
- **Reporting:** the three columns go beside 28 Oct's, with every miss and its cause. n = 8, and each case runs once, so a difference of a case or two can be chance. It is never "better" or "beats", and never a count like "5 vs 3" without the causes.
- **Spend:** about $0.80 of Meta (Voice Transcribe and SAM in every column, Spark 1.3 in the first two), about $0.40 of Fireworks, and about $3 of Modal for the container's time. `scripts/spend_check.py` runs first. The live ledger is at $8.04, so each run passes `--cap 11.00`.
- **What goes where** (`docs/DATA_HANDLING.md`, batch 26): the transcript text of the synthetic notes goes to Modal, and the eight Commons photos go to Fireworks.

## Commands (from the main checkout)
```
GLIMMER_URL=<the deployed server> uv run python scripts/intake_live.py --cap 11.00 --case Uk-b26[-glimmer|-open] \
    --voice evidence/raw/media/public/voice/Uk.wav --photo evidence/raw/media/public/commons/<photo> --lang en \
    [--extractor glimmer] [--reader fireworks]
```
The server is warmed through `GET /health` first.

## Results, 30 Oct evening
- **Code:** `main` at dfc72e3, with batch 26 merged. The Glimmer server was deployed from that commit.
- **Files:** 24 intakes, each case once in each column. The reports are `report_<case>-<column>.json` in `evidence/live/2026-10-30/`, and each intake has a line in `runs.jsonl`.
- **Scoring:** `evidence/batches/22/intake_score.py`, unchanged. Every column ran with `--session-usd 0.50`, because the supervisor found the $0.25 default below two Glimmer estimates.

| Case | Expected | Spark 1.3 does both | Glimmer extracts, Spark 1.3 reads | Glimmer extracts, Spark Open on Fireworks reads |
|---|---|---|---|---|
| U1 Concor, Russia | `match` | ✓ | ✓ | no reading (Fireworks timed out) |
| U2 Augmentin, Belgium | `match` | the pack read as partial | the pack read as partial | no reading |
| U3 Panadol, Australia | `match` | ✓ | the pack read as partial | no reading |
| U4 Panadol, Finland, two tablets | `intake_differs_from_unit_strength` | ✓ | ✓ | no reading |
| U5 Norvasc 5 mg and 10 mg, Israel | claim ↔ the 5 mg box: `match` | ✓ | ✓ | ✓ |
| U6 Glucophage, China | `match` | `unresolved_name` | `unresolved_name` | no reading |
| U7 Sortis 40 mg vs "Lipitor twenty milligrams" | `strength_mismatch` | both regions read as partial | both regions read as partial | no reading |
| U8 Betaloc ZOK 100 | `match` | `insufficient_information` | the pack read as partial | no reading |
| **Correct** | | **4 of 8** | **3 of 8** | **1 of 8** |

- **Harm check:** no column has a false `match`, or a wrong strength or ingredient shown as fact.
- **The claim step.** The tuned Glimmer extracted the same claims as Spark 1.3 on seven of the eight cases: the same name, amount and unit.
  - On U2 it kept "Augmentin 875 mg", where Spark dropped the amount. That is the risk written down before the run: it reads "875 and 125" as one 875 mg intake, as on test_real #13–15. The pack was read as partial in that column, so no finding came from the pair.
  - Its claim requests took 4.3–7.0 s, against Spark 1.3's 10.2–22.4 s, on the same notes.
- **The second column's two extra misses are on the reading side.** Spark 1.3 read the labels in both of the first two columns. On U3 and U8 this draw read the pack as partial; in the first column it read U3 fully and U8 without a strength. That is run-to-run variation in the reader, not the extractor.
- **The third column failed on Fireworks' latency.** Spark Open on Fireworks timed out at the reader's 60 s limit on 7 of the 8 intakes, as 16 estimated ledger lines with the reason "timeout" show. Each of those intakes failed safe: no reading, so the claim stood alone (`missing_modality`), with nothing shown as fact.
- **Post-hoc diagnostic, not pre-registered:** one read of U1's first region on Fireworks with a 180 s limit, the same evening.
  - The successful attempt took 52 s, and the whole read 114 s.
  - It came back correct: bisoprolol 5 mg, readable.
  - In batch 22, reads on Fireworks took 16–52 s.

  So tonight's failures are latency at the product's limit, not wrong readings. The table keeps them as misses.
- **So:** inside the full intake, the tuned Glimmer gave the same claims as Spark 1.3 on seven of eight cases, in about a third of the time, with no harmful finding. Spark Open on Fireworks couldn't be judged tonight, because the host answered too slowly. n = 8 with one run each, so this is never "better", and never "4 vs 3 vs 1" without the causes above.

**Cost:**
- **Meta:** about $0.40 across the three columns, for Voice Transcribe, SAM 3.1 and Spark 1.3.
- **Fireworks:** $0.40, estimated from the ledger, and mostly charged timeouts.
- **Modal:** the per-call estimates came to $0.11. The container's time is reconciled in `evidence/spend/modal_ledger.jsonl` from Modal's billing summary.

The live ledger went from $8.04 to $9.01.

## A fourth column after batch 26.1: plan, committed before its first call (30 Oct, 23:40 CET)
- **Why:** the third column lost 7 of its 8 readings to Fireworks timeouts. The cause was the reasoning effort: the open-weight reader sent none, so Spark Open reasoned at its default, `xhigh`. Batch 26.1 makes `--reader fireworks` ask for `low`, as Spark 1.3's reader does (SPEC §4). Three diagnostic reads at `low` took 16–24 s, and all three were correct.
- **The column:** `<case>-b261-open`. The tuned Glimmer extracts and Spark Open on Fireworks reads, at low effort.
  - It runs on `main` after batch 26.1 merges, on the same eight cases, voice notes and photos, with the same expected results (8b993ff), the same scorer and the same caps (`--session-usd 0.50`).
  - The Glimmer server stays as deployed from dfc72e3, because batch 26.1 doesn't change it.
- **How it's reported:** as a second draw of the open column, after a fix. The third column stays in the table as run, 1 of 8.
  - The first two columns ran on dfc72e3. Batch 26.1 changes nothing on their paths, so they stay the controls, and this is noted beside them.
  - n = 8, one run each; never "better" or "beats".
- **Known risks, written before the run:**
  - **U2:** the claim may again come out as one 875 mg intake.
  - **U6:** every column so far gave `unresolved_name`. The Chinese pack never prints "Glucophage" in Latin script.
  - **A slow host:** Fireworks may still be slow at low effort on some crops. A timeout stays a miss.
- **Spend:** about $0.10 of Meta, $0.25 of Fireworks and about $2 of Modal (a cold start, the column and 10 idle minutes). `scripts/spend_check.py` runs first.

## The fourth column's results (30 Oct, 23:41–23:49 CET)
- **Code:** `main` at c016ccc, with batch 26.1 merged. The Glimmer server is as deployed from dfc72e3, because batch 26.1 doesn't change it.

| Case | Expected | Glimmer extracts, Spark Open on Fireworks reads at low effort |
|---|---|---|
| U1 | `match` | ✓ |
| U2 | `match` | `insufficient_information`: the pack read as amoxicillin 875 mg + clavulanic acid 125 mg, and the claim kept only 875 mg (the risk written down before the run) |
| U3 | `match` | ✓ |
| U4 | `intake_differs_from_unit_strength` | ✓ |
| U5 | claim ↔ the 5 mg box: `match` | ✓ |
| U6 | `match` | `unresolved_name`, as in every column |
| U7 | `strength_mismatch` | ✓, the first column to get it. Spark Open read the box as atorvastatin 40 mg, where Spark 1.3 read both regions as partial |
| U8 | `match` | the pack read as partial |
| **Correct** | | **5 of 8** |

- **Harm check:** no false `match`, and no wrong strength or ingredient shown as fact.
- **Timing:** every Fireworks read finished inside the 60 s limit, and the intakes took 31–94 s.
- **So:** with both model steps on Meta open weights (the tuned Glimmer on Modal and Spark Open on Fireworks), the full intake ran end to end on all eight cases and got five right. That's the most of the four columns, with no harmful finding.
  - It is one run per case, after a fix, and the first two columns ran on dfc72e3 with unchanged paths. So it is never "better" or "beats", and the third column stays in the record as run.
- **Cost:** about $0.18 on the live ledger, for Meta, Fireworks and Modal's per-call estimates. The container's time is reconciled from Modal's billing.
