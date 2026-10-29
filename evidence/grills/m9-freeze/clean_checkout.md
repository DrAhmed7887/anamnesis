# The clean-checkout run at `demo-freeze` (30 Oct, 00:40 CET)

- **The clone:** `git clone --depth 1 --branch demo-freeze` from the private GitHub remote. The tag points at 4b32c02.
  - The tree was clean.
  - `uv sync --frozen` installed from the lock file.
  - Ruff passed, and `uv run pytest -q` gave **2,411 passed**.
- **One live run from the clone:** the U12 hero, with two Wikimedia Commons boxes and one synthetic voice note. That's the film's hero case without recordings, as pre-registered in `evidence/batches/21/manifest.md`.
  - The run took 6 calls, 47.8 s and $0.03845 of Meta. Its ledger lines were copied from the clone's ledger into main's.
  - The report is `evidence/live/2026-10-29/report_U12_freeze_clone.json`.
- **What came back:**
  - the transcript "I take Concor 10 milligrams every morning and and BelocZok 50 milligrams twice a day";
  - **Concor:** `intake_differs_from_unit_strength`, 10 mg taken against a 5 mg tablet;
  - **Beloc-Zok against the Bloxazoc box:** `match`, metoprolol succinate 50 mg, modified release;
  - **the beta-blocker note** in the brief ("…beta-blockers); interactions were not assessed.").
- **Scored against the pre-registered key:** a miss on Concor, as in all 10 runs of 28 Oct. The key expected `strength_mismatch`, but "I take Concor ten milligrams" states an intake. That is the CEO's key error, recorded in `evidence/batches/21/u11-u12.md`.
- **Read with the system's own categories:** all three results came out, as they did in 6 of the 10 earlier runs.
- **Harm check:** no false `match`, and both boxes were read at their printed strengths.
- **One usage note:** `scripts/intake_live.py` runs as its docstring says, with `PYTHONPATH=.`. Without it, the import fails before any call.
