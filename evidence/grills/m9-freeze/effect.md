# QM M9 (batches 24–24.1, the freeze): triage

**Verdict: PASS.** Gemini 4 Argon on Vertex read an 826 KB package (311,372 input tokens), for $0.64 est. (`evidence/spend/google_ledger.jsonl`). Nothing blocks the `demo-freeze` tag. After the freeze, a change goes in only to fix:
- a harmful false agreement;
- wrong provenance;
- advice leakage;
- a spend-cap failure;
- a failure on the frozen demo path.

| # | Finding | Decision |
|---|---|---|
| 1 | Major: the README on main makes stale claims | **Planned, Tue 3 Nov:** the judge-facing README draft merges before submission. It is docs, not the demo path. |
| 2 | Major: the public copy needs its history filter first (the M1 Muse export, SNOMED in `drugs_v2.json`, the SHA remap) | **Planned, Tue 3 Nov, before anything goes public.** The SNOMED call and the publish method are Ahmed's. |
| 3 | `CLAUDE.md` still says "synthetic data only" | **Ahmed's decision**, already on his list. Patient data stays synthetic. Public pack photos are used under `docs/DATA_HANDLING.md`. |
| 4 | `OpenWeightLabelReader` checks `model` but not `price_key` for `-contributor` | **After the freeze.** It fails closed today, because the price lookup fails before any request. |
| 5 | Run `assert_no_advice` on the formatted photo-request message too | **After the freeze, defense in depth.** The QM finds the invariant holding: every claim reaches the message through `claims.py`'s parser check. |
| 6 | The codes line resolves a pack without its country | **Recorded in batch 24.1's review.** It has no visible effect today, because entries with the same ingredient carry the same codes. |
| 7 | The cross-language input classes the supervisor recorded, the colon clock time, and contradicted salt labels | **To the README's Limitations** (judge-facing session), as `evidence/batches/24/review.md` lists them. |
| 8 | Raw model replies aren't saved; disclose S1's transcription miss | **Disclose it in the README and CLAIMS** (judge-facing session). Saving the raw reply in `intake_live.py` waits until after the freeze. |
| 9 | The README and CLAIMS must report U12's 0 of 10 and how Modal was unblocked | **Judge-facing session,** from `04beb2e` and `evidence/finetune/results.md`. |
| 10 | `LICENSE`, the hosted brief, CLAIMS on main and the final video aren't on main yet | **Per the Mon–Tue schedule.** The licence choice is Ahmed's. |
