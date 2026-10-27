# Batch 3 review: hardening from the M1 grill

Reviewer: Claude Code (Opus 5.5). Builder: codex `gpt-6-sol`, 58,878 tokens. Gate: pass, 133 tests (up from 81). The reviewer revised the b1 and b2 contracts for the v2 rules in the contract commit; the builder didn't touch them.

Verdict: PASS

## Checked against SPEC.md §2–3 v2 and `evidence/grills/m1-core/effect.md`
- **#1, rule 7 fallthrough:** a pair with nothing comparable now gives `insufficient_information`, never `match`. ✅
- **#2, Beloc-Zok ER trap:** release comes from the explicit strength, otherwise from a **brand** match only. Unknown against modified gives `insufficient_information`; immediate against modified gives `formulation_mismatch`. ✅
- **#3, splittability per product:** capsules and `splittable: false` give `strength_mismatch`; `null` gives `insufficient_information`; `ml` and `dose` units give `insufficient_information`. ✅
- **#4:** the intake check now runs after a strength match. ✅
- **#5:** `Finding` rejects any note or question id that isn't the canonical template. Side IDs must match the evidence. The templates moved to `schema/templates.py`, and `guardrails` re-exports the same objects. ✅
- **#6, pairing:** candidates are scored 3, 2 or 1, and ties are broken by **ID**. Only readable packs pair. The permutation test (144 orders) passes. ✅
- **#7:** identity comes from the strength's ingredients when present, and a name/strength conflict gives `insufficient_information`. `canonical_inn` handles synonyms, and duplicate INNs are rejected. ✅
- **#8:** hyphens and slashes count as spaces, and text naming 2+ products resolves to `None`. ✅
- **#12, #13:** `as_needed` is tri-state, and `transcript` and `speaker` must be non-empty. ✅

## Deviation, accepted
- Ties in pairing are broken by `claim_id`/`observation_id` instead of list index. That's better than the spec, because breaking ties by index would reintroduce order dependence. SPEC updated on this branch.

## Notes (not blocking)
- The synonym `acetaminophen → paracetamol` is hard-coded in both `canonical_inn` and `Catalogue._matches`. Extract one `INN_SYNONYMS` table when the catalogue grows.
- The `Finding` validator imports `templates` inside the function to avoid a circular import. It works; revisit if the schema package grows.
- The builder said "no existing unit tests needed changes". Only an import line changed; everything else was additions. Accurate.
