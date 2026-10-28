# M6 check, round 2 (Gemini 4 Argon on Vertex), batches 22–23: triage

- **The run:** 28 Oct, `QM_VIA=vertex scripts/qm.sh m6-timeline-r2 22 23`, 159,495 input tokens, $0.32984 est. on the Google credit; the spend gate passed it first.
- **Verdict:** HOLD (`qm.md`). It ran in parallel with the supervisor's round 2 review.
- **Triage by the CEO:**

| # | Finding | Decision |
|---|---|---|
| 1 | blocker: `evidence/batches/22/comparison.md` isn't in the package | **Branch timing, not a defect.** The batch 23 branch was cut (87e323d) before the comparison was committed on main (fa377d1). Main is merged into the branch before the final check and the merge |
| 2 | blocker: no round 2 supervisor report, review or merge | **Process.** The supervisor's round 2 review is in `supervisor.md` (CHANGES); round 3 follows |
| 3 | major: no open-weight or 39-photo calls in `ledger.jsonl` | **The same branch timing.** Main's ledger holds them (fa377d1). The spend gate now reads every worktree's ledgers (461caa1) |
| 4 | minor: a bracket without a spoon word (`250 mg per (5 ml)`) is kept | **Accepted, round 3** (Muse and the supervisor found it too) |
| 5 | minor: a decimal-comma volume, `mL`, `ملي` | **Already handled; pinned in round 3.** A comma is a decimal mark in volumes (`2,5 ml`), and matching ignores case. `ملي` reads as `مل`, because it isn't followed by `جم` or `غ` |
| 6 | minor: the timeline total cell has no `colspan` | **Accepted, round 3** |
| 7 | minor: the README contradicts the SPEC | **Passed on** to the judge-facing session's draft (merged on Tue) |
| 8 | minor: the safety invariants hold | **Noted.** The M1 export is removed in Tuesday's filtered copy |
| 9 | minor: deliverables still to come | **Deferred to their dates** in the plan |
