muse muse-spark-1.3, batch 17, started 2026-10-27T15:50:57Z
muse: workspace root: <repo> (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
All green. Short report:

**Files changed**
- `anamnesis/core/reconcile.py` — `_identity`, `_release`/`_claim_release`, `_pair_type`, ratio refactor (`_dose_ratio_type`, `_units_type`).
- `anamnesis/core/catalogue.py` — added `Catalogue.is_ambiguous` and `Catalogue.matches_brand`.
- `anamnesis/schema/templates.py` — new `match` note.
- `anamnesis/providers/claims.py` — dropped-`units_per_intake` rule.
- `tests/unit/test_reconciler_extra.py` — new, 12 focused tests. Nothing under `tests/contract/` touched.

**Per numbered change**
1. C1 units-per-intake: new `_units_type` reuses the extracted `_dose_ratio_type` (same mapping as rule 8, no copy). In `_pair_type` it runs only with no `intake_amount`, `u ≠ 1`, a pack strength, and either no claim strength or rule 7 already agreeing; it never sets `compared`, so it can't produce `match` or satisfy rule 9.
2. Parser: `parse_claims_json` coerces the regimen once, and a sent-but-unparseable `units_per_intake` nulls `strength` and `intake_amount` like the existing dropped-amount rule.
3. C4: `is_ambiguous` (matches exist but `resolve` is `None`) sets the side's extraction-conflict flag even when identity comes from strength; brand-plus-ingredient of one product still resolves, so no false conflict. With no strength/inn it stays `unresolved_name` per the rule order and the type table.
4. C8: `_claim_release` trusts an explicit claim release on a release word (whole word after `normalise`, incl. `ممتد`, `بطيء`) or a catalogue brand match; otherwise brand-implied. Pack side unchanged.
5. Match note is now exactly `The compared identity and strength details agree.`

**Verification** — `.venv/bin/python -m pytest -q`: 551 passed (21 batch-17 contract + 12 new + rest); `.venv/bin/ruff check .`: clean. (`uv` itself is unusable here — cache init fails — so I used the repo `.venv` directly.)

**One thing in the brief I think is wrong** — change 4 as literally worded ("a claim's explicit release counts *only if* … otherwise brand-implied") contradicts two frozen older tests: `test_b3_hardening.py::test_decision_order_v2[release_ir_vs_er]` and `test_b10_identity.py::test_f01b…`, where a bare-name claim with explicit `immediate` vs a modified pack must stay `formulation_mismatch`. I implemented the version all three contracts agree on: an *unsaid release that agrees with the pack* is distrusted (kills the false match), while an unsaid release that *disagrees* still flags the conflict. This keeps the batch's false-agreement goal intact without downgrading safe flags, and I locked it with `test_an_unsaid_release_that_disagrees_still_flags_a_conflict`.

## Round 2
muse muse-spark-1.3, batch 17 round 2, started 2026-10-27T15:58:49Z
muse: workspace root: <repo> (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
All three supervisor findings are fixed, with `ruff` clean and the full suite green.

- `anamnesis/core/reconcile.py` — item 1: dropped the `claim.intake_amount is None` gate so the units mapping also runs after an intake comparison at r = 1 ("intake 20 mg, units 0.5" vs non-splittable Lipitor 20 → `strength_mismatch`).
- `anamnesis/core/reconcile.py` — item 2: new `_says_release` helper recognises `ممتد`/`بطيء` with the attached clitics (`ال`, `وال`, `بال`, `فال`, `لل`, `و`, `ف`, `ب`, `ل`), so `"ميتوبرولول الممتد"` with an explicit modified release counts as said.
- `anamnesis/core/reconcile.py` — item 3: units block moved into `_units_check(claim, pack, catalogue) -> DiscrepancyType | None`; `_pair_type` is 46 lines with a single `compared` flag.
- `tests/unit/test_reconciler_extra.py` — added `test_units_apply_when_the_intake_copies_the_tablet_strength` and `test_an_arabic_release_word_with_an_attached_article_counts_as_said` as durable cover.

`uv` cache was unusable (`Operation not permitted`), so I ran the repo `.venv` directly: `ruff check .` passes, `pytest -q` passes with 558 passed. Nothing under `tests/contract/`, `SPEC.md`, `scripts/`, `evidence/` or `docs/` was touched (the other modified files in the tree are the round-1 change, left as is).
