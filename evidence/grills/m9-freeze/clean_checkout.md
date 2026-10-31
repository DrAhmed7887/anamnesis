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

## The tag moved after the relation audit (31 Oct, 00:15 CET)
- **No code changed.** The tag adds the audit (`evidence/audits/relation-provenance/`, with Muse's double-check) and its decision entry.
- **For the judge session:** the README's limits section should carry the audit's sentence and numbers ("Decision", 31 Oct, in `evidence/decisions.md`).

## For the judge session: the freeze moved, batch 27 is coming, and PubMed citations (31 Oct, 11:46 CET)
- **The freeze moved (Ahmed, 31 Oct):** engine changes stay open until Tue 3 Nov 12:00 CET (`evidence/decisions.md`, "10:45: the freeze moves"). Captures come Mon from the tag of that moment.
- **The README's limits sentence from the audit is about to change.** Batch 27 adds word rules on claim amounts (negation, units, counts, another medicine's amount, past doses, split daily totals), so "which medicine, tense, negation or unit it belonged to is not checked" will no longer be true as written. Wait for the merge entry below before re-wording it.
- **The hero's 6 of 10 predates batch 24's fix** (`evidence/diagnostics/hero-claims-2026-10-31/`). Ten fresh runs are pre-registered there; don't re-word the hero rows until they're in.
- **PubMed, checked by the engine through E-utilities** (`evidence/ncbi/README.md`, `pubmed_esummary.json`):
  - lead the problem statement with Bedell 2000 (PMID 10904455): in an outpatient practice, 76% of patients (239) had at least one discrepancy between what they took and the doctor's record. Of the 545 discrepancies, 51% were medicines taken but not recorded; the split is of discrepancies, not patients;
  - Tam 2005 (PMID 16129874, up to 67%) and Cornish 2005 (PMID 15738372, 53.6%) are hospital admissions: say "at admission";
  - README line 14's "33 of 44" is confirmed (PMID 42849491). The study enrolled 114 and 98 completed: never "n=100".
- **PubChem:** "35 of 52 aliases agree with PubChem, none disagree, 17 aren't listed there", never "verified against PubChem" alone. A snapshot test may follow.

## For the judge session: batch 27 merged, and the hero's ten fresh runs (31 Oct, 12:58 CET)
- **Batch 27 merged** (3d3a30e): word rules on claim amounts. Results in `evidence/batches/27/checks.md`:
  - the relation audit's ten traps all fail safe offline; live, 19 of 20 calls showed no wrong finding as fact, and the one that did (trap J on the tuned Glimmer, a false disagreement through its tablet count) is batch 27.1's target;
  - Spark 1.3's, r1's and r2's scores are unchanged, byte for byte; on base Glimmer's replies, 52 wrong amounts are no longer shown.
- **The README's limits sentence** can now say: each amount is checked as said in a cited turn, and word rules check what it was said about (negation, unit, count, another medicine, past, a split daily total); words outside those rules, and medicines in neither the catalogue nor the reply, aren't seen. Cite SPEC §2 "Relation checks (batch 27)".
- **The hero, ten fresh runs on 2e0d985** (`evidence/diagnostics/hero-claims-2026-10-31/results.md`): **10 of 10 with the system's own categories, 0 harmful**; 0 of 10 as registered on 28 Oct, whose Concor row named the wrong type. Report both, never only the 10. The 28–29 Oct 6 of 10 predates batch 24's fix (`README.md` in the same folder). Synthetic voice, n = 10.
- **U1–U8 after batch 27:** 3 of 8 correct, 0 harmful; three of the five misses are packs Spark 1.3 read as partial, batch 28's target.
