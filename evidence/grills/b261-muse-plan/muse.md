muse: workspace root: <repo>/.muse/worktrees/20261030-7749 (cwd default)
muse: warning: rules file at <repo>/CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
## 1. Verdict on the draft

Accept: add opt-in `reasoning_effort`, default None, live Fireworks passes `low` (`anamnesis/providers/openweight.py:60`).

## 2. Risks

1. Estimate drift: estimate is built from the body (`anamnesis/providers/openweight.py:99`, `anamnesis/providers/meta.py:309`). Action: pin that `low` changes only the body key, and `guard.check` sees the same pre-call estimate.
2. Body pins: batch 22 asserts messages and `response_format` equal Spark's (`tests/contract/test_b22_openweight.py:78`). Action: assert None sends no `reasoning_effort` key and `low` adds only that key to today's body (`anamnesis/providers/openweight.py:84`).
3. Cut-short reply: `finish_reason == "length"` is non-retryable with one charged trace (`anamnesis/providers/openweight.py:123`, `tests/contract/test_b22_openweight.py:179`). Action: keep this under `low`; a truncated JSON must stay `length`, not become a parse retry.
4. Malformed retry unchanged: parse failure raises retryable and `with_one_retry` charges both attempts (`anamnesis/providers/openweight.py:131`, `tests/contract/test_b22_openweight.py:110`). Action: keep one retry; watch whether `low` raises malformed rate on the eval.
5. Live/eval mismatch: live forces `json_mode=False` (`scripts/intake_live.py:131`) while the Fireworks preset is True (`anamnesis/providers/openweight.py:14`) and the eval uses the preset (`scripts/reader_eval.py:86`). Action: decide explicitly; the live `low` result tests `low` plus no-JSON-mode only.
6. Baseten unknown field: Fireworks documents `reasoning_effort` and JSON mode (`docs/muse/muse-spark-open.md:26`); Baseten documents no structured outputs (`docs/muse/muse-spark-open.md:24`). Action: refuse non-None effort on Baseten or pin its 400 path, not just leave it None by convention.
7. Value validation: documented values are `low`/`medium`/`high`/`xhigh` (`docs/muse/muse-spark-open.md:34`); Spark 1.3 sends `low` (`anamnesis/providers/meta.py:296`). Action: raise `ValueError` in `__init__`, case-sensitive, before any call.

## 3. Tests the contract should pin

- None sends today's exact body with no `reasoning_effort` key (`anamnesis/providers/openweight.py:84`).
- `low` adds only `"reasoning_effort": "low"` (`anamnesis/providers/meta.py:296`).
- Invalid values raise `ValueError` at construction (`anamnesis/providers/openweight.py:60`).
- Live builds Fireworks with `low` and Baseten with None (`scripts/intake_live.py:131`).
- Batch 22 comparison body for None is unchanged (`tests/contract/test_b22_openweight.py:78`).
- `length` under `low` stays non-retryable, one charge (`anamnesis/providers/openweight.py:123`).
- Malformed under `low` retries once, both charged (`tests/contract/test_b22_openweight.py:110`).
- Live still builds `json_mode=False` and the preset stays True (`tests/contract/test_b26_open_weight_path.py:199`).

## 4. Open questions for the CEO

- Timeout: client default is 60 s (`anamnesis/providers/openweight.py:44`); is 60 s still right given a 52 s retry success?
- Placement: should effort live in `PRESETS` instead of the call site (`anamnesis/providers/openweight.py:14`)?
- Eval: should `reader_eval.py` gain an effort flag or stay None forever (`scripts/reader_eval.py:76`)?
- Logging: should `runs.jsonl` record the effort alongside the reader (`scripts/intake_live.py:145`)?
- Streaming: the doc recommends setting effort and streaming (`docs/muse/muse-spark-open.md:34`); is non-streaming `low` the final shape?

