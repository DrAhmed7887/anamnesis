VERDICT: PASS

| # | severity (blocker/major/minor) | area (1–8) | evidence (file or section) | required action |
|---|---|---|---|---|
| 1 | major | 6 | `SPEC.md` §4 & `evidence/grills/m6-timeline/effect.md` #2 | Include `evidence/batches/22/comparison.md` and `evidence/batches/21/` live artifacts in the submission/QM package, or run `qm.sh` across `21 23` so the 39-photo and real-media claims are backed in-package. |
| 2 | minor | 2 | `anamnesis/providers/spark.py` (`_printed_before_volume`), `evidence/batches/23/supervisor.md` Round 9 #1 | Restrict the tablet/capsule-word carve-out in the before-form to connectors `in` and `في` (and pin in contract tests) so `250 mg = 1 tablet per 5 ml` cannot survive as a per-tablet reading. |
| 3 | minor | 2 | `evidence/batches/23/builder.md` Round 9, `SPEC.md` §2 | Pin the nominative colloquial Arabic dual spoon `معلقتان` (and `المعلقتان`) in `tests/contract/` (currently only `معلقتين` is in the contract while `معلقتان` is only in unit tests). |
| 4 | minor | 2 | `anamnesis/providers/spark.py` (`_PER_1ML_RE`, `_AFTER_AMOUNT_RE`) | Pin and handle plural per-1-ml targets (`100 mg / 1 millilitres`, `mililitros`) and multiple consecutive bracket groups before a connector (`250 mg (as base) (anhydrous) per 5 ml`). |
| 5 | minor | 4 | `README.md`, `CLAUDE.md`, `SPEC.md` | Merge the judge-facing `README.md` update and update `CLAUDE.md` so all docs consistently reflect the batch 22 open-weight comparison ("Built with Muse Spark Open"), "all product code in `anamnesis/`", and public pack photos under `docs/DATA_HANDLING.md`. |
| 6 | minor | 5 | `anamnesis/providers/spend.py`, `evidence/decisions.md` | Safety invariants: 1 (templates/no advice) HOLDING; 2 (no `*-contributor`) HOLDING (defense-in-depth: add check to `SpendGuard._append`); 3 (no secrets/personal data) AT RISK until the M1 Muse export with personal skill catalog is filtered out on Tue 3 Nov; 4 (synthetic/de-identified data) HOLDING under `DATA_HANDLING.md`; 5 (live calls on ledger) HOLDING. |
| 7 | minor | 8 | `evidence/grills/m5-openweight/effect.md` #10, `SPEC.md` line 3 | Complete remaining judge/clinician deliverables before submission: `LICENSE` file, hosted static brief, recorded human voice notes (currently only macOS TTS has been tested live), 10× hero run report, claims checklist, and video. |

Deadline risks:
- Filtering the git history on Tue 3 Nov to remove the M1 personal skill catalog export will rewrite commit SHAs and break hardcoded commit references across `evidence/` unless an automated SHA-remapping pass is verified.
- Real human speech (Ahmed's recorded voice notes) has not yet been tested live through Voice Transcribe and `stated_amounts`, leaving a late-stage risk of transcription or grounding misses on the hero demo path.
- Judge-facing deliverables (3-minute video, hosted interactive brief, `LICENSE`, and merged `README.md` with open-weight comparison tables) are concentrated in the final days before the Thu 5 Nov 03:00 CET deadline.
