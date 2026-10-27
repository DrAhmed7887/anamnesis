# Batch 20, round 2: fix the supervisor's findings

You are the builder for batch 20 of Anamnesis, round 2. Your round-1 change is in the working tree, uncommitted (`anamnesis/brief.py`, `anamnesis/brief_html.py`, `anamnesis/providers/claims.py`, `anamnesis/providers/meta.py`, `anamnesis/providers/spark.py`, `anamnesis/providers/stated.py`, `anamnesis/review.py`, `anamnesis/schema/report.py`, `anamnesis/schema/review.py`, `anamnesis/schema/templates.py`, `tests/unit/test_review_extra.py`, `tests/unit/test_stated_extra.py`). An independent supervisor reviewed it. Fix the items below and keep everything else as it is.

**Two things changed since round 1:**
- **Your `pyproject.toml` change was reverted.** The I001 failure was the contract's fault, and the contract's import is now wrapped. Don't touch `pyproject.toml`.
- **The contract has new cases.** They are at the end of `tests/contract/test_b20_stated_amounts.py` and `tests/contract/test_b20_review.py`, under "round 2". SPEC.md changed in four places marked "supervisor 20" (§2 runs and labels, §8 `add_photo`). Read those first.

1. **A non-string `label_text` is a malformed reply** (`anamnesis/providers/spark.py`). Today `stated_amounts(data.get("label_text") or "")` raises `AttributeError` on `5`, a list or a dict. That escapes the parser and crashes the whole intake after the call was charged.
   - Fix: inside the existing `try`, raise `ValueError` when `label_text` is neither a string nor None, before `stated_amounts` sees it. It then becomes the usual retryable "malformed label reading".
   - Contract: `test_a_label_text_that_is_not_a_string_is_a_malformed_reply`. Add a unit test that runs such a reply through `run_intake` and expects a `read` step with `error: spark ProviderError`.
2. **`add_photo` refuses a review of another report** (`anamnesis/review.py`). Make it the first refusal: `review.intake_id != report.intake_id` raises `ValueError`. Today, a review made for report A can answer a request on report B and supersede one of B's packs that was read clearly. Contract: `test_a_review_of_another_report_cannot_answer_a_request`.
3. **Regions unique by `region_id`.** De-duplicate the new photo's regions by `region_id` before they join the report, as `run_intake` does. Contract: `test_a_region_found_twice_is_kept_once`.
4. **Only positive values** (`anamnesis/providers/stated.py`). The `point` branch adds its value without the positive check, so "zero point zero" states 0.0. Contract: `test_a_point_decimal_that_is_zero_states_nothing`.
5. **A run of number words ends at punctuation.** `catalogue.normalise` strips punctuation, so "Concor five, two tablets" states 7.
   - Fix: split the raw text at `, . ; : ! ? ، ؛ ؟` and line breaks, and run the word pass on each part separately.
   - A hyphen and a slash don't split.
   - **The digit pass stays on the whole text**, so "2.5", "2,5", "1,000" and "0.125" behave exactly as before. Don't split the text before the digit regex.
   - Contract: `test_a_run_of_number_words_ends_at_punctuation`.
6. **Tidy `add_photo`.**
   - Prepare the new photo once: today `_prepare([photo])` runs twice.
   - Use the loop's `_NEEDS_ZOOM` instead of listing the two readabilities again.
   - Compute the review status in one private helper used by every function that sets it.
   - Don't change `anamnesis/agent/loop.py`.

## Rules (same as round 1)
- **Never create, modify or delete anything under `tests/contract/`.** Don't edit `pyproject.toml`.
- Don't edit `SPEC.md`, `scripts/`, `evidence/` or `docs/`. No network, no API keys, no git commits, no new dependencies.
- Run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass, and `git status --porcelain tests/contract` prints nothing. Reply with the files you changed, one line per numbered item, the final test count, and anything in this brief you think is wrong.
