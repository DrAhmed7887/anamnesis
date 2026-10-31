muse: workspace root: <repo>/.muse/worktrees/20261031-b11a (cwd default)
muse: warning: rules file at <repo>/CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
## 1. Verdict

Build follows SPEC §4 step 5b on the contract's paths, but lets a readable second reading erase first-read evidence the contract never exercises.

## 2. Findings

1. **Severity: medium. Readable second that names nothing replaces a naming first.** Diff `loop.py::_second_read` only conflicts when *both* sides name ingredients (`SPEC.md:353`), and only compares strengths when *both* have one. A `READABLE` second needs only `label_text` ([spark.py](<repo>/.muse/worktrees/20261031-b11a/anamnesis/providers/spark.py:137)), so a second with `inn=None, strength=None` replaces a partial first with `inn`/strength; same for first-with-strength vs second inn-only (amount lost). The pack flips from `unreadable_source` (re-requestable, [review.py](<repo>/.muse/worktrees/20261031-b11a/anamnesis/review.py:37)) to a readable observation with no identity. Contract's readable seconds always name ingredients. Fix: when the first names ingredients and the readable second names none (or drops the strength), keep the first and log `conflict: kept the first reading`.

2. **Severity: low. `per` ignored in agreement, so tablet↔ml swaps replace.** Diff `_strength_key` is `(inn, amount, unit)` only, per `SPEC.md:353`. First partial 250 mg per tablet + second readable 250 mg per ml agree and replace, yet reconciler branches on `per` ([SPEC.md](<repo>/.muse/worktrees/20261031-b11a/SPEC.md:302)). Untested. Fix: include `per` in the key (conflict on differ), or keep first on `per` mismatch.

3. **Severity: low. Conflict/wrong-region logs two `second_read` steps.** `session.call` always notes one step ([session.py](<repo>/.muse/worktrees/20261031-b11a/anamnesis/agent/session.py:77)), then the diff `session.note`s `conflict...` / `error: reading for another region`; SPEC says "a `second_read` step ..." ([SPEC.md](<repo>/.muse/worktrees/20261031-b11a/SPEC.md:352)). Timeline shows a phantom `readable` row; tests only assert `[-1]`. Fix: emit a single step for the rejected second read (zoom has the same shape at [loop.py](<repo>/.muse/worktrees/20261031-b11a/anamnesis/agent/loop.py:114); keep both consistent).

## 3. What you checked and found fine

No-reader path returns early with identical budget/steps; default budgets add `top_k`/photo in loop, re-photo and live script; explicit budget untouched; crop is `crop_region` un-enlarged with `cropped=True`; zoom→second-read stays per-region in order; wrong-region and unreadable/partial seconds keep the first; re-photo supersedes only with ≥1 observation; timeline renders the new action generically; `--second-reader` guards (`--case`, `--reader spark`, public photos) run before any key/client read and reuse the Fireworks wording.
