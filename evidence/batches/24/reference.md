# Batch 24: the CEO's reference build, 29 Oct

- **Contract:** `test_b24_number_words.py` (part 1), `test_b24_grounding.py` (part 2) and `test_b24_release.py` (part 3). That's 87 tests: 77 from 11bf9de, plus 10 added in this amendment.
- **On the code before the batch:** 62 fail and 25 pass. The 25 that pass are of three kinds:
  - the "never" and "states nothing" cases, which hold today because no Spanish or German word is read yet;
  - the English and Arabic pins;
  - two guards that a naive build would break: a combination said by its brand, and a label that names the brand's own ingredient.
- **Reference build:** a scratch copy outside the repo, with all three parts done by the CEO. **2,162 passed**, ruff clean.

## What the reference build changed, before any Muse run (this commit)
1. **A SPEC error:** on its own, `einhalb` is a half (0.5), not 1.5. Only `eineinhalb` is 1.5. Pinned both ways.
2. **A conflict with English:** Spanish `once` (11) would make "I take it once a day" state 11, which `test_english_and_arabic_are_unchanged` forbids. So `once` is left out, and that's pinned.
3. **Grounding labels by the turns alone broke three older pins:**
   - `test_b8_claims.py::test_parse_splits_salts_through_the_schema`;
   - `test_b21_media_fixes.py::test_a_combination_strength_said_in_words_is_kept`;
   - `tests/unit/test_stated_extra.py::test_claim_strength_kept_only_when_every_ingredient_is_stated`.

   Relabelling Augmentin's two labels to "Augmentin" made the strength invalid, and "Bisoprolol fumarate" lost its salt. The 29 Oct plan grill had warned about combination names (finding #3).
   - **The fix:** an amount label is now also grounded when it names an ingredient of the catalogue entry that the claim's name resolves to. The claim's own `inn` is still grounded by the turns only.
   - **Three pins added:** the brand's own ingredient is kept, a wrong ingredient is relabelled, and a combination is kept.
4. **Hundreds:** "cinco cien" would state 105. Spanish hundreds and one-word German hundreds now close a run that already holds a number. On their own, `hundert` and `tausend` are multipliers, so "fünf hundert" is 500. Both are pinned.
5. **Smaller fixes:**
   - "treinta y un miligramos" states 31, pinned;
   - the multiplier before `tausend` or `hundert` is `ein`–`neun`;
   - SPEC §2's known-limits line no longer says that Spanish number words state only their parts.

## One mutant per behaviour
Each mutant was applied alone to the reference build, and the contract catches every one. The count is the failures in `tests/contract`.

| Mutant | Failures |
|---|---|
| Spanish `y` joins any two numbers | 1 |
| A German number may be a token's prefix | 8 |
| `einhalb` read as 1.5 (the old SPEC line) | 2 |
| Articles always count as 1 | 3 |
| The claim's `inn` isn't grounded | 1 |
| An empty strength still counts as a dropped amount | 2 |
| Labels grounded by the turns only (no catalogue route) | 4 |
| A unit or number label can be grounded | 1 |
| No Spanish release word | 1 |
| Glucophage keeps immediate release | 2 |

## Found, not fixed here
- **A brand outside the catalogue, said with a strength, becomes its own ingredient.** `_identity` reads an unknown label as an INN.
- **What follows:** such a claim is reported as `missing_modality`, not `unresolved_name`, and it can't pair with its photographed pack. This already happens today when the model labels an amount with the brand. Batch 24 makes it more frequent, because an unsaid INN is no longer kept.
- **It fails safe:** no false `match`.
- **The live cases S1 and G3** are amended for it in `manifest.md`.
