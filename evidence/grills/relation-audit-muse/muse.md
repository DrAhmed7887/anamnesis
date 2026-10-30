muse: workspace root: <repo>/.muse/worktrees/20261031-df9a (cwd default)
muse: warning: rules file at <repo>/CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
## 1. Verdict

Audit direction is right but its "no code change" conclusion is under-evidenced: method is largely the real path, several false-`match` traps are missing, and n=8×1 proves little.

## 2. Findings

1. **Severity: medium — offline path is the real checks + reconciler.** `audit.py` calls product `parse_claims_json` (`anamnesis/providers/claims.py:285`) then `tests/.../intake` with the real reconciler (`anamnesis/core/reconcile.py:340`, `:443`; test file imports both at `tests/contract/test_b19_brief.py:23`, `:28`). **Fix:** cite the `intake` helper's lines; I did not open them, so fake-provider fidelity is unverified.
2. **Severity: high — value-only check confirmed, so A/B/H table is plausible.** Amount survives iff `amount in said` (`anamnesis/providers/claims.py:353-358`), where `said` is `stated_amounts` (`anamnesis/providers/stated.py:760-773`): every number, no negation, tense, or attribution. SPEC pins it: "Only the value is checked, not its unit or the word next to it" (`SPEC.md:238`). **Fix:** keep table; add this citation.
3. **Severity: medium — E/F/G fail-safe is explained by code, not luck.** Multi-ingredient intake returns `INSUFFICIENT_INFORMATION` (`anamnesis/core/reconcile.py:385-386`); intake INN≠pack INN returns it too (`anamnesis/core/reconcile.py:146-149`); `units` "never produce a match" (`anamnesis/core/reconcile.py:345-356`, `SPEC.md:238`). **Fix:** note these three rules in README.
4. **Severity: high — "no code change" from 0/16 overstates one run each.** `probe_live.py` loop is one call per case×model (audit inline, `for case... for name, extractor`). Eight invented transcripts cannot bound negation/code-switching risk. **Fix:** freeze doc now, but file smallest follow-up: add the §3 traps as contract tests; gate any negation heuristic behind them.
5. **Severity: low — README sentence is accurate if scoped.** "Checks test that an amount is said in the cited turn, not what it's said about" matches `claims.py:350-358` + `SPEC.md:238`. But names are also turn-grounded (`anamnesis/providers/claims.py:180-186`) and labels brand-relabeled (`anamnesis/providers/claims.py:275-282`). **Fix:** write "each amount value was said in a cited turn; which medicine, tense, negation, or unit it belonged to is not checked."

## 3. Missing traps

- **mcg said, mg claimed (pack 5 mg; "5 mcg" → claim 5 mg): would pass** as false `match` — value 5 is stated (`stated.py:760`), reconciler sees 5 mg vs 5 mg ratio 1 (`reconcile.py:155-158`).
- **"twice" → "two" mg/units: caught by today's checks** for false `match` — "twice" states no amount I saw in `stated.py:10-16`, so mg intake drops (`claims.py:357-358`); `units` path never matches (`reconcile.py:353-356`).
- **Daily total as intake ("10 mg a day" on 5 mg pack → intake 10 mg): would pass** (not as `match`) — 10 stated, ratio 2 gives `intake_differs...` (`reconcile.py:155-160`).
- **Two same-ingredient brands, swapped amounts, same turn: would pass** as wrong fact, usually not false `match` — same-turn values both stated; pairing prefers same brand (`reconcile.py:434-453`), so swapped doses mismatch rather than match.
- **Other brand's strength ("Concor ... Panadol 500 mg" → Concor strength 500 mg): would pass** (not as `match`) — 500 stated (`claims.py:353-356`), `_strength_type` mismatches (`reconcile.py:103-130`).

## 4. Open questions

- What is the exact proposed README sentence? I judged the "said in the cited turn" line from the audit inline.
- Does `tests/.../intake` stub anything (vision/overlap/brief) that could change `FACT` vs fail-safe? Need its lines.
- Do `MetaClaimExtractor`/`GlimmerClaimExtractor` share `parse_claims_json`, or does Glimmer add checks?
