# Batch 16, round 2: fix the supervisor's findings

You are the builder for batch 16 of Anamnesis, round 2. Your round-1 change is in the working tree, uncommitted: `anamnesis/providers/numbers.py` (new), `anamnesis/providers/claims.py`, `anamnesis/providers/spark.py` and `tests/unit/test_model_replies_extra.py`. An independent supervisor reviewed it. Fix the items below and keep everything else as it is. The contract `tests/contract/test_b16_model_replies.py` now has two more tests, and SPEC.md §2 "Model replies (batch 16)" has the updated rules: read both first.

1. **Blocker.** SPEC: "A dropped claim amount takes the other one with it." In `parse_claims_json`, when a claim's reply sent a non-null `strength` or a non-null `intake_amount` and either one is dropped (becomes null), set both to null, so the claim can't reach `match` on what is left. Contract: `test_a_dropped_claim_amount_takes_the_other_with_it_so_nothing_false_matches`.
2. **Numbers.** A dot followed by exactly three digits with a non-zero whole part (`"1.000"`, `"2.500"`, `"10.000"`) is ambiguous, like `"1,000"`, and returns `None`; `"0.125"` and `"12.5"` still parse. Contract: `test_a_dot_before_exactly_three_digits_is_ambiguous_unless_the_whole_part_is_zero`.
3. **Pin the advice-check order** with unit tests in `tests/unit/test_model_replies_extra.py`: an ingredient `{"inn": "bisoprolol; take two", "amount": "five"}` must raise a retryable `ProviderError` from `parse_claims_json` (as a strength ingredient, and as the `intake_amount`) and from `parse_label_json` (as a strength ingredient). The advice check runs on the raw strings before any field is dropped.
4. **Tidy:**
   - Use one shared helper to collect the ingredient `inn` strings and run `assert_no_advice`, called by both parsers, instead of the two copies.
   - In `parse_label_json`, don't modify the parsed dict in place; build the validated input as one new dict.

## Rules (same as round 1)
- **Never create, modify or delete anything under `tests/contract/`.**
- Don't edit `SPEC.md`, `scripts/`, `evidence/` or `docs/`. No network, no API keys, no git commits, no new dependencies.

## Done when
`uv run ruff check .` and `uv run pytest -q` both pass from the repo root. Reply with the files you changed, one line per numbered item, and the final test count.
