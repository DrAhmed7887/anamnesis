# Batch 7 review: curated salt-to-moiety mapping

Builder: codex `gpt-6-sol`, **cut off by the provider's rate limit** (`429 Too Many Requests` after 25,789 tokens; most likely today's Sol quota of 60 messages, spent on batches 2–5). Its finished part, the `INN_ALIASES` table plus `IngredientAmount.salt`, was kept. Claude Code finished the rest, as the plan allows when a quota runs out. Gate: pass, 222 tests.

Verdict: PASS

## Split of work
- **Sol:** the curated `INN_ALIASES` (alias → moiety, salt), `canonical_inn` / `salt_of`, the `"(as …)"` label form, and `IngredientAmount.salt` filled by a `mode="before"` validator that returns a new dict. ✅ Reviewed: the aliases cover only catalogue moieties, and unknown suffixes are never stripped.
- **Claude Code:**
  - exported `salt_of` and `INN_ALIASES`
  - catalogue resolution now matches every alias of a single-INN entry, replacing the hard-coded `acetaminophen` case (closes the batch 3 note)
  - the formulation gate returns `formulation_mismatch` when both sides name different salts of one ingredient
  - `tests/unit/test_salts_extra.py`

## Checked
- The **real Spark readings from 27 Oct** (`tests/fixtures/spark_labels_live_2026-10-27.json`) now pair. Concor gives `match`; Beloc-Zok against "metoprolol 50 twice a day" gives `intake_differs_from_unit_strength`. Before, every finding was `missing_modality`. ✅
- Metoprolol succinate vs tartrate at equal mg gives `formulation_mismatch`. ✅
- A salt name never implies a brand release ("metoprolol succinate" alone stays `unknown`), so a salt can't sneak in an ER assumption. ✅
- An unknown suffix ("metoprolol extra") stays a different ingredient, which surfaces as a conflict instead of matching silently. ✅

## Note
- `LABEL_SCHEMA` has no `salt` field. Spark keeps reporting the full name, and the validator splits it, so the salt stays grounded in what is printed on the pack.
