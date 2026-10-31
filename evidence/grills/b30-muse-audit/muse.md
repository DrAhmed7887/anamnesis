muse: workspace root: <repo>/.muse/worktrees/20261031-65e7 (cwd default)
muse: warning: rules file at <repo>/CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
**Verdict:** Request changes — combined-`inn` salts are dropped (false-`match` risk), plus two minor split gaps.

**Findings:**

1. **High — salts named in a combined `inn` never reach rule 6.** [reconcile.py](<repo>/.muse/worktrees/20261031-65e7/anamnesis/core/reconcile.py:247) (`pairs.append((_resolve_inn(inn…), salt_of(inn)))`) resolves the whole string, and the diff only splits inside `_identity`. Evidence: `salt_of("metoprolol tartrate/amlodipine")` is no curated salt, so two sides whose combined `inn`s name different salts compare with empty salt sets → `match` instead of `formulation_mismatch` ([SPEC.md](<repo>/.muse/worktrees/20261031-65e7/SPEC.md:303) rule 6). Fix: split with `_split_inn_parts` in `_side_salts` and add one pair per part.
2. **Low — single-part fallback resolves the raw string.** Diff lines `elif _resolve_inn(inn, catalogue) not in inns:` (both branches) use `inn`, not the stripped `parts[0]`. Evidence: `"amoxicillin/"` filters to one part but resolves `"amoxicillin/"` → likely unknown → false extraction conflict. Fix: resolve `parts[0]` when `parts` is non-empty.
3. **Low — attached Arabic `و` won't split.** Diff regex `(?<!\w)و(?!\w)` vs [SPEC.md](<repo>/.muse/worktrees/20261031-65e7/SPEC.md:291) ("spaced «و»"). Evidence: `"amoxicillin وclavulanic"` (attached, the normal Arabic spelling) yields one unknown part → false `insufficient_information`. Fix: also split `و` attached to the next word, or strip via clitic handling.

**What you checked and found fine:**

- Delimiter set (`/ + & , and و`, case-insensitive) matches the contract cases ([test_b30_combined_inn.py](<repo>/.muse/worktrees/20261031-65e7/tests/contract/test_b30_combined_inn.py:54)); `candesartan`/`دواء` non-splits hold via `\b`/`\w` guards.
- Set-equality vs single-`inn`-among-strength logic; subset/superset and one-ingredient-strength conflicts ([test_b30_combined_inn.py](<repo>/.muse/worktrees/20261031-65e7/tests/contract/test_b30_combined_inn.py:63)); no-strength identity ([test_b30_combined_inn.py](<repo>/.muse/worktrees/20261031-65e7/tests/contract/test_b30_combined_inn.py:74)).
- No other reconciler rules touched: diff is `_identity` + helper + new unit test; name-mismatch/ambiguous conflict paths preserved.
