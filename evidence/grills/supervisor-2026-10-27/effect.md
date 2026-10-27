# Supervisor review (GPT-6 Astra, 27 Oct 2026): triage

One Astra message, run at Ahmed's request before batch 15. Prompt: `evidence/grills/SUPERVISOR_PROMPT.md`. Package: spec, decisions, all triage tables, batch log, loop/report code, the real Arabic live output. Its job was the blind spot shared by every other reviewer (Muse, Astra grills, Gemini QM, Claude Code).

| # | Missing item | Verdict | Plan |
|---|---|---|---|
| 1 | **A clinician-readable brief.** Findings are IDs plus generic text; a clinician must rebuild the case. Show "patient: 50 mg twice daily \| pack: 100 mg per tablet" side by side, with the image region and the audio turn | **Accepted, top priority** | B16: a local, printable HTML brief. Disagreements first; source values side by side; image overlay plus a turn-level audio link; missing sources labelled. The `match` template narrows to "The compared identity and strength details agree" |
| 2 | **Cross-medication overlap.** The showcase patient reports Concor (bisoprolol) **and** Beloc-Zok (metoprolol) as current: two beta-blockers. Every reviewer checked pairs only | **Accepted. The biggest clinical miss so far** | B16: a templated, non-advisory cross-medication observation ("two medicines reported as current belong to the same curated class; concurrent use is unconfirmed") from a tiny explicit class map, plus the same INN across different products. Repeated photos never imply duplicate use |
| 3 | Packs can't confirm frequency, timing, PRN use or adherence; there's no prescribed-list comparator | **Accepted as scope honesty** | B16 brief: show regimen and status verbatim, plus a fixed line "Prescribed directions, timing, adherence and supply not assessed". No frequency discrepancy is invented from a pack |
| 4 | "No discrepancy" can look like "everything checked": OTC, herbal and non-tablet products are invisible, and unread regions are silent | **Accepted** | B16: a coverage block (images, readable observations, regions not read, interrupted) plus a fixed intake prompt naming OTC/herbal/non-tablet. Unsupported mentions are kept as unverified entries |
| 5 | Nothing beyond synthetic media: the first real phone photo or rambling note is untested | **Accepted. Needs Ahmed** | B17: 6 staged real-media cases. **Ahmed provides the photos** of real packaging with fictional histories, under the privacy rules in #9. Annotate the expected result first, cap at $1, report honestly as staged tests, not validation |
| 6 | No evidence the brief saves clinician time; low-value prompts (stopped Panadol with no pack) compete with real disagreements | **Accepted. Needs Ahmed** | The brief separates *source disagreements*, *incomplete evidence* and *historical statements* (B16). A usability check with one GP and one pharmacist: **Ahmed recruits them**, or counts as the GP himself and discloses it |
| 7 | The judging story should rest on demonstrated behaviour, not model count. The fixed loop isn't model-directed planning, so don't claim it | **Accepted** | Demo script: the first 20 s exactly as proposed (Arabic/English note + photo → one real disagreement → click to hear the turn and see the region → "reports disagreements; gives no treatment advice"). Show zoom before/after only if it actually helps. Don't chase the agentic bonus |
| 8 | **Over-hardening:** 400 tests but no brief, no real-media trial, no live loop run | **Accepted** | Release gate: from now on, block only on reproduced harmful false agreement, wrong provenance, advice leakage, spend-cap failure, or a failure on the frozen demo path. B15 is time-boxed to 2 h |
| 9 | No privacy boundary for realistic tests (names and pharmacy labels on real boxes; identifying details in voice notes) | **Accepted** | Before B17: a 1-page data-handling note. Fictional, de-identified inputs only; cover or crop dispensing labels; raw media stays out of git and can be deleted locally |

## Revised plan (≈ 20 h focused + 4 h reserve, submit by Wed 4 Nov 20:00 CET)
1. **B15, time-boxed to 2 h:** QM M3 #1 (failed-call spend in the report), #4 (strength vs literal), #2, #3, #7. Then the QM, then the first live loop run.
2. **B16, about 7 h:** the clinician brief (HTML), the cross-medication overlap observation, the coverage block, scope lines, and the narrowed `match` wording.
3. **B17, about 6 h:** data-handling note → 6 staged real-media cases (Ahmed's photos) → fix only demonstrated blockers.
4. **About 3 h:** clinician usability observations (Ahmed arranges them).
5. **About 2 h:** record the 3-minute demo with a replay fallback, package, submit.

## Stop doing (accepted)
- Broad multi-reviewer grills after every change. From now on there's one release review, plus targeted reproduction of genuine blockers. The QM keeps running per milestone, but only blocks on the release-gate classes in #8.
- Expanding salt, alias and formulation coverage without a failure on the frozen cases.
- Treating test counts, batch counts and process tooling as progress.

## Cut, pending Ahmed's decision
- **Open-weight benchmark (Baseten/Modal).** Astra says cut it: hardware, budget and schedule. That gives up the $10K Open Weight bonus. The Baseten $100 credit is already granted, so a *minimal* single-model comparison is possible later if time remains. **Ahmed decides.**
- Barcode/GS1, external drug databases, catalogue expansion, interaction checking, full list reconciliation, supply arithmetic, production features: **cut** (already deferred or out of scope).
