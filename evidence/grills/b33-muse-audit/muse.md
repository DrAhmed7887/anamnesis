muse: workspace root: <repo>/.muse/worktrees/20261102-72e1 (cwd default)
muse: warning: rules file at <repo>/CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
## 1. Verdict

Request changes: the build meets the contract, but the label-salt union can misattribute and double-count in cases the contract doesn't pin.

## 2. Findings

1. **Medium — label salt not scoped to its own ingredient.** Diff (`pairs.extend(_text_salts(part.inn, catalogue))`) adds salts for *any* moiety found in one part's label: `anamnesis/core/reconcile.py:251-265` returns all-alias/all-loose matches, and `anamnesis/core/reconcile.py:282-301` unions them without filtering to `_resolve_inn(part.inn)`. A combination line or brand-plus-words mentioning another moiety attributes that salt to the wrong key. Fix: keep only pairs whose moiety equals the part's resolved moiety.

2. **Medium — alias/loose suppression is per-set, not across the union.** Suppression lives inside each set (`anamnesis/core/reconcile.py:262` for aliases, `anamnesis/core/reconcile.py:278` for loose), then `anamnesis/core/reconcile.py:264` unions them. The contract shows both `calcium` and `calcium trihydrate` salts exist (`tests/contract/test_b33_label_salts.py:102-103`); any label where the alias match and loose match yield different strings for one moiety (missing longer alias, `(as …)` variant) becomes two salts → rule 3 `insufficient_information`, losing a finding. Fix: one final substring-suppression pass per moiety over the union.

3. **Low — loose moiety unresolved, alias moiety resolved.** `anamnesis/core/reconcile.py:260` wraps alias moieties in `_resolve_inn`, but `anamnesis/core/reconcile.py:275-279` returns raw `moiety`. A synonym-moiety salt then splits across two keys: conflict missed (two keys of one) or `_salts_differ` missed (keys don't intersect, `anamnesis/core/reconcile.py:318-326`). Fix: `_resolve_inn` the loose moiety too.

## 3. What you checked and found fine

- Longer succinate/maleate labels mismatch; own salt still matches; salt-free labels add nothing (contract §§1–2).
- Two salts on one side abstain, claim and pack readings included.
- Scalar `inn` still exact-only (`anamnesis/core/reconcile.py:293-295`).
- Pack nominal lookup still exact-only (`anamnesis/core/reconcile.py:228-238`); claim label salt correctly disables it via `_claim_has_salt`.
- Monotonic: salts only added, so no disagree→agree path through `_salts_differ`/`_salt_conflict`/nominal.
- `_pair_score` conflict path (`anamnesis/core/reconcile.py:464`) consistent with rule 3.
