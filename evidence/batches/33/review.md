# Batch 33 review: a salt said inside a longer label (SPEC §3, rule 6)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 1 round, planned first by a read-only Muse session and audited by a fresh one

Verdict: PASS

**What the batch adds:**
- **`_side_salts`** (`anamnesis/core/reconcile.py`): each strength ingredient's and intake's `inn` label is also read for salts the way `name_text` and `label_text` are (`_text_salts`: whole-word curated aliases, and curated salt words beside a moiety or brand the label names). It holds on both sides.
- **The effect:** "tomo metoprolol succinate", "tomometoprolol succinate", "metoprolol, succinate", "metoprolol (as succinate)", "metoprolol succinate retard" and "metoprolol succinate 100 mg", as an intake or a strength label, are `formulation_mismatch` against a tartrate pack, as the exact label "metoprolol succinate" always was. Before, each was a `match`.
- **What doesn't change:** a label naming the pack's own salt still matches, a label with no curated salt adds nothing, the scalar `inn`, the pack's salt-basis lookup, the salt tables and name matching.

**Why:** after batch 32, the README named this gap. Batch 32's supervisor had found it, and the CEO confirmed it while checking a README sentence: a salt said inside a longer label wasn't read, so a formulation difference could reach the clinician as a match. Ahmed's call (2 Nov): close it as batch 33 before Wednesday.

**Who did what:**
- **A read-only Muse session planned it** (`evidence/grills/b33-muse-plan/`, $0.2562). It agreed with the CEO's candidate, and six of its eight risks went into the contract (`effect.md`).
- **The CEO** wrote the SPEC bullets, the contract (38 cases, then 40) and a throwaway reference (`reference.md`): 38 of 38 with 6 of 6 deliberate breaks caught, and the 205 saved live reports unchanged.
- **Muse built it in one round** ($0.75216): two lines in `_side_salts` and 8 tests of its own. Gate 2,923, then 2,925 on the round-2 contract.
- **The Opus supervisor** (`supervisor.md`), **APPROVE.** No pair newly agrees: none of 22,746 generated pairs moves to `match`, and the 205 saved reports give the same findings as before. Four minor points:
  - #1 and #2, older limits that labels now reach too: calcium vs calcium trihydrate and fumarate vs hemifumarate count as different salts, and a salt named as a basis or negated still counts. Both fail toward review; the CEO wrote them into SPEC rule 6's known limits.
  - #3, a contract gap: taken by the CEO as round 2 of the contract, with no Muse round, because the build already passed it.
  - #4, the docstring of `_side_salts` doesn't mention labels: left for the next batch that touches it.
- **A fresh Muse session audited it, read-only** (`evidence/grills/b33-muse-audit/`, $0.28269), and asked for changes. The CEO ran each finding (`effect.md` there):
  - #1, a salt from one part's label credited to another moiety, changed no result: such a part already fails identity, before and after.
  - #2, alias and loose salt words suppressed separately, is the supervisor's #1. Its fix would turn abstentions into matches, which this batch's hard limit forbids.
  - #3 can't happen with today's table: every salted moiety resolves to itself.

**The gate** (on the round-2 contract, `33e6bd9`): 2,925 tests pass, ruff is clean, and the contract lock holds.

**Usage:** Muse's build $0.75216 est. (the Muse ledger); its plan and audit $0.53886, in neither ledger (`scripts/spend_check.py` adds them).

**Not in this batch:** Spanish salt names (SPEC's batch 32 known limit), counting calcium trihydrate as calcium and hemifumarate as fumarate, and reading "equivalent to" on a pack that prints its salt basis.
