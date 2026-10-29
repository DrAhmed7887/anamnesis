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

## Round 2, after the supervisor's review of round 1
- **Contract:** `test_b24_round2.py`, 26 tests. On Muse's round 1 code, 17 fail and 9 pass.
- **Reference build:** the CEO's round 1 reference had the same three serious holes (findings 1–3), because they came from the SPEC. With round 2's fixes it passes **2,188**, ruff clean.

**One mutant per fix** (failures in `tests/contract`):

| Mutant | Failures |
|---|---|
| The parser keeps two lines for one ingredient | 1 |
| The reconciler accepts two lines for one ingredient | 1 |
| `mil` is always a thousand | 4 |
| No salt-pair grounding | 1 |
| Halves join any number | 2 |
| `coma` is a decimal point anywhere | 1 |
| `null` is no digit | 1 |
| No NFC | 2 |
| English unit words ground a label | 2 |

Each layer of finding 1 is pinned on its own, so neither can be dropped.

## Round 3, after the supervisor's review of round 2
- **Contract:** `test_b24_round3.py`, 18 tests. On Muse's round 2 code, 13 fail and 5 pass.
- **Reference build:** **2,206 passed**, ruff clean.

**One mutant per fix** (failures in `tests/contract`):

| Mutant | Failures |
|---|---|
| A half anywhere | 5 |
| `mil` before any unit word | 3 |
| Number words that need a neighbour ground a label | 5 |

## Round 4, after the supervisor's review of round 3
- **Contract:** `test_b24_round4.py`, 26 tests. On Muse's round 3 code, 18 fail and 8 pass.
- **Reference build:** **2,232 passed**, ruff clean.
- **A sweep of 66 everyday Spanish and German phrases** found one more of the same kind: the clock time "a las dos y media". It is pinned.

**One mutant per rule** (failures in `tests/contract`):

| Mutant | Failures |
|---|---|
| A half keeps its run open | 6 |
| "por ciento" states 100 | 2 |
| `un`/`una` count again before `medio` | 4 |
| `sobre` is a dose word again | 3 |
| Any `y` before `medio` | 1 |
| No clock-time exception | 3 |
| A one-letter word grounds as a prefix | 1 |

The first clock-time check the reference had was redundant, so no test caught its mutant (0 failures). That copy was removed, and the remaining check is pinned.

## Round 5, after the supervisor's review of round 4
- **Contract:** `test_b24_round5.py`, 23 tests. On Muse's round 4 code, 17 fail and 6 pass.
- **Reference build:** **2,255 passed**, ruff clean.

**One mutant per fix** (failures in `tests/contract`):

| Mutant | Failures |
|---|---|
| Adjacent number words add up | 9 |
| The `y` joins a half after a clock hour | 3 |
| `Acht` is always eight | 3 |
| No NFC on the field and the turns | 1 |
| "una y media" is only 1 | 1 |

## Round 6: one structural rule for Spanish and German
- **The rules:**
  - a Spanish or German run states its values only before a unit or dose word;
  - German number words never combine, and `hundert` and `tausend` are plain numbers;
  - an article joins no number.
- **Contract:**
  - `test_b24_round6.py`, 35 tests. On Muse's round 5 code, 22 fail and 13 pass.
  - Earlier tests that said bare Spanish or German numbers now say them with a unit or dose word.
  - "fünf hundert Milligramm" now states 100, never 500.
- **Reference build:** **2,289 passed**, ruff clean.
- **Differential:** English and Arabic give exactly the results of 843f64f on all 21,747 fuzz phrases.
- **Fine-tune re-score:** unchanged.

**One mutant per rule** (failures in `tests/contract`):

| Mutant | Failures |
|---|---|
| A Spanish or German run counts anywhere | 16 |
| German numbers combine | 1 |
| An article joins the number before it | 4 |
| `hundert` multiplies again | 3 |

## Round 7: the amount rule, whatever closes the run
- **Contract:** `test_b24_round7.py`, 13 tests. On Muse's round 6 code, 6 fail and 7 pass.
- **Reference build:** **2,302 passed**, ruff clean.
- **Differential:** English and Arabic give exactly the results of 843f64f on all 21,747 fuzz phrases.
- **A fix to the reference itself:** an English "hundred" after a Spanish number stated the Spanish part without an amount. It is fixed and pinned.

**One mutant per rule** (failures in `tests/contract`):

| Mutant | Failures |
|---|---|
| A Spanish or German word adds an English one after it | 4 |
| The English-hundred cut states the Spanish part | 1 |
| A decimal with Spanish or German digits counts anywhere | 2 |
