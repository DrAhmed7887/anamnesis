# Batch 21, part 1: reference build and mutation checks (CEO, before Muse runs)

The contract was proven passable on a throwaway scratch copy of this branch before Muse saw it.

- **Before the build** (this branch): 13 contract cases fail, the ones for the digit sets, the thousands sign and the question. The two pins already pass, and 908 tests pass in all.
- **Reference build:** three one-line changes (`_AMOUNT_RE`, `_DIGIT_RUN`, `PATIENT_QUESTIONS["formulation"]`) plus the one stale unit case in `tests/unit/test_stated_extra.py`. Result: **921 passed**, ruff clean.
- **Mutants**, each run against the new contract and then restored:

| Mutant | Result |
|---|---|
| Patient Ingredient row not escaped | caught |
| Patient Ingredient row without `dir="auto"` | caught |
| Pack Ingredient row not escaped | caught |
| Pack Ingredient row without `dir="auto"` | caught |
| Free-text salts ignored (`_text_salts` returns nothing) | caught |

The supervisor's two 19.1 mutants (unescaped rows, no `dir="auto"`) passed all 707 tests then. They now fail the contract.

## Part 2 (contract lock 6ad7021): reference build
- **Before the build:** 47 part-2 cases fail and 7 pins pass. Every failure is an assertion, never an error. The Norvasc pairing case fails in both pack orders.
- **Reference build:** a scratch copy with these changes:
  - the number-word split in `_word_amounts`;
  - `<bdi dir="ltr">` in `_ingredient_html`;
  - the two prompt sentences;
  - 35 `INN_ALIASES` entries;
  - one extra score-3 case in `_pair_score`.
- **Result: all contract tests pass, 973 tests in all.** Two failures remain, both expected:
  - Muse's own two unit tests that compare the exact strength-row string. Brief item 6 tells Muse to update them.
  - Two E501 long lines in the scratch prompt edit. Brief item 7 asks for wrapped strings.
