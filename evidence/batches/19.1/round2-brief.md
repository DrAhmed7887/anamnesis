# Batch 19.1, round 2: fix the supervisor's findings

You are the builder for batch 19.1 of Anamnesis, round 2. Your round-1 change is in the working tree, uncommitted (`anamnesis/brief_html.py`, `anamnesis/core/guardrails.py`, `anamnesis/core/overlap.py`, `anamnesis/core/reconcile.py`, `anamnesis/providers/numbers.py`, `anamnesis/schema/templates.py`, `tests/unit/test_brief_extra.py`, `tests/unit/test_qm_fixes_extra.py`). An independent supervisor reviewed it. Fix the items below and keep everything else as it is.

The contract `tests/contract/test_b19_1_qm_fixes.py` has new cases at the end ("round 2"). SPEC.md changed in §2 (the new bullet "A label reply's strength carries no key beyond `LABEL_SCHEMA`'s", and one sentence on whole words after the Arabic advice words) and in §7 (the two sides now include the scalar `inn`; the cross-medication bullet on conflicted claims). Read those first.

1. **Blocker: no model-written salt on the brief.** `IngredientAmount.salt` is a declared field, so `parse_label_json` accepts a `"salt"` key in a strength ingredient. Since round 1, that model text reaches the brief with no advice check. In `anamnesis/providers/spark.py`, before the strength is coerced, refuse two things:
   - any `strength` key beyond `ingredients`, `per`, `release`;
   - any ingredient key beyond `inn`, `amount`, `unit` (a subset is fine: a missing `release` still defaults to `unknown`).

   Raise `ValueError` inside the existing `try`, so the reply becomes the usual retryable "malformed label reading". Salts then reach a pack only through the curated split of `inn`. Contract: `test_a_label_strength_with_keys_beyond_the_schema_is_malformed`, `test_a_pack_salt_comes_only_from_the_curated_split`.
2. **A conflicted claim counts by what its readings share.** Round 1 skips every conflicted claim, which hides a real duplicate: "Panadol" with a paracetamol + caffeine strength, plus Gelocatil. Instead, when `_claim_identity` reports a conflict:
   - intersect its identity set with the INNs of `catalogue.resolve(claim.name_text)`;
   - skip the claim when the name doesn't resolve (None) or the intersection is empty;
   - otherwise count it with the intersection.

   Contract: `test_a_conflicted_claim_counts_by_the_ingredients_its_readings_share`. Round 1's case still holds: "Concor" with a metoprolol strength shares nothing with bisoprolol and doesn't count.
3. **The scalar `inn` on both sides.** Rule 6 also takes salts from `salt_of(inn)`, and the brief shows neither the claim's nor the pack's scalar `inn`. When one is present, add a row with it, verbatim and escaped, with `dir="auto"`, on the patient side and on the pack side. Label the row with a new fixed `FIELD_INN = "Ingredient"` in `templates.py`, and add that string to your advice test. Contract: `test_a_salt_named_only_in_the_inn_field_shows_on_both_sides`.
4. **Whole words.** The Arabic advice words must still match only as whole words: "يتناول", "المتناول", "تناولت الدواء" and "أخذ" pass. Contract: `test_arabic_advice_words_match_only_as_whole_words`. Keep your current boundaries; this pins them.
5. **One clitic list.** The Arabic clitic alternation `(?:وال|بال|فال|لل|ال|و|ف|ب|ل)?` is now written in `catalogue.py`, `reconcile.py` (`_RELEASE_CLITICS`) and `guardrails.py`. Define it once in `anamnesis/core/catalogue.py`, for example as `ARABIC_CLITICS`, and use it in all three places with the same behaviour. Remove the six Arabic words from the raw-text `_ADVICE` pattern, since the normalised check already catches every raw hit.

## Rules (same as round 1)
- **Never create, modify or delete anything under `tests/contract/`.**
- Don't edit `SPEC.md`, `scripts/`, `evidence/` or `docs/`. No network, no API keys, no git commits, no new dependencies.
- Run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass, and `git status --porcelain tests/contract` prints nothing. Reply with the files you changed, one line per numbered item, the final test count, and anything in this brief you think is wrong.
