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
