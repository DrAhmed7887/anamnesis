# Batch 24: the 8 Spanish and German live cases, run on main after the merge

- **When:** 29 Oct 2026, 23:37–23:40 CET. Main at 9099fd1 (batch 24 merged in 6360325), one run per case (`scripts/intake_live.py`).
- **Cost:** $0.18 of Meta in all (`evidence/spend/ledger.jsonl`).
- **Inputs:** synthetic voice notes (macOS `say`, Mónica and Anna; for runs only, never in the film). Each file matched its hash in `manifest.md` before any call.
- **Pre-registration:** `manifest.md` (23530fe, amended in 1ef4536 and a7a6828 before any call).
- **Reports:** `evidence/live/2026-10-29/report_<case>.json`.

## Findings against the pre-registration: 7 of 8
| Case | Expected | Live | Scored |
|---|---|---|---|
| S1 | `unresolved_name` | `missing_modality` | **miss** (transcription, below) |
| S2 | `match` | `match` | as expected |
| S3 | `missing_modality` | `missing_modality` | as expected |
| S4 | `insufficient_information` | `insufficient_information` | as expected |
| G1 | `match`, or `unreadable_source` + `missing_modality` if the pack is partial | pack read as partial: `unreadable_source` + `missing_modality` | as expected (the listed alternative) |
| G2 | `missing_modality` | `missing_modality` | as expected |
| G3 | the claim `unresolved_name`; the pack `missing_modality`, or `unreadable_source` if partial | the claim `unresolved_name`; box and blister read as two partial packs, each `unreadable_source` | as expected (the listed alternative) |
| G4 | `missing_modality` (reported as stopped) | `missing_modality`, status discontinued | as expected |

## Every miss, by its kind
- **S1, the finding: the transcriber wrote a different, catalogued brand.**
  - Voice Transcribe heard "Emconcor" as "Concor" and dropped "Tomo", so the claim is Concor, status unknown.
  - Concor resolves in the catalogue (bisoprolol, the same ingredient as Emconcor), and no photo was given, so `missing_modality` is what the rules give for that transcript.
  - Batch 24's grounding held: the claim kept no unsaid INN, and its 5 mg intake was stated.
  - `manifest.md` listed the risk ("Emconcor and Sortis aren't among the catalogue's keywords until batch 24b").
  - **The general risk:** the transcriber's keyword bias can turn an unknown brand into a known one. Here the ingredient is the same; another pair could differ. Recorded for after the freeze.
- **G2, the claim: a strength said with "half a tablet" came back as the intake amount.** "eine halbe Tablette Beloc-Zok hundert Milligramm" gave an intake of 100 mg with 0.5 units per intake. The expected claim had a strength of 100 mg and no intake. No pack was photographed, so the finding is unaffected.
- **Transcription slips that changed no finding:**
  - S3 "de un un gramo", read as 1 g;
  - G4 "vierhundert vierhundert", where the bare German number states nothing, as round 6 says;
  - G2 "BelocZok".

## What the cases confirm
- **S2:** the decimal comma survives the stated-amount check ("dos coma cinco miligramos" is 2.5 mg) and reaches `match`.
- **S4:** "medio comprimido" survives as half a tablet. The bare "quinientos" states nothing, so no strength is invented, and the finding is `insufficient_information`.
- **G1:** "zweimal täglich" states no amount, and the reader judged the pack partial.
- **S1 and G3:** no unsaid INN was kept in either case.
