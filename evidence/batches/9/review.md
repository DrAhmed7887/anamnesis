# Batch 9 review: brand-named intakes and joined brand names

Reviewer: Claude Code (Opus 5.5). Builder: codex `gpt-6-luna`. Gate: pass, 264 tests. The contract replays the **real** claims Spark extracted on 27 Oct, in English and Arabic.

Verdict: PASS

## Checked
- `_intake_type` resolves a brand-named intake (`"concor"`) through a single-INN catalogue entry before comparing. If the ingredient still differs, or can't be resolved, the result is an extraction conflict (`insufficient_information`), never a strength alarm. SPEC rule 7 updated. ✅
- Brands with spaces or hyphens also match their joined form (`"BelocZok"`), with whole-word boundaries kept, so `"beloczokx"`, `"Belo"` and `"Zok"` don't match. ✅
- Both **fixtures** (the English run and the first Arabic run, which used Latin spellings) now reconcile **offline** as a clinician would expect: Concor `match`, metoprolol 50 mg twice a day vs Beloc-Zok 100 mg `intake_differs`, Panadol (stopped, no pack) `missing_modality`. ✅
- *Correction, 27 Oct (QM M2 round 2, #7):* later live Arabic runs with Arabic-script brands stayed `unresolved_name` until batch 11, which proves them **offline** only. No live Arabic run has been made since batch 11, because the QM HOLD blocks live runs.

## Why the fix is in the reconciler, not the prompt
The extraction prompt says not to infer an INN from a brand, which keeps the claim honest about what the patient actually said. The reconciler is deterministic and auditable, so the catalogue lookup belongs there.
