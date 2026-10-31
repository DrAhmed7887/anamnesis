# Batch 24, round 2: the supervisor's review of round 1

You are the builder for batch 24, round 2. Your round 1 code is still in the working tree, uncommitted: keep it and build on it. Keep each change surgical: no refactors, and nothing outside this brief.

## Goal
Make `tests/contract/test_b24_round2.py` pass, keep every other test green, and keep `tests/contract/test_b24_*.py` passing. First read the SPEC.md lines marked "round 2".

## The fixes. Each one is pinned in `test_b24_round2.py`
1. **Two lines for one ingredient never reach `match`** (`anamnesis/providers/claims.py`, `anamnesis/core/reconcile.py`). This is the safety one.
   - **The failure:** an unsaid second line ("caffeine" 65 mg beside "paracetamol" 500 mg, for Panadol) was relabelled "Panadol". The Strength duplicate check compares spellings, so it passed. The reconciler then read both lines as paracetamol, kept only the last line, and gave `match`. A junk "" or "string" line beside "bisoprolol" did the same for Concor, and which line came first decided the result.
   - **In the parser:** after relabelling and coercion, resolve each strength line's label as the reconciler does (`_resolve_inn`: a curated alias, or a catalogue brand with one INN). If the lines resolve to fewer ingredients than there are lines, drop the strength. That counts as a dropped amount, so the intake goes too.
   - **In `_identity`:** also report a conflict when a strength's lines resolve to fewer ingredients than it has lines.
   - **Pinned twice:** the contract tests both layers on their own, so both are needed.
2. **`mil` is a thousand word only next to Spanish** (`anamnesis/providers/stated.py`).
   - **When it counts:** after a Spanish number word ("dos mil"), or before a Spanish number word or a unit word ("mil doscientos", "mil miligramos").
   - **Otherwise it ends the run.** English says "five mil" for millilitres, which stated 1000 and 5000, so a 1000 mg intake reached `match`.
3. **A salt said inside a German compound is grounded** (`claims.py`).
   - **The rule:** a field is also grounded when its `(canonical_inn, salt_of)` pair equals that of a word, or of a run of up to three words, in a cited turn.
   - **Use the schema's own functions:** `anamnesis.schema.canonical_inn` and `salt_of` already read "Metoprololtartrat" as (metoprolol, tartrate).
   - **The failure it closes:** "metoprolol tartrate", said as "Metoprololtartrat", was nulled. A succinate pack then gave `match` instead of `formulation_mismatch`.
4. **Halves and the decimal words** (`stated.py`).
   - **Halves:** a Spanish or German half word (`medio`, `media`, `halb`–`halbes`, `einhalb`) joins a number before it only through `y`. Otherwise it closes the run and states 0.5 on its own: "zwei halbe Tabletten" and "two media reports" must never state 2.5. English "half" and Arabic «نص» stay as they are.
   - **The decimal words:** `coma` and `komma` are the decimal point only right after a number word in the run. Otherwise they end it, so "in a coma two years ago" never states 0.2. English `point` stays as it is.
5. **German `null` is a digit after `komma`:** "zwei Komma null fünf" is 2.05. It counts nowhere else.
6. **Decomposed accents:** `stated_amounts` normalises its text to Unicode NFC first.
7. **Amount-only labels are never grounded** (`claims.py`). In the "made only of digits, unit words or number words" check, these count as amount words too:
   - the English unit words: milligram(s), gram(s), microgram(s), millilitre(s), milliliter(s), unit(s), iu;
   - the joiners: `and`, `y`, `und`, `a`, `point`, `coma`, `komma`.

   So "milligrams", "five milligrams", "treinta y cinco" and "two and a half" are relabelled.
8. **Your unit test** in `tests/unit/test_b24_extra.py` for "a grounded label in a second cited turn" passes through the catalogue route, because bisoprolol is Concor's ingredient. Give it a `name_text` that resolves to no catalogue entry, so turn grounding itself is tested.

## Rules
- **Never create, modify or delete anything under `tests/contract/`, any `conftest.py`, `pyproject.toml` or `uv.lock`. A batch that touches them is rejected automatically.** A contract test that is skipped or xfailed fails the gate too.
- Don't edit `SPEC.md`, `scripts/`, `evidence/`, `docs/` or `finetune/`.
- Work only inside this repository. No network, no API keys, no git commits, no new dependencies.
- `uv` can't write its cache in your sandbox, so run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.
- **One test needs a local network socket that your sandbox forbids.** If it is the only failure, say so and close your goal. The gate runs outside the sandbox.
