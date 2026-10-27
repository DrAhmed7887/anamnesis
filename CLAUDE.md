# Anamnesis: project instructions

Claude Code is the **only orchestrator** in this repo (Meta Global AI Developer Hackathon, deadline Thu 5 Nov 03:00 CET). Other agents (Antigravity, Muse, Astra) review or suggest. They don't write to build paths.

## Pipeline
- **Claude Code** writes `SPEC.md`, the briefs and the contract tests, runs the scripts, reviews every diff, merges, and keeps `evidence/`.
- **codex** builds: Luna for mechanical work, Sol for logic. It doesn't touch `tests/contract/`; the gate rejects any batch that does.
- Commands:
  ```bash
  scripts/batch.sh start <n> <slug>   # branch batch/<n>-<slug>; then commit "test(contract): batch <n>" + briefs/<n>.md
  scripts/batch.sh run <n> <luna|sol> # builder + gate (ruff, pytest, contract lock) → evidence/batches/<n>/
  scripts/batch.sh gate <n>           # rerun the gate after a fix
  scripts/batch.sh merge <n>          # needs "Verdict: PASS" in evidence/batches/<n>/review.md
  scripts/grill.sh <milestone>        # Muse Code + Astra on evidence/grills/<milestone>/brief.md → effect.md triage
  ```
- **Evidence for judges:** every batch has a brief, the builder's report, a gate result and a review. Every milestone has its grills and an `effect.md` table (finding → verdict → commit). Decisions go in `evidence/decisions.md`.

## Privacy and data
- Synthetic data only. No patient data ever goes to any model.
- `muse exec` always runs with `--model muse-spark-1.3 --no-foreign-personal-context`. **Never use a `*-contributor` model**, because Meta may train on what we send.
- Raw tool logs go to `evidence/raw/`, which is git-ignored. Commit only summaries, and check exports for personal content first. The repo goes public at submission.

## Money
- The Meta credit is $150, and there is no hard cap on Meta's side. Billing and alerts are at `dev.meta.ai/billing`.
- `SpendGuard` (batch 4) records every live call in a ledger and refuses before the cap is crossed. Prices come from `docs/muse/`, never from memory.
- Tests run offline with fixture adapters and cost $0.

## Scope decisions (see `evidence/decisions.md`)
- Barcode/DataMatrix: deferred to day 5+.
- Literature citations: none go in the submission unless verified against the source.
- ICU or renal dosing cases: rejected (inpatient dosing advice).
- Anamnesis reports where sources disagree. It **never** gives medical advice. All text comes from `anamnesis/schema/templates.py`.
