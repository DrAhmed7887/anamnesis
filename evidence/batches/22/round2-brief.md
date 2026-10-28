# Batch 22, round 2: fix the supervisor's findings

You are the builder for batch 22 of Anamnesis, round 2. Your round-1 change is in the working tree, uncommitted. An independent supervisor reviewed it, in `evidence/batches/22/supervisor.md`. Fix the items below and keep everything else as it is.

The new contract is `tests/contract/test_b22_round2.py`. SPEC.md changed in two places: one sentence at the end of the **Numbers** bullet in §2, and the **Spend** bullet of the §4 subsection "Open-weight label reader". Read those first.

1. **A word amount must be bare** (`anamnesis/providers/numbers.py`, `parse_amount_text`). Today `catalogue.normalise` runs first and turns punctuation into spaces and strips tashkeel, so "<five", "-five", "five?", "(five)" and «خُمس» (a fifth) all parse as 5. "I take Concor, less than five milligrams" then reaches `match`.
   - Before `normalise`, require the stripped text to be letters only, tatweel allowed. Suggested: `_WORD_RE = re.compile(r"(?:[^\W\d_]|ـ)+")` and `if not _WORD_RE.fullmatch(value.strip()): return None`, in place of the one-token check.
   - Remove any check this makes dead.
2. **Refuse a contributor model wherever the word is** (`anamnesis/providers/openweight.py`, `OpenWeightLabelReader.__init__`): `-contributor` anywhere in the id, in any case, surrounding whitespace ignored. For example `"-contributor" in model.strip().casefold()`.
3. **The reader's own errors name its provider** (`openweight.py`, `read`): the malformed-response error, the length-stop error and the label-parse error pass `self.client.provider`, never `"spark"` or `exc.provider`. Their message text can stay as it is.
4. **Don't copy `_data_url`** (`openweight.py`): import it from `anamnesis/providers/meta.py`, and drop any import this leaves unused.
5. **Unit tests** in `tests/unit/test_b22_extra.py`: add None cases for the inputs in item 1, and two of the model ids in item 2.

## Rules
- **Never create, modify or delete anything under `tests/contract/`. A batch that touches it is rejected automatically.**
- Don't edit `SPEC.md`, `scripts/`, `evidence/` or `docs/`. Work only inside this repository. No network, no API keys, no git commits, no new dependencies.
- `uv` can't write its cache in your sandbox, so run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass from the repo root, and `git status --porcelain tests/contract` prints nothing. Reply with a short report: the files you changed, what you did for each numbered item, the final test count, and anything in this brief you think is wrong.
