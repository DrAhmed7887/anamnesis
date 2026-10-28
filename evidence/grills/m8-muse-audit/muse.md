muse audit m8 started 21:15:21
muse: workspace root: .muse/worktrees/20261028-1518 (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
# Anamnesis pre-freeze audit

## 1. Goal

The audit is done ONLY when your reply has all six sections below, every finding cites a file and line you opened in this session, and no finding repeats one already recorded in an `evidence/grills/*/effect.md`.

## 2. Plan

As first written, before opening any code:

1. Read every `evidence/grills/*/effect.md` (m7-pre-freeze first) to build known-findings exclusion list; done when all effect.md listed and read.
2. Trace `scripts/intake_live.py` end to end for untested demo path (real voice, multi-photo, unreadable+re-photo, timeouts/budget/Arabic/pairing); done when each branch and limit checked.
3. Compare SPEC.md rules against `tests/contract/` and `anamnesis/` code; done when each spec rule mapped to test/code or recorded as gap.
4. Safety: templates, spend ledger, `*-contributor` refusal, photo routing vs DATA_HANDLING; done when each of 4 sub-checks traced to code.
5. Judge view: git show judge/claims-video README + CLAIMS vs repo; done when missing-by-Saturday items listed.
6. Run offline tests/ruff only if .venv exists; done when run or confirmed missing.
7. Write six-section reply with ≤12 new findings, each with opened file:line.

No plan changes.

## 3. Steps

- Listed 15 `effect.md` files via search; read all 15 (m7-pre-freeze first): built exclusion list of ~120 recorded decisions.
- Read `scripts/intake_live.py`: budget formula, baseten gate, TimedClient, per-run outputs; learned demo entry points.
- Read `anamnesis/review.py`: requestable/request/add_photo/approve match SPEC §8; add_photo has no live script caller.
- Read `SPEC.md` (v3.7), `templates.py`, `spend.py`, `DATA_HANDLING.md`, `agent/loop.py`: baseline for spec-vs-code and safety checks.
- Read `agent/session.py`, `providers/meta.py`, `providers/base.py`, `providers/claims.py`, `brief.py`: all 5 adapter call sites charge; retry wrapper carries prior charges.
- Read `brief_html.py`, `providers/openweight.py`, `core/guardrails.py`, `core/reconcile.py`, `core/catalogue.py`: brief text is templates + escaped source; pairing global across photos.
- Read `providers/voice.py`, `sam.py`, `spark.py`, `stated.py`, `core/overlap.py`: parsers fail closed; mixed-digit runs die in Decimal as SPEC requires.
- Read `providers/numbers.py`, `agent/media.py`, `agent/crop.py`, `schema/report.py`, `schema/review.py`: photo hygiene code-level; audio has no equivalent.
- Read `schema/findings.py`, `medication.py`, `evidence.py`, `README.md`, `catalogue.yaml`: template enforcement via validators; main README stale as recorded.
- Listed 40 contract test files; searched scripts for contributor/live-call sites: zoom/smoke are Meta-only; baseten gated in intake_live and reader_eval.
- Read `scripts/reader_eval.py`: gate code matches intake_live (M7 #6 fixed); docstring line 10 still claims wider allowance.
- Ran `git show judge/claims-video:README.md` (head + tail) and `docs/CLAIMS.md` (head): all pending rows already have owners/dates.
- Read `evidence/batches/21/manifest.md`: R3 note cites retired =12 budget; R6 note contradicts SPEC dropped-units rule; no multi-photo case staged.
- Read `scripts/zoom_live.py`, `scripts/smoke_live.py`: SessionGuard/SpendGuard wired, Meta-only, no data-rule issue.
- Read `scripts/batch.sh`: contract/conftest/pyproject locks present as recorded; contributor refused.
- Probed `.venv/bin/python -m pytest -q` and ruff: both missing, so read code instead per rules.

## 4. Findings

| # | severity | area | evidence | what is missing or wrong | the smallest fix |
|---|---|---|---|---|---|
| 1 | minor | 1 | `scripts/intake_live.py:146`, `anamnesis/providers/sam.py:59-60`, `anamnesis/agent/loop.py:75`; input `--top-k -1` | Negative `--top-k` passes argparse, then `top_regions` raises mid-run after transcribe/claims/segment spend; no report or brief is written | Validate `top_k >= 0` in argparse or at `run_intake` entry before any call |
| 2 | minor | 1 | `evidence/batches/21/manifest.md:36` vs `SPEC.md:26`, `anamnesis/providers/claims.py:219-227` | R6 note says a dropped units range gives `match`; SPEC and code null strength+intake on dropped units, so rule 9 gives `insufficient_information` | Correct the R6 note: dropped range → `insufficient_information`, a miss |
| 3 | minor | 1 | `evidence/batches/21/manifest.md:31` vs `SPEC.md:205`, `anamnesis/agent/loop.py:135-136` | R3 note says watch `max_provider_calls=12`; batch 23 made the default dynamic (`2+(3+6)×photos`) | Update the R3 note to the dynamic budget before finalizing the manifest |
| 4 | minor | 1 | `evidence/batches/21/manifest.md:27-37` | No staged case runs ≥2 photos through one intake; multi-photo pairing, budget and coverage paths first run on demo day (closest is R2's sequential `add_photo`) | Add one two-photo case (e.g. R3 photo + one more) to the manifest before recording |
| 5 | minor | 2 | `scripts/reader_eval.py:10` vs `:40-41`, `:68-72` | Docstring still says photos outside `media/public/` + `media/real-public/` are refused, implying DailyMed may go to Fireworks/Baseten; code correctly refuses it since M7 #6 | Reword line 10 to name the three allowed folders |
| 6 | minor | 2 | `anamnesis/providers/spark.py:171-176` vs `SPEC.md:28` | SPEC says country is kept only as an ISO 3166-1 alpha-2 code; code keeps any two ASCII letters (`XX` passes) | Validate against the ISO list (or catalogue countries); else null |
| 7 | minor | 3 | `anamnesis/providers/meta.py:176-193`, `anamnesis/agent/loop.py:140-145`, `docs/DATA_HANDLING.md:24` vs `anamnesis/agent/media.py:35` | Photos are stripped of metadata in code, but voice bytes go to Transcribe and into the brief as-is; metadata removal relies solely on the operator's ffmpeg step | Re-encode the WAV through PCM frames (or reject files with extra chunks) in `intake_live.py` or the transcriber |

## 5. Checked and fine

- Real-voice failure modes: timeout/length-stop/oversize audio all fail safe to error steps with no claims; the 30 s claim-call risk and R7 latency measurement are already on the plan.
- Re-photo path: `add_photo` refuses wrong-report/closed/duplicate media, never supersedes without fresh observations, and counts requests answered whatever the photo shows, per SPEC §8.
- Spend: all five adapter call sites charge after success, `with_one_retry` charges uncertain failures at estimate, length stops carry real usage; no uncharged model call found.
- Contributor refusal: enforced in three reader constructors, `ProviderTrace`, `AgentStep`, `SpendGuard.charge_estimate`, and `batch.sh`; voice/SAM ids are fixed constants.
- Photo routing: both Baseten paths resolve symlinks before the allowlist check; zoom/smoke scripts are Meta-only; no staged Ahmed photo can reach Fireworks/Baseten.
- Brief and patient text: all added sentences come from `templates.py`; source data is escaped; step outcomes use the fixed `error: <provider> <ExceptionName>` vocabulary with no message text.
- Pairing and budget across photos: pairing is global and order-independent by id; the loop budget scales per photo with a session dollar cap in front.
- Judge branch: every pending row (pause live, hero N/10, Ahmed's cases/voice, cross-country brand, hosted brief, LICENSE, video) already has an owner and date; nothing further is showable by Saturday that the plan doesn't cover.
- Build gates: contract/conftest/pyproject locks and the skip/xfail fail are in `batch.sh` as recorded; no `conftest.py` exists under tests.

## 6. How you reached the goal

The plan held with no changes and no dropped steps. I could not run the test suite or ruff (no `.venv`, and installs were forbidden), so I verified by reading code; I could not open `evidence/raw/` or anything outside the repo, so live-run artifacts and pre-freeze media claims are unverified from text evidence only; I made no live or network calls, so timeout, Arabic human-voice, and multi-photo behavior is traced, not executed; and I read only the head of the judge-branch claims table, relying on the README draft's pending-items comment plus grill records for the rest. The remaining risk is the one the plan already names: today's `main` has never run end to end live, which Wednesday's scheduled runs address.

AUDIT: 7 findings (0 blockers, 0 majors)

