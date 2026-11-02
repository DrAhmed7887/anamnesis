# Batch 32 review: Spanish speech in catalogue resolution (SPEC §3)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 2 rounds

Verdict: PASS

**What the batch adds:**
- **`Catalogue._matches`** (`anamnesis/core/catalogue.py`): for Latin-script names, `b` and `v` match each other, and one attached form of *tomar* (`TOMAR_FORMS`: tomo, toma, tomas, tomamos, toman) may come right before a name, inside the match. "visoprolol", "Tomobisoprolol" and "Tomovisoprolol" now resolve to bisoprolol.
- **What stays exact:** Arabic names, as before, and every name that carries a salt ("metoprolol succinate"), so a spelling variant can't drop a salt.
- **What doesn't change:** the claim keeps its name as heard, matching stays on whole words, and text that names two products still resolves to `None`.

**Why:** the Spanish hero's fourth set (U13d, 2 of 10). Voice Transcribe wrote a natural Spanish voice's "Tomo bisoprolol" as "visoprolol", or joined the verb to the name, and the claim stayed unresolved in 8 runs. Ahmed's call (1 Nov, evening): fix it, then re-test the same voice.

**Who did what:**
- **The CEO** wrote the SPEC bullet, the contract (45, then 58 cases) and a throwaway reference for each (`reference.md`): 45 of 45 with 6 of 7 deliberate breaks caught (the seventh can't change a result), then 58 of 58 with 3 of 3.
- **Muse built it in two rounds:**
  - **round 1** ($0.47757): the fold and the attached forms, gate 2,863;
  - **round 2** ($0.95865): the review's fixes, gate 2,877.
- **The Opus supervisor** (`supervisor.md`):
  - **Round 1, CHANGES:** a salt name spelled with `b`/`v` or a joined *tomar* form lost its salt, so "tomometoprolol succinate" against a tartrate pack went from `insufficient_information` to `match`. It also found test gaps (`p`/`w` folding and other verb forms would have passed) and asked for a named constant. All were taken.
  - **Round 2, APPROVE**, with one minor point on SPEC wording, taken by the CEO without another Muse round: the label limit is now stated as partly new with this batch.
  - **Its probes:** nothing newly matches among 729 RxNorm and CIMA drug names or 313,489 dictionary entries; of 193 saved live reports, only the eight U13d runs change, each to the intended result.

**The gate** (on the round-2 contract, `6722c7f`): 2,877 tests pass, ruff is clean, and the contract lock holds.

**Usage:** Muse's two rounds cost $1.43622 est. (the Muse ledger).

**Not in this batch:**
- the live re-test, which follows the merge, pre-registered (set 5);
- the two limits now stated in SPEC: a salt word inside a label isn't read by name matching, and the alias table has no Spanish salt names.
