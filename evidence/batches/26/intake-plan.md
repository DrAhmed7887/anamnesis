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
