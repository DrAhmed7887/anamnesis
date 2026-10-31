muse: workspace root: <repo>/.muse/worktrees/20261031-8311 (cwd default)
muse: warning: rules file at <repo>/CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
This is a plan, not a special mode; I haven't started implementation. Reply `go` to execute this plan, or tell me what to change.

1. **Verdict on the design:** Ship with tightened wording — word rules close the false `match`es but leave fail-open bare numbers and walk-back ambiguities (`SPEC.md:259`).

2. **Risks:**
   1. Negation window under-pins contractions: `don`+`t` tokenisation and 1–2-token window (`SPEC.md:242`) vs keeps like "never miss … five" (`tests/contract/test_b27_relations.py:138`) — pin tokenizer output for `don't`/`I'm` first.
   2. Bare numbers still fail open: no unit leaves unit open (`SPEC.md:250`) and bare number grounds any unit (`SPEC.md:259`) — confirm intended; else add unit-required gate.
   3. Count vs strength collision: "10 ملليجرام tablets" must keep strength (`tests/contract/test_b27_relations.py:189`) though count words follow (`SPEC.md:251`) — implement "no unit word between" check literally.
   4. Another-medicine walk-back ambiguous: skips joiners/numbers/units (`SPEC.md:252`) — "every morning and Panadol 500mg" (`tests/contract/test_b27_relations.py:70`) hits "morning"; define stop words and longer-name win (`SPEC.md:255`).
   5. Past/clause interaction: split on "now/but" (`SPEC.md:240`), past dropped unless discontinued (`SPEC.md:256`, `tests/contract/test_b27_relations.py:95`) — test "used to … Now …" (`tests/contract/test_b27_relations.py:56`) with comma vs `but`.
   6. Rule 6 fraction undefined: daily-total intake dropped only if half/third/quarter mention exists (`SPEC.md:257`) — define value ratio on Decimals and "another run"; "once a day" excluded.
   7. Hook order with drop rule: intake/strength dropped together (`SPEC.md:241`, `anamnesis/providers/claims.py:366`) — hook after `said` check (`anamnesis/providers/claims.py:350`) before drop, per brief (`briefs/27.md:15`).
   8. Own-names source: raw dict + resolved entry (`briefs/27.md:17`, `SPEC.md:253`) vs relabelled labels (`anamnesis/providers/claims.py:313`) — use raw labels, not `_grounded_label` fallback.

3. **The implementation plan:**
   - Module `anamnesis/providers/relations.py` (`briefs/27.md:11`): `tokenize_turn`, `mentions_for_claim`, `is_grounded` (`briefs/27.md:12`).
   - Reuse `normalise`/`ARABIC_CLITICS`/`has_number_role`/`GATE_WORDS` (`briefs/27.md:18`); add positions function, don't change `stated_amounts` (`briefs/27.md:27`).
   - Hook in `parse_claims_json` after value check (`anamnesis/providers/claims.py:353`), before coupled drop (`anamnesis/providers/claims.py:366`).
   - Order: tokenizer/clauses (`SPEC.md:239`) → rules 1–3 → rule 4 → rule 5–6 → hook → `tests/unit/test_b27_extra.py` (`briefs/27.md:19`) then contract.

4. **Open questions for the CEO:**
   1. Should bare "five" ground 5 mg (`SPEC.md:259`) or fail closed like Spanish/German (`SPEC.md:91`)?
   2. Does walk-back skip only listed joiners (`SPEC.md:252`), so "morning" blocks another-medicine attribution?
   3. Is rule-6 half/third/quarter exact Decimal ratio, any unit (`SPEC.md:257`)?
   4. Do clause words split inside "Now I take five" (`SPEC.md:240`)?

Reply `go` to execute this plan, or tell me what to change.
