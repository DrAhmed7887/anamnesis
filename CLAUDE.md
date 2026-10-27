# Anamnesis: project instructions

Antigravity (on Ahmed's personal account) is the **orchestrator** in this repo (Meta Global AI Developer Hackathon, target submission Wed 4 Nov 20:00 CET, deadline Thu 5 Nov 03:00 CET).

## Pipeline (from batch 16, 27 Oct 2026)
- **Antigravity** orchestrates: it writes `SPEC.md`, the briefs and the contract tests, runs the gate, reviews each batch against `evidence/grills/BATCH_SUPERVISOR_PROMPT.md` (`evidence/batches/<n>/supervisor.md` and `review.md`), and merges.
- **Muse Code (`muse-spark-1.3`)** builds each batch from the repo root with `muse exec --model muse-spark-1.3 --no-foreign-personal-context`, and never uses a `*-contributor` model. It doesn't touch `tests/contract/`; the gate rejects any batch that does. Its spend is outside the ledger and is logged per run in `evidence/decisions.md`.
- **Gemini 4 Argon (Medium) via `agy`** stays the quality manager (`scripts/qm.sh`).
- This project no longer uses Codex (built batches 1–12, with GPT-6 Astra grills) or Claude Code (built batches 13–15.5).
- Commands:
  ```bash
  scripts/batch.sh start <n> <slug>   # branch batch/<n>-<slug>; then commit "test(contract): batch <n>" + briefs/<n>.md
  scripts/batch.sh run <n>            # Muse Code builder (muse-spark-1.3) + gate (ruff, pytest, contract lock) → evidence/batches/<n>/
  scripts/batch.sh gate <n>           # rerun the gate after a fix
  scripts/batch.sh merge <n>          # needs "Verdict: PASS" in evidence/batches/<n>/review.md
  scripts/grill.sh <milestone>        # Muse Code on evidence/grills/<milestone>/brief.md → effect.md triage
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

## Quality manager (every milestone)
- After each milestone's grill and triage, run `scripts/qm.sh <milestone> <first-batch> <last-batch>`. Gemini 4 Argon (Medium), via `agy`, audits the **process and the evidence**, not the code: traceability, contract adequacy, gate integrity, spec/code consistency, safety invariants, honest claims and deadline risk. The prompt is `evidence/grills/QM_PROMPT.md`.
- `VERDICT: HOLD` blocks the next milestone until its blocker is fixed. Every QM finding gets a verdict row in that milestone's `effect.md`.
- To run it by hand: paste `evidence/raw/<milestone>-qm-package.md` into Antigravity with Gemini 4 Argon (Medium).
