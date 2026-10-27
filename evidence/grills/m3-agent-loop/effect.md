# Milestone 3: the bounded agent loop (batch 14)

Batch 14 turns the M2 open items into a working loop: F-06 (crop-zoom provenance), F-07 (session caps, Arabic regression words), F-09 (the `ReconciliationReport` bundle) and M1 #10 (referential checks), plus QM3 #2–#4.

| Source | Item | Status |
|---|---|---|
| M2 F-06 | Crop-zoom never re-runs SAM, and keeps the source region id and hash | **Applied** in batch 14 (contract: `test_concept_fallback_then_crop_zoom…`, `test_crop_refuses…`) |
| M2 F-07 | Session $ and call caps, no outer retry, Arabic regression words | **Applied** in batch 14 (`SessionGuard`, `IntakeSession`); reviewer fix: a spend cap ends the session |
| M2 F-09 | One report artifact | **Applied**: `ReconciliationReport` |
| M1 #10 | Referential checks on the whole intake | **Applied**: report validator |
| QM3 #2–#4 | Literal or nominal EU strength; separated salt words; country passed to brand facts | **Applied** in batch 14 |
| M2 F-09 | Open-weight benchmark (Baseten Spark Open) | **Open:** next batch |

The M3 grill (Muse + Astra) has not run yet. This QM round reviews the milestone package before the first live run of the loop, as Ahmed asked.

## Quality manager, round 1 (`qm.md`): VERDICT HOLD
**No live run of the loop until the blocker (#1) is fixed.**

| QM # | Finding | Verdict | Where |
|---|---|---|---|
| 1 | **Blocker:** when a call fails after an earlier attempt was charged, the report's `spend_usd` and `call_ids` miss it. The ledger is still right; the report under-reports | **Accepted:** a failed `ProviderError` carries `prior_call_ids` and `prior_cost_usd`, and the loop adds them to the report and the step | B15 |
| 2 | Pairing can give a conflicted candidate the top score (3) | **Accepted:** extraction-conflicted pairs score at most 1 | B15 |
| 3 | `mentions_moiety` misses joined and clitic brand forms ("BelocZok succinate", وبيلوكزوك) | **Accepted:** reuse the same matcher as `_matches` | B15 |
| 4 | `_basis_amount` lets a **strength** comparison accept 0.5×/2×… against the literal EU amount | **Accepted (my brief was wrong):** a stated tablet strength must equal the literal or the nominal amount; multiples only apply to intakes | B15 |
| 5 | QM package lacked the loop, report and spend code | **Fixed now** (`qm.sh`) | done |
| 6 | Crop margin wording contradicts itself (SPEC "+10%" vs brief "5% per side") | **Fixed now:** SPEC says 5% of the box per side, 10% in total | done |
| 7 | Reviewer-added B14 behaviours aren't in the contract; run the M3 grill after the live run | **Accepted:** both are promoted to the B15 contract; the M3 grill runs after the live loop run | B15, then M3 grill |
| 8 | All 5 safety invariants hold (report spend at risk per #1) | Noted | — |

## Quality manager, round 2 (after batch 15): **VERDICT PASS**
The HOLD is lifted. **The first live run of the agent loop** followed (below).

| QM2 # | Finding | Verdict | Where |
|---|---|---|---|
| 1 | Call counting: `IntakeSession` counts logical calls, while `SessionGuard` counts attempts (a retry is 2); a crop failure after `budget_exhausted` can append a step | Accepted: SPEC §4 states both counters (logical-call budget vs billed-attempt cap); the step-after-exhaustion case is fixed next batch | SPEC now; B16 |
| 2 | The #4 contract test proves nothing; only a unit probe pins the rule | Accepted: promote the direct `_strength_type` probe to the B16 contract | B16 |
| 3 | An Arabic clitic attached to a Latin brand ("الBeloc-Zok succinate") in `mentions_moiety` isn't pinned | Accepted (minor) | B16 |
| 4 | Record Ahmed's decision on F-09 (open-weight benchmark) | **Done:** cut (Ahmed accepted the supervisor plan, 27 Oct); see `decisions.md` | done |
| 5 | Change the narrowed `match` template and SPEC together in B16 | Accepted | B16 |
| 6 | Put `supervisor.md` in the QM package | **Done** (`qm.sh` includes batch supervisor files) | done |
| 7 | The first-live-run ledger figure in `decisions.md` is ambiguous | **Done:** clarified in `decisions.md` | done |

## First live run of the agent loop (27 Oct, after QM PASS)
- Two intakes (English, Arabic) through `scripts/intake_live.py`, each behind a `SessionGuard` ($0.25, 12 calls). Each took **6 provider calls, about $0.027**: transcribe → extract claims → SAM "medicine box" (0 regions) → SAM "label" (2) → 2 reads → reconcile.
- **Both reports are correct:** Concor `match`; metoprolol 50 mg twice a day vs Beloc-Zok 100 mg `intake_differs_from_unit_strength`; Panadol (stopped) `missing_modality`. The report spend equals the ledger. Reports: `evidence/live/2026-10-27/report_{en,ar}.json`.
- Crop-zoom did **not** trigger: both labels were readable on the synthetic photo. Showing it working needs a hard real photo (B17).
