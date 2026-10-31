muse: workspace root: <repo>/.muse/worktrees/20261031-a846 (cwd default)
muse: warning: rules file at <repo>/CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
**Verdict:** Request changes — units backing ignores negation/context; durations and negation look right.

**Findings:**

1. Medium — negated/other-medicine counts back `units_per_intake`. `anamnesis/providers/relations.py:599-608` excludes negated/another/past runs before counting, but the diff's `count_values_for_cited_turns` checks only `+    if _is_count(tokens, start, end, clause, False):` with no `_is_negated`/`_is_another`/`_is_past`. Evidence: "I take Concor not ten milligrams, not two tablets" with units 2 keeps the 2; a Panadol "two tablets" in a shared cited turn likewise backs Concor's units. Fix: apply `_is_negated` (and, for active claims, past/another filtering) inside `count_values_for_cited_turns`, threading own/another names and status through.
2. Low — gate logic duplicated, risks drift. `anamnesis/providers/relations.py:586-594` appends the gate word before `stated_amounts`; the diff repeats it (`+            and (tokens[nxt].text in GATE_WORDS or tokens[nxt].text in _GATE_EXTRA)`) in `count_values_for_cited_turns`. If the gate set changes, counts and mentions diverge and units are wrongly kept or dropped. Fix: extract one `_run_values(tokens, start, end, clause)` helper used by both.

**What you checked and found fine:**
- Duration list matches SPEC (`SPEC.md:252`); unit-word and "ends in a" guards correct; durations excluded before grounding/splitting so "ten a day for five years" keeps 10.
- "weiß nicht 5" keeps, plain "nicht 5" still drops; clause checks intact.
- Units cleared only when `relation_dropped` is set; backed counts keep units; pairing rule at `anamnesis/providers/claims.py:396-401` then applies unchanged.
- Batch 27 traps C–J (`tests/contract/test_b27_relations.py:54-110`) contain no knowing-negation or duration-adjacent numbers, so behaviour there is unchanged.
