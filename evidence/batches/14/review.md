# Batch 14 review: the bounded agent loop, crop-zoom provenance, session caps, report bundle (+ QM3 #2–#4)

Built-by: Claude Sonnet subagent (Claude Code) + Claude Code reviewer fixes (spend-cap stop, zoom provenance check)

Reviewer: Claude Code (Opus 5.5). Gate (run by the reviewer): pass, 400 tests (398 from the builder plus 2 regression tests from the reviewer). The contract lock held.

Verdict: PASS

## Checked
- **Deterministic loop** (`agent/loop.py`, 116 lines): transcribe → extract claims → for each image, segment with concept fallback → read the top-k regions → one crop-zoom per unreadable or partial reading → reconcile. No model chooses actions. Model prose is never surfaced; step outcomes carry the error class only. ✅
- **Provenance (F-06):** SAM only ever sees the source photo. `crop_region` refuses bytes whose hash or frame size don't match the region, and pads 5% per side, clamped. The zoom call passes the **source** region. ✅
- **Budgets:** `IntakeSession` counts every provider call and stops with one `budget_exhausted` step. `SessionGuard` adds per-session $ and call caps in front of the parent ledger, and every charge reaches the parent. ✅
- **`ReconciliationReport`** (F-09): one artifact with turns, claims, regions, packs, findings, steps, calls and spend. The referential checks (M1 #10) cover every reference. ✅
- **QM3 #2** (literal or nominal EU strength), **#3** (salt words apart from the moiety or next to a brand), **#4** (country passed through to brand-implied facts): all pinned and passing. ✅
- Sonnet's 11 interpretation notes were reviewed. All are reasonable except #10, fixed below.

## Reviewer fixes (on this branch, test-first)
1. **A spend-cap refusal now ends the session.** Before, the loop caught `SpendCapExceeded` and moved on, so every remaining call was attempted and refused one by one. Nothing was spent, but it was noisy and wrong. Regression test: `test_reviewer_spend_cap_ends_the_session_instead_of_retrying_every_call`.
2. **A zoomed reading must carry the source `region_id`**, otherwise it is discarded and logged. This is defence in depth: the live reader already does this. Test: `test_reviewer_zoom_reading_with_a_foreign_region_id_is_rejected`.
3. Removed a stray `Decimal` from `loop.__all__`.

## Note
- `core/reconcile.py` is now about 370 lines, over the ~300 guideline. Split it (identity, salts, rules) in a later refactor batch with no behaviour change.
