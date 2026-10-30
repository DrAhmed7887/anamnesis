# The clean-checkout run at `demo-freeze` (30 Oct, 00:14 CET)

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

## The tag moved after batch 24.2 (30 Oct, 06:05 CET)
- **Why it moved:** `demo-freeze` went from 4b32c02 to f29092e, the merge of batch 24.2. That is decision 4 of 30 Oct, a provenance fix the freeze allows (`evidence/decisions.md`). The official freeze is Sat 31 Oct 23:59.
- **What sits between the two tags:**
  - Apache-2.0 for the code only;
  - SNOMED CT ids out of the repository;
  - `CLAUDE.md`'s data line;
  - batch 24.2: no catalogue codes beside a side that contradicts its own name.
- **A fresh clone of main at f29092e from the private remote:**
  - the tree was clean;
  - `uv sync --frozen` ran;
  - ruff passed, and pytest gave **2,417 passed**;
  - `LICENSE` and `NOTICE` were present, and `drugs_v2.json` held no SNOMED ids.
- **No live run:** batch 24.2 changes only which boxes show a codes line. U12's sides agree with their names, and the supervisor found 83 existing briefs byte-identical apart from codes lines.

## The tag moved after batch 25 (30 Oct, 15:21 CET)
- **Why it moved:** `demo-freeze` went from f29092e to 0d8424c, batch 25's log commit after its merge (63b9312). Batch 25 is the brief's look and a viewport tag for phones, on Ahmed's go of 30 Oct. The official freeze is Sat 31 Oct 23:59.
- **What sits between the two tags:**
  - 63002d3, the record of the previous move;
  - batch 25's commits: its contract (a42676b, fixed in 4a7ae6e), the Muse ledger (98bf622), the build (df1f251), the merge (63b9312) and its log line (0d8424c).
- **A fresh clone of main at 0d8424c from the private remote:**
  - the tree was clean;
  - `uv sync --frozen` ran;
  - ruff passed, and pytest gave **2,428 passed**;
  - the page head carries the viewport tag.
- **No live run:** batch 25 changes only the page's style and one tag in its head. Outside them, the briefs are byte-identical: 49 distinct pages from the test suite (supervisor, round 2) and six the CEO rendered.
- **For the judge session:**
  - `anamnesis/brief_html.py` lines from 71 on moved down by 45 (`_SCRIPT` now starts at 134, not 89);
  - `anamnesis/brief.py` lines from 122 on moved down by 2;
  - `docs/CLAIMS.md` rows 1.3 and 1.4 cite `brief_html.py` lines, so they need re-citing at the tag, as planned.

## The tag moved after batch 26 (30 Oct, 23:10 CET)
- **The tag:** `demo-freeze` now points at 4dbacff: batch 26 merged in 12093c9, plus the live U1–U8 results and the Modal reconcile.
- **A fresh clone** of the tag from the private remote passes all 2,490 tests offline.
- **What batch 26 changed:**
  - `anamnesis/providers/base.py`: the Modal price and `gpu_ms`;
  - `scripts/intake_live.py`: the `--extractor glimmer`, `--reader fireworks` and `--glimmer-url` options and their guards;
  - two new files, `anamnesis/providers/glimmer.py` and `finetune/modal_serve.py`.

  `anamnesis/brief_html.py` is untouched since batch 25.
- **For the judge session:**
  - no row of `docs/CLAIMS.md` or the README draft cites a line of the changed files, so the rows re-cited after batch 25 stand;
  - new rows for the open-weight path should cite `evidence/batches/26/intake-plan.md` ("Results, 30 Oct evening") and the 30 Oct batch 26 entry in `evidence/decisions.md`, with their wording limits: never "better", "beats" or "matches", and Fireworks "couldn't be judged live".

## The tag moved after batch 26.1 (30 Oct, 23:53 CET)
- **The tag:** `demo-freeze` now points at c657db5: batch 26.1 merged in 0af0e33, plus the fourth live column and the Astra grill.
- **A fresh clone** of the tag passes all 2,519 tests.
- **What batch 26.1 changed:** `anamnesis/providers/openweight.py` (an optional `reasoning_effort` on the reader) and `scripts/intake_live.py`, where Fireworks asks for `low`. Neither file is cited by line in `docs/CLAIMS.md`.
- **For the judge session:**
  - the open-weight rows can cite the fourth column (`evidence/batches/26/intake-plan.md`, "The fourth column's results"), which ran both model steps on Meta open weights: 5 of 8, 0 harmful;
  - the Astra grill's wording advice is in `evidence/grills/win-grill-astra/effect.md`.
