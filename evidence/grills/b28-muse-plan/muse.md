muse: workspace root: <repo>/.muse/worktrees/20261031-adc3 (cwd default)
muse: warning: rules file at <repo>/CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
## 1. Verdict on the design

Approve with fixes: gate is narrow and safe, but strength-mismatch and budget/cap interaction are unpinned (`SPEC.md:351`).

## 2. Risks

1. **Second read can override on same-INN, wrong-strength.** SPEC replaces unless INN sets differ (`SPEC.md:353`); contract only pins different-INN conflict (`tests/contract/test_b28_second_reader.py:115`). Fix: also keep-first on strength/country mismatch, add test.
2. **Nameless-first overclaim.** If first names no ingredients, "both name" check passes and any readable second wins (`SPEC.md:353`). Fix: state this is intended or require label containment.
3. **Dollar cap not exercised.** Call budget grows to `2+(len+3×top_k)×photos` (`SPEC.md:358`) but live spend is bounded by SessionGuard/`--session-usd`; no contract test combines second reader with guard. Fix: set/verify session-usd covers extra Fireworks calls.
4. **Explicit-budget starvation.** Explicit `max_provider_calls` stops before second read (`tests/contract/test_b28_second_reader.py:177`). Fix: document callers must raise explicit budgets by `photos×top_k`.
5. **Re-photo still supersedes on persistent abstention.** Any fresh observation supersedes (`anamnesis/review.py:133`); all-abstain keeps `unreadable_source` and re-requestable (`tests/contract/test_b28_second_reader.py:107`). Fix: confirm supersede-then-rerequest loop is intended.
6. **Crop provenance.** Must be first read's `crop_region`, not enlarged (`briefs/28.md:12`), pinned by byte equality (`tests/contract/test_b28_second_reader.py:93`). Fix: crop inside helper from source image as `_zoom` does (`anamnesis/agent/loop.py:93`), keep `cropped=True`.
7. **No-zoom placement untested.** SPEC says "or in its place, when there was no zoom" (`SPEC.md:351`); zoom can return silently at size cap (`anamnesis/agent/loop.py:104`) but order test only covers zoom-then-second (`tests/contract/test_b28_second_reader.py:143`). Fix: add enlarge-None test.
8. **`cropped`/unreadable gaps.** Fake ignores `cropped` (`tests/contract/test_b28_second_reader.py:50`); tests use partial, not unreadable, though both trigger (`SPEC.md:351`). Fix: assert `cropped=True`, add unreadable-first test.

## 3. The implementation plan

1. Add `SECOND_READ` after `ZOOM_READ` (`briefs/28.md:11`).
2. Add `_second_read` beside `_zoom` mirroring region check (`anamnesis/agent/loop.py:114`): region, readability, ingredient checks (`SPEC.md:351`); call per-region after zoom (`tests/contract/test_b28_second_reader.py:143`).
3. Thread `second_reader=None` through `run_intake`, conditional default budget (`briefs/28.md:13`), preserving exact report when None (`tests/contract/test_b28_second_reader.py:155`); keep spend sum (`tests/contract/test_b28_second_reader.py:138`).
4. Thread through `add_photo` with budget `len+3×top_k` only with reader (`briefs/28.md:14`), same step-5b rule (`SPEC.md:529`); verify re-photo test (`tests/contract/test_b28_second_reader.py:186`).
5. Live script: `--second-reader`, `Run.second_client`, Fireworks/low-effort build (`SPEC.md:416`), guards-before-key (`SPEC.md:418`), budget and `runs.jsonl` field (`SPEC.md:419`).
6. Add `tests/unit/test_b28_extra.py` for gaps above, then ruff + pytest (`briefs/28.md:16`).

## 4. Open questions for the CEO

1. Same INN, different strength: replace or keep-first (`SPEC.md:353`)?
2. Should second read fire when zoom was skipped at size cap (`anamnesis/agent/loop.py:104`)?
3. What `--session-usd` covers the extra Fireworks reads (`SPEC.md:358`)?
4. Does the brief timeline need a new rendering for `SECOND_READ` (`SPEC.md:356`)?
5. Is supersede-on-still-partial re-photo intended (`anamnesis/review.py:133`)?

