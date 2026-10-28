muse muse-spark-1.3, batch 22, started 2026-10-28T10:23:53Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Batch 22 done. All gates pass: `.venv/bin/ruff check .` clean, `.venv/bin/python -m pytest -q` → **1075 passed**, `git status --porcelain tests/contract` prints nothing.

Files changed:
- [openweight.py](anamnesis/providers/openweight.py) (new) — items 1–3
- [base.py](anamnesis/providers/base.py) — item 4
- [numbers.py](anamnesis/providers/numbers.py) — item 5
- [test_b22_extra.py](tests/unit/test_b22_extra.py) (new) — 19 unit tests

Per numbered change:
1. `OpenWeightClient` subclasses `MetaClient` (60 s default timeout); `post` reuses the inherited path and rewrites only `ProviderError.provider` to `"fireworks"`/`"baseten"`. `MetaClient` untouched.
2. `PRESETS` with the exact Fireworks/Baseten base URLs, model ids, and `json_mode` flags.
3. `OpenWeightLabelReader` mirrors `MetaLabelReader`: imported `_SYSTEM_PROMPT`, identical user text/image, `max_tokens` 4000, no `reasoning_effort`, same `response_format` when `json_mode`, sorted-schema sentence plus one-fence strip without it, `parse_label_json`, `spark_call_estimate` on a `price_key`-swapped copy while sending the real model id, trace/ledger named `price_key`, length stop non-retryable, `with_one_retry`, `-contributor` refused.
4. Both `muse-spark-open@…` prices added ($1.25/$4.25 per 1M).
5. `parse_amount_text` falls back for a single non-digit token: `catalogue.normalise`, then `ENGLISH_NUMBERS`/`ARABIC_NUMBERS`/`_combined_hundreds` when > 0, via function-level imports. `stated.py` untouched.

Two notes on the brief: error *messages* still read "Meta …" ("malformed Meta response JSON") since behavior is inherited verbatim — only the `provider` field names fireworks/baseten, which is all the brief requires. And "five," (trailing punctuation) parses as 5 because `normalise` strips punctuation; the brief doesn't specify that edge, so I followed it literally.

## Round 2
muse muse-spark-1.3, batch 22 round 2, started 2026-10-28T10:46:39Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Done. `ruff check .` passes, `pytest -q` gives 1122 passed, `git status --porcelain tests/contract` prints nothing.

Files changed:
- [numbers.py](anamnesis/providers/numbers.py)
- [openweight.py](anamnesis/providers/openweight.py)
- [test_b22_extra.py](tests/unit/test_b22_extra.py)

Per item:
1. Added `_WORD_RE = re.compile(r"(?:[^\W\d_]|ـ)+")`; the fallback branch now returns None unless `value.strip()` fully matches, replacing the one-token check. Removed the post-`normalise` split check (dead: a split result misses the dicts anyway).
2. `__init__` now refuses with `"-contributor" in model.strip().casefold()`.
3. Malformed-response, length-stop, and label-parse errors all pass `self.client.provider`; message text unchanged.
4. Deleted the local `_data_url`, imported it from `anamnesis.providers.meta`; dropped the now-unused `base64` import.
5. Added `test_a_qualified_or_vowelled_word_does_not_parse` (`<five`, `-five`, `five?`, `(five)`, `خُمس`) and `test_a_contributor_model_is_refused_anywhere` (`muse-spark-open-Contributor`, `accounts/fireworks/models/muse-spark-open-contributor:latest`).

Nothing in the brief looks wrong.
