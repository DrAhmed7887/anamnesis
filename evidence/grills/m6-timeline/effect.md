# M6 check (Gemini 4 Argon on Vertex), batch 23 round 1: triage

- **The run:** 28 Oct, 12:30 UTC, `QM_VIA=vertex scripts/qm.sh m6-timeline 23 23`. The package was 412 KB with every module, at $0.28843 est. on the Google credit; the spend gate passed it first.
- **Verdict:** HOLD (`qm.md`). It ran in parallel with the Opus supervisor on the same round 1 build, so both feed one fix round.
- **Triage by the CEO:**

| # | Finding | Decision |
|---|---|---|
| 1 | blocker: no supervisor report, review or merge for batch 23 yet | **Not a defect.** The check ran before the merge on purpose. The supervisor reviewed in parallel, CHANGES (`evidence/batches/23/supervisor.md`), and the merge follows round 2 |
| 2 | blocker: batch 22's comparison and batch 21's live records weren't in the package | **Accepted as tooling.** The range was batch 23 only, but batch 23's SPEC lines cite `evidence/batches/22/comparison.md`. The next check of this batch runs on batches 22–23 |
| 3 | major: the volume rule misses the Arabic decimal sign and IU; pin a volume with no number | **Accepted, round 2.** The supervisor found the decimal sign too (its #1). The rule now reads `٫`, IU, `unit(s)` and `وحدة`. "250 mg / ml" and "50 mg/ml" are pinned as kept |
| 4 | major: pin where the rule stops (a pack size, a dosing volume) | **Accepted, round 2.** "5 mg/ml, 5 ml bottle", "100 mg tablets, 100 ml" and "dissolve in 100 ml of water" are pinned as kept |
| 5 | minor: a retry whose second attempt leaves no trace shows no model | **No change.** SPEC §4 says the model comes from the error's `attempt_trace` when it has one, and the cost always counts. The supervisor confirmed the row shows "—" with the cost |
| 6 | minor: `add_photo` uses two concepts | **Accepted, round 2.** The supervisor (its #4) and Muse found it too. Both paths now share `SAM_CONCEPTS` |
| 7 | minor: the README contradicts the SPEC | **Passed on.** The README is the judge-facing session's draft, merged on Tue |
| 8 | minor: safety invariants hold; the project `CLAUDE.md` still says "Synthetic data only" | **For Ahmed.** That line is his rule text. The public photos of real packs follow `docs/DATA_HANDLING.md`, and the CEO doesn't rewrite `CLAUDE.md` |
| 9 | minor: `LICENSE`, the hosted brief, the hero runs and the claims table are still to come | **Deferred to their dates** in the plan |
