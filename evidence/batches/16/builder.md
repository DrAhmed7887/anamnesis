muse muse-spark-1.3, batch 16, started 2026-10-27T14:58:15Z
muse: workspace root: <repo> (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Done. `uv run ruff check .` passes and `uv run pytest -q` passes: 508 passed (55 in the batch-16 contract file plus my new unit file).

Files changed (the two untracked `docs/` files were already there, not mine):
- New [anamnesis/providers/numbers.py](anamnesis/providers/numbers.py): shared `parse_amount_text` plus `coerce_strength`.
- Edited [anamnesis/providers/claims.py](anamnesis/providers/claims.py): advice, grounding, and null-coercion in `parse_claims_json`.
- Edited [anamnesis/providers/spark.py](anamnesis/providers/spark.py): advice, country, and strength handling in `parse_label_json`.
- New [tests/unit/test_model_replies_extra.py](tests/unit/test_model_replies_extra.py): 7 focused unit tests.

Per numbered change:
1. `parse_amount_text` accepts `"2.5"`/`"2,5"` (comma only with 1–2 trailing digits, so `"1,000"` → None) and returns None for ranges, words, empty, zero, and negatives. Non-string numerics are handled too (ints/Decimals pass through with the positivity check; bools → None).
2. Null-coercion happens before pydantic validation: each regimen field independently, `intake_amount` (bad amount or failed `IngredientAmount` validation → null), and `strength` via shared `coerce_strength` (any bad amount, or `Strength` rejection such as duplicate canonical INNs → null). Other claims are unaffected.
3. Grounding: `normalise(name_text)` must be a substring of `normalise(transcript)` for a cited turn, else retryable `ProviderError("spark", ...)`, same envelope as the uncited-turn error.
4. Country kept only on full match of two ASCII letters, stored upper-case; else null.
5. `assert_no_advice` (reused, no new blocklist) runs on raw strings: claim `name_text`, claim `inn`, intake `inn`, all strength ingredient `inn`s, and label `inn` plus its ingredient `inn`s. `label_text` exempt. Hits become retryable `ProviderError`; the offending text is not echoed in the error.

One thing in the brief I stretched slightly: for `intake_amount` the brief says null when the amount "doesn't parse", but I also null it when `IngredientAmount` validation fails for any other reason (e.g. bad unit). That matches the brief's "one bad field never drops the other claims" principle, and no contract test pins the narrower behavior. Also note: `uv` needed `UV_CACHE_DIR=/tmp/uv-cache` because the default `~/.cache/uv` is not writable in this environment.

## Round 2
muse muse-spark-1.3, batch 16 round 2, started 2026-10-27T15:08:14Z
muse: workspace root: <repo> (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
All four items fixed. `uv run ruff check .` passes and `uv run pytest -q` passes with 518 tests.

Files changed, one line per item:

1. Blocker — [anamnesis/providers/claims.py](anamnesis/providers/claims.py): in `parse_claims_json`, when the reply sent a non-null `strength` or `intake_amount` and either coerces to null, both are set to null.
2. Numbers — [anamnesis/providers/numbers.py](anamnesis/providers/numbers.py): `parse_amount_text` returns `None` for a dot followed by exactly three digits with a non-zero whole part (`"1.000"`); `"0.125"` still parses.
3. Advice-check order — [tests/unit/test_model_replies_extra.py](tests/unit/test_model_replies_extra.py): three new tests proving `{"inn": "bisoprolol; take two", "amount": "five"}` raises retryable `ProviderError` from `parse_claims_json` (strength ingredient and `intake_amount`) and from `parse_label_json` (strength ingredient), i.e. advice fires before the unparseable amount is dropped.
4. Tidy — [anamnesis/core/guardrails.py](anamnesis/core/guardrails.py) gained shared `assert_no_advice_in_ingredients`, now called by both parsers (copies removed from [claims.py](anamnesis/providers/claims.py) and [spark.py](anamnesis/providers/spark.py)); `parse_label_json` builds the validated input as one new dict instead of mutating the parsed dict in place.

Final test count: 518 passed.
