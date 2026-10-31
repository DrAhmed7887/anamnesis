# Batch 24.1: the supervisor's review

## Round 1: SUPERVISOR: APPROVE
**No finding meets a CHANGES condition.**
- **Codes:** every code matches the brief's table, including Nolotil N02BB02 / RxCUI 3523, and no existing entry changed.
- **Escaping:** hostile names and code values are escaped, and there are no links.
- **The reference line:** exactly once, and only when codes show.
- **Which box shows codes:** the claim side first, the pack side only with no claim.
- **No regressions:** existing briefs and findings are byte-identical apart from the new lines, and resolution is unchanged across 2,230 names in 6 countries.
- **Fine-tune data:** byte-identical.
- **The build:** 2,411 passed.

**Findings, none blocking:**
1. **Info:** "metamizole 575 mg" now resolves to Nolotil, giving `missing_modality` with codes instead of `unresolved_name`. That is the SPEC's ingredient rule.
2. **Low, for Ahmed:** claim "Concor" with said INN "atorvastatin" shows bisoprolol's codes next to the patient's atorvastatin. This follows the SPEC; whether to hide codes when name and ingredient conflict is a design decision.
3. **Low:** the pack side resolves without `pack.country`, while reconciliation uses it. It has no visible effect today.
4. **Nit:** the codes entry is worked out twice, and the results agree.
5. **Housekeeping:** the worktree's ledger copy. Main already has the line (11a0ebb).
