# Batch 26.1 review: the Fireworks label reader asks for low reasoning effort (SPEC §4)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 1 round, planned first by a read-only Muse session and audited by a fresh one

**What the batch changes:**
- **The option:** `OpenWeightLabelReader` gains an optional `reasoning_effort`.
  - None, the default, sends batch 22's request unchanged.
  - One of `low`, `medium`, `high` and `xhigh` adds only that field.
  - Anything else raises `ValueError` before any call.
- **The live script:** `--reader fireworks` asks for `low`, the effort Spark 1.3's own reader asks for. Baseten stays at None.

**Why:** Ahmed said yes to a batch 26.1 for the Fireworks column.
- **Not the timeout:** the CEO's diagnosis found the timeout wasn't the cause. With a 180 s limit, Fireworks itself dropped a request at about 62 s.
- **The cause:** the reader sent no reasoning effort, so Spark Open reasoned at its default, `xhigh` (`docs/muse/muse-spark-open.md`).
- **The test:** at `low`, three diagnostic reads took 16–24 s, and all three were correct.

**Who did what:**
- **Muse planned first** (`evidence/grills/b261-muse-plan/`, $0.18): "Accept", with 7 risks, all handled in the contract.
- **The CEO** wrote the SPEC paragraph, the contract and the brief (a00f4be).
  - The reference build passed 16 contract tests (2,506 in all).
  - It caught 6 of 6 mutants.
- **Muse wrote the code** in one round ($0.54): the option, its validation, the live script's wiring, and 13 unit tests.
- **Reviews:**
  - **The Opus supervisor approved** (`supervisor.md`): the request is unchanged under None, the comparison path is unchanged, and Muse's tests catch two breaking edits the contract misses.
  - **A fresh Muse audit passed it** (`evidence/grills/b261-muse-audit/`, $0.21).

**The gate:** pass, 2,519 tests, ruff clean, contract untouched since a00f4be (`gate.json`).

**Found, not fixed here:** validation compares by equality (supervisor, low), and the run log doesn't record the effort (info).

**Cost:** Muse $0.93 in all: plan $0.18, round 1 $0.54, audit $0.21. The round is in `evidence/spend/muse_ledger.jsonl`; the grills are in neither ledger.

Verdict: PASS
