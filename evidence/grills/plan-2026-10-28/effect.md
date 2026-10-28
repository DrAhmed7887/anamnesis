# Grill of the plan to submission, 28 Oct 2026: triage

An independent Opus subagent grilled the plan approved just after midnight (`evidence/decisions.md`, 2026-10-28). It worked read-only. It was given the plan and the evidence, but not the CEO's view of it.

The full report stays in `evidence/raw/` (git-ignored), because it quotes a personal schedule and names from a personal skill catalog.

**What the CEO checked before triage.** These claims all hold:
- The last live adapter call was on 27 Oct at 13:31 UTC, before batch 16 (`evidence/spend/ledger.jsonl`).
- `scripts/batch.sh merge` runs `git switch main`, which fails inside a worktree.
- README line 15 says "all code".
- The 27 Oct supervisor's item 7 still stands.
- In batch 20 the lint ignore was widened and then reverted.
- There is no LICENSE file.

**The personal skill catalog.** The committed M1 Muse export carries Ahmed's personal skill catalog, and so does every raw Muse export from batches 16–20. The catalog includes skills from work outside this project. They load from `~/.agents/skills`, which `--no-foreign-personal-context` does not cover.

The verdicts below are the CEO's. The revised plan waits for Ahmed's yes.

| # | Finding | Verdict | Where |
|---|---|---|---|
| 1 | The video, the artifact judges see, gets one pass, at the end | **Accepted** | A judge-facing session starts Wed. Rough cut v0 Sat, final cut Tue |
| 2 | The real media come Thu with no slot to fix what they break. Today's `main` has never run end to end live | **Accepted** | Wed night: the pre-registered real cases plus the two synthetic notes run live on `main` (≤ $0.35). The synthetic rerun is QM M4 #6, which the plan had dropped. Fixes go into batch 21's round 2, and Fri is a second fix slot |
| 3 | Going public would publish a committed Muse export that holds a personal skill catalog. Every Muse run still sends that catalog to Meta | **Accepted, blocker for going public** | Before batch 21 runs: disable those skills in Muse (needs Ahmed's yes). Tue: the public repo is a filtered copy without that file, with the commit email mapped to GitHub's noreply address |
| 4 | Two CEO sessions with no working channel. Each worktree has its own ledger, merge can't run in a worktree, and there is one rate limit per team | **Accepted** | One engine session runs Muse, the live calls, the ledger and merges, from the main checkout. One judge-facing session works on files only. Session B retires, and the engine restarts fresh after batch 21 |
| 5 | The cut order drops work judges can see first | **Accepted** | Cut the `run_intake` refactor, the follow-ups on Unicode breaks and Arabic advice forms, and the M5 Muse grill. The QM stays. Batch 22 is the timeline only |
| 6 | The synthetic scorecard grades its own work, and its answer keys aren't truly held out | **Accepted** | Replaced by pre-registered real cases, whose expected results are committed before any run, and the hero's N/10. Every miss is reported |
| 7 | The deadline and the form fields aren't verified | **Accepted** | Ahmed checks the guide on Wed, then CLAUDE.md is made to match it |
| 8 | No claims check, and the README overclaims "all code" | **Accepted** | A claims table (claim → file:line) before the voiceover. README line 15 becomes "all product code in `anamnesis/`" |
| 9 | The video production chain isn't specified (Playwright records no sound) | **Accepted** | Fri: a 20-second test render through the exact chain |
| 10 | The agentic track contradicts the supervisor's accepted item 7 | **Accepted, with framing** | Keep the track only if the photo-request pause and resume is on screen, shown as human-in-the-loop. Never "autonomous" |
| 11 | Claude Code access is a single point of failure | **Accepted** | Write HANDOFF.md and do one gate run through a fallback tool. |
| 12 | Ahmed's hours are undercounted | **Accepted** | About 8–9 h after the cuts |
| 13 | Muse at work is never filmed | **Accepted** | Screen-record batch 21's Muse run |
| 14 | The gate locks only `tests/contract` | **Accepted** | Also lock pyproject's `[tool.*]` sections and every `conftest.py`, and fail when a contract test is skipped. Tag `demo-freeze` on Sat |
| 15 | Gaps in the media list | **Accepted** | Commit the V1–V3 scripts and a skeleton manifest before recording. Add an unreadable shot and its re-photo |
| 16 | No LICENSE, the key comes only from the Keychain, and local paths appear in logs | **Accepted** | Tue |
| 17 | The reasons for the open-weight cut are partly stale | **Noted** | It stays cut. Reopen only if the hero is green on Thu night, and only by Ahmed's call |
