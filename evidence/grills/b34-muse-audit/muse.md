muse: workspace root: <repo>/.muse/worktrees/20261102-7148 (cwd default)
muse: warning: rules file at <repo>/CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
**Verdict:** Pass — the eleven-word table and `_loose_salts` hookup match the spec; no disagree/abstain→agree path found.

**Findings:**

1. Low — decomposed (NFD) `cálcica` is not read. `normalise` ([catalogue.py](anamnesis/core/catalogue.py:12)) has no NFC step, and the diff table holds only composed `cálcica` plus plain `calcica`. NFD input puts U+0301 between letters; it isn't `\w`, so line 19 turns it into a space (`ca lcica`), matching neither key. Precedent: alias keys NFC-normalise so decomposed accents resolve ([medication.py](anamnesis/schema/medication.py:110)). Fix: NFC-normalise once around the Spanish comparison inside `_loose_salts` (the `reconcile.py` diff hunk), leaving global `normalise` untouched.

**What you checked and found fine:**

- Table is exactly the spec's eleven words, every value a curated English salt ([medication.py](anamnesis/schema/medication.py:46)); only `_loose_salts` reads it; `INN_ALIASES`, `canonical_inn`, `salt_of`, and name matching untouched.
- Whole-word padded match plus unchanged moiety-or-brand gate ([catalogue.py](anamnesis/core/catalogue.py:105)); capitals, punctuation, line breaks, and word order all handled via `normalise`; cross-moiety and inside-word attachment impossible.
- One salt across languages (`succinato`+`succinate` collapse to one entry); longer-suppresses-shorter runs on English names so `cálcica trihidrato` stays one salt ([reconcile.py](anamnesis/core/reconcile.py:275)); calcium vs calcium trihydrate and fumarate vs hemifumarate stay split per the known limits.
- Hero boxes gain fumarate (Emconcor) and tartrate (Lopresor) without changing the pinned findings; pairing, scoring, and rule 7 (Spanish claim salt drops nominal equivalents like English; pack lookup stays exact-only, [reconcile.py](anamnesis/core/reconcile.py:224)) verified against the contract.
- Added salts can only add rule-3 conflicts, rule-6 mismatches, or remove equivalents — nothing that disagreed or abstained can now agree.
