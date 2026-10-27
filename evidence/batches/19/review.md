# Batch 19 review: the clinician brief, observations across medicines, coverage, and the reply schema in Spark estimates (SPEC §7, §3, §5)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 2 rounds, goal pinned with its goal tool in each

**Who did what:**
- Claude Code (Opus 5.5), as CEO, wrote the SPEC lines, the brief, the contract and the round-2 brief.
- Before Muse started, the CEO ran the contract against a throwaway reference build. All 42 new contract tests and the whole suite (617) passed, and 6 mutations were each caught.
- Round 2's new contract cases were proven the same way (624).
- Muse wrote all the code.

**Gate:** pass, 638 tests (575 before). The contract lock held in both rounds.

**Goal (`goal.md`, now printed by `batch.sh` after every run):**
- Round 1: `create_goal` with the batch's check, closed complete; 29 of 30 main-agent model calls were under it.
- Round 2: the same, through the new `batch.sh round`; 42 of 43.

**Muse cost:** **$2.31096** for the batch, priced from Muse's own billing records (`usage.json`):
- round 1: $0.96374, from 3,374,352 input tokens (3,135,243 cached) and 45,780 output;
- round 2: $1.34722, from 4,717,264 input (4,426,327 cached) and 75,201 output.

Verdict: PASS (supervisor APPROVE, round 2)

## What changed
- **The clinician brief** (`anamnesis/brief.py`, `brief_html.py`) is one self-contained static HTML page per intake.
  - **Layout:** disagreements first. Then observations across medicines, findings that can't be confirmed, agreements, and medicines reported as stopped.
  - **Evidence:** both sources sit side by side, and every fact links to its audio turn and its image region. Each region shows the crop the reader saw. A turn plays on its own, from its start to its end.
  - **Coverage** never goes silent: every photo gets a line ("no pack found", "could not be opened", "not examined"), and so does the voice note and a budget stop.
  - **Fixed scope lines.**
  - **Mismatched media:** the page refuses photos or audio the report wasn't made from (`intake_id`).
- **Across medicines** (`anamnesis/core/overlap.py`), from what the patient reports, never from the photos:
  - the same ingredient in two products (Panadol + Gelocatil);
  - two members of one curated class (Concor + Beloc-Zok, two beta-blockers).
- **Pairing:** a named brand is compared with its own pack before the score. Before this batch, "Panadol 1 g" could match an equal-strength Gelocatil pack and hide that the Panadol pack says 500 mg.
- **Catalogue:** Gelocatil (synthetic, ES), for the hero case.
- **Spark estimates** also count the reply schema. They now bound the live claim calls (550 and 559 billed prompt tokens), and a live-sized length stop stays inside a cap set to the estimate. Label reads are pinned at `max_tokens` 4000 and the zoom at a Lanczos 2x upscale.

## How it was checked
- **Supervisor:** round 1 asked for changes on 4 major points: boxes hid the photo, turn playback broke, wrong media were accepted, and score-first pairing hid a disagreement. Round 2 approved (`supervisor.md`).
- **The CEO's browser check** rendered both synthetic live intakes and the contract showcase with each round's code. Round 1 had seven visible defects, all fixed in round 2:
  - boxes painted black;
  - the page scrolled sideways on a 382 px screen;
  - evidence links ran together;
  - no turn controls;
  - no crop captions;
  - no title;
  - no `dir="auto"`.
- **Playback**, tested with real clicks: turns play one after another and stop at their end, and evidence links play their turn.
- **Media check:** the saved live reports render with their original media, so their recomputed `intake_id` matches.

## Follow-ups (from the supervisor; none blocking)
- Pin the playback script (pause at the end, the shared end time, link playback) and `dir="auto"` in the next contract.
- Small leftovers: the `reconcile_all` docstring, the unused `FIELD_EVIDENCE`, and a `continue` in `_photos_html` that should raise.
