# Batch 34 review: Spanish salt names (SPEC §3, rule 6)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 2 rounds, planned first by a read-only Muse session and audited by a fresh one

Verdict: PASS

**What the batch adds:**
- **`SPANISH_SALT_NAMES`** (`anamnesis/schema/medication.py`, exported from `anamnesis.schema`): eleven Spanish salt words, as Spain's medicines registry (AEMPS CIMA) names the active substances, each mapped to a salt `INN_ALIASES` already curates in English: succinato, tartrato, fumarato, hemifumarato, besilato, maleato, hidrocloruro, cálcica or calcica, and cálcica trihidrato or calcica trihidrato.
- **`_loose_salts`** (`anamnesis/core/reconcile.py`): a curated salt counts when its English name or one of its Spanish words stands as whole words in a text that names the moiety or its brand, and a Spanish word is read as its English salt.
- **The effect:** "metoprolol succinato" against a tartrate pack, a claim named "Metoprolol succinate" against Spain's Lopresor box ("Metoprolol, tartrato"), "besilato de amlodipino" against a maleate pack and "amlodipino maleato" against a besilate pack are each `formulation_mismatch`. Before, each was a `match`. The Spanish hero's findings don't change: its claims name no salt.
- **What doesn't change:** `INN_ALIASES`, `canonical_inn`, `salt_of`, the validator, the claim parser and name matching, so a Spanish salt name is never a catalogue name.

**Why:** after batch 33, the README named this as the remaining false-match path for Spanish speech. Ahmed's call (2 Nov): close it as batch 34.

**Who did what:**
- **A read-only Muse session planned it** (`evidence/grills/b34-muse-plan/`, $0.26612). It chose the CEO's candidate, a separate table read only by `_loose_salts`, over adding the names to `INN_ALIASES`, which feeds identity, grounding and name matching. Six of its nine risks went into the contract (`effect.md`).
- **The CEO** queried CIMA for the Spanish names (`evidence/data/cima_salts.json`), and wrote the SPEC bullets, the contract (53 cases, then 58) and a throwaway reference (`reference.md`): 53 of 53, with 8 of 8 deliberate breaks caught, and the 205 saved live reports unchanged.
- **Muse built it in two rounds:**
  - **round 1** ($0.40069): the table and the reading, gate 2,981;
  - **round 2** ($0.28682): the two docstrings the supervisor and batch 33's supervisor asked for, nothing else (the CEO diffed it against round 1), gate 2,986.
- **The Opus supervisor** (`supervisor.md`), **APPROVE.** The table is exactly the SPEC's eleven words, and all 205 saved reports give the same findings, pair types and pairing scores. Four minor points:
  - #1, a text naming calcium in one language and calcium trihydrate in the other now matches a calcium trihydrate pack: the CEO checked that the all-English wording already matched on `main`. Named in SPEC as the one move toward `match`, and pinned (`reference.md`, round 2).
  - #2 and #3, the known limits reaching Spanish box text, and decomposed accents read only where the validator composes them: written into SPEC rule 6's known limits.
  - #4, the `_loose_salts` docstring: taken in round 2, with batch 33's `_side_salts` docstring.
- **A fresh Muse session audited it, read-only** (`evidence/grills/b34-muse-audit/`, $0.26079): pass, with one Low finding, the supervisor's #3 (`effect.md` there).

**The gate** (on the round-2 contract, `7c9cbbe`): 2,986 tests pass, ruff is clean, and the contract lock holds.

**Usage:** Muse's two rounds $0.68751 est. (the Muse ledger); its plan and audit $0.52691, in neither ledger (`scripts/spend_check.py` adds them).

**Not in this batch:** other languages' salt names (German "Metoprolol Succinat" as two words, for one), and the older salt limits SPEC rule 6 names.
