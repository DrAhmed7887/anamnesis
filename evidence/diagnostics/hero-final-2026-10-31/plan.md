# The hero on the final code: written before any call (31 Oct, 20:01 CET)

- **What:** the hero case U12, ten runs on the default path, in one sitting. Spark 1.3 extracts the claims and reads the labels, and there is no second reader. It uses two public Commons photos and the synthetic voice note `U12.wav`, which never appears in the film.
  - **The code:** `main` with the code of `demo-freeze` (34473ba): since the tag, nothing under `anamnesis/`, `scripts/` or `tests/` has changed, only docs.
  - **The command:** the same as on 31 Oct at 12:45 (`evidence/diagnostics/hero-claims-2026-10-31/`), with case id `U12-final`.
- **Why:** the 31 Oct ten (10 of 10 with the system's own categories) ran on batch 27's code. Batches 27.1, 28, 29 and 30 merged after them. Batch 29 changed Spark's claim prompt, and batch 30 changed how a pack's `inn` resolves. The claims table can't say "on the submitted code" until the hero runs on it.
- **Scored two ways, both reported,** with `evidence/diagnostics/hero-claims-2026-10-31/score_rerun.py` on these reports:
  1. as registered on 28 Oct, which scores 0 by construction;
  2. with the system's own categories: Concor `intake_differs_from_unit_strength`, Beloc-Zok `match`, and the beta-blocker note. A run counts when all three appear.
- **Expected:** close to the 31 Oct ten. Two risks:
  - batch 30's whole-name rule makes a pack abstain if the reader writes an `inn` with words the alias table lacks;
  - transcription repeats can leave a name unresolved.

  Both fail safe, and each is reported.
- **Harmful:** any false `match`, or a wrong strength or ingredient shown as fact. Expected 0.
- **Spend:** about $0.40 of Meta, which brings it to about $78.35 of the $80 line.
