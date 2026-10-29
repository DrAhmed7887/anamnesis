# Batch 24, round 6: one structural rule for Spanish and German

You are the builder for batch 24, round 6. Your round 1–5 code is still in the working tree, uncommitted: keep it and build on it. Keep each change surgical: no refactors beyond what this brief asks, and nothing outside it.

## Why this round is different
Five review rounds each found a new Spanish or German idiom that stated a number nobody said, and an invented amount of that number then reached a false `match`. Examples: "a las diez treinta" (10:30) became 40, "um halb zwei" 2.5, "por ciento" 100, "vier Ein-Gramm-Tabletten" 5, and "ich gebe Acht" 8. So round 6 replaces that game with one rule.

## Goal
Make `tests/contract/test_b24_round6.py` pass, and keep every other test green, including all of `tests/contract/test_b24_*.py`. Several of those earlier files changed in this contract commit, so read them again. Also read the SPEC.md lines marked "round 6".

## The rules (`anamnesis/providers/stated.py`)
1. **A Spanish or German number states an amount only before a unit or dose word.**
   - **Which runs it covers:** a run of number words that holds a Spanish or German word. That means a Spanish or German number, an article (`un`, `una`, `ein`–`einer`), a Spanish or German half, `mil`, `coma`, `komma`, `hundert` or `tausend`.
   - **When such a run counts:** its values, and its words' own values, count only when the token right after the run is a unit or dose word.
   - **The unit and dose words:**
     - the unit words already listed;
     - `milligram(s)`, `gram(s)`, `microgram(s)`, `millilitre(s)`, `milliliter(s)`;
     - the Spanish dose words;
     - `tablette`, `tabletten`, `filmtablette`, `filmtabletten`, `retardtablette`, `retardtabletten`, `kapsel`, `kapseln`, `retardkapsel`, `retardkapseln`, `dragee`, `dragees`.
   - **Anywhere else, or at the end of a part, the run states nothing.**
   - **Decimals:** "dos coma cinco miligramos" counts, decided by the token after its last digit.
   - **What it changes:** "Panadol de quinientos", "tengo cuarenta años", "a las dos", "veinte por ciento" and "ich gebe Acht" state nothing.
   - **What still counts:** "quinientos miligramos" 500, "acht Tabletten" 8, "medio comprimido" 0.5, "zweieinhalb Tabletten" 2.5.
   - **A run of only English or Arabic words is exactly as before.** "Concor five" still states 5.
2. **German number words never combine.** A German number token never joins a number before it; close the run first.
   - `hundert` and `tausend` on their own are the plain numbers 100 and 1000, no longer multipliers.
   - So "fünf hundert Milligramm" states 100 (the 5 has no unit after it), never 500. "um sechs hundert Milligramm" never states 600, and "seit zweitausendzehn fünf Milligramm" never 2015.
   - `parse_amount_text` stays as it is: a bare "hundert" still doesn't parse.
3. **An article joins no number before it.** An article that counts as 1 before a unit gets the same close as a Spanish number under 100 after another: "vier Ein-Gramm-Tabletten" states 1, never 5. The `y` exception stays, so "treinta y un miligramos" is still 31.

The earlier special cases (`mil`, `medio`/`media`, `por ciento`, `Acht`, clock times) may stay. Rule 1 covers them now, but they do no harm.

## Rules
- **Never create, modify or delete anything under `tests/contract/`, any `conftest.py`, `pyproject.toml` or `uv.lock`. A batch that touches them is rejected automatically.** A contract test that is skipped or xfailed fails the gate too.
- Don't edit `SPEC.md`, `scripts/`, `evidence/`, `docs/` or `finetune/`.
- Work only inside this repository. No network, no API keys, no git commits, no new dependencies.
- `uv` can't write its cache in your sandbox, so run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.
- **One test needs a local network socket that your sandbox forbids.** If it is the only failure, say so and close your goal. The gate runs outside the sandbox.
