# Batch 1 review: domain schemas

Reviewer: Claude Code (Opus 5.5). Builder: codex `gpt-6-luna`, 35,883 tokens. Gate: pass, 41 tests.

Verdict: PASS

## Checked against SPEC.md §1–3
- `AudioTurn`: `end_ms > start_ms ≥ 0`. Turn-level timing only. ✅
- `ImageRegion`: inclusive source-pixel corners with `x2 < frame_w`, a 64-character lowercase hex hash, and `confidence` in [0,1]. ✅
- Every model has `extra="forbid"`, and amounts are `Decimal`. ✅
- `Strength` requires at least one ingredient, so combinations work. `intake_amount` is kept separate from `strength`. ✅
- `Finding`: the evidence-side rules match the §3 table exactly, and every non-match type requires review. ✅
- No recursive schemas, no network calls, no new dependencies. ✅

## Notes (not blocking)
- `NonEmptyStr` is defined in three modules. Move it into one shared module when batch 2 touches the schemas.
- `PatientClaim.name_text` accepts an empty string. Harmless for now, because the reconciler treats it as unresolved.

## Process finding
The `~/.codex/AGENTS.md` session-continuity rule made the builder read `RECENT.md` and `~/.claude/CLAUDE.md`. That text went to the model provider and into the raw log. Fixes:
- Raw logs now go to the git-ignored `evidence/raw/`. Only the builder's final report is committed, as `codex.md`.
- `briefs/_worker_preamble.md` now tells the builder to skip those steps.
