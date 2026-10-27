muse muse-spark-1.3, batch 18, started 2026-10-27T16:19:28Z
muse: workspace root: <repo> (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Batch 18 done. `.venv/bin/ruff check .` passes, `.venv/bin/python -m pytest -q` passes (575 passed), `git status --porcelain tests/contract` prints nothing.

Files changed:
- [crop.py](anamnesis/agent/crop.py) — new `enlarge_crop`
- [loop.py](anamnesis/agent/loop.py) — `_read_photo`, `_zoom`
- [meta.py](anamnesis/providers/meta.py) — `spark_call_estimate`, `MetaLabelReader.read`
- [claims.py](anamnesis/providers/claims.py) — `MetaClaimExtractor.extract`
- [test_m3_blockers_extra.py](tests/unit/test_m3_blockers_extra.py) — updated stale $0.03 test
- [test_crops_extra.py](tests/unit/test_crops_extra.py) — new, 5 tests

Per numbered change:
1. Crop-first reads: `_read_photo` skips cut/log once exhausted, cuts `crop_region(image[0], region)` outside `session.call`, logs `READ / "error: crop failed"` with no call on `ValueError`, reads crop as PNG with `cropped=True`.
2. 2x zoom: `_zoom` keeps signature and check order, re-cuts via the `crop_region` name in loop.py, enlarges through `enlarge_crop` (factor `min(2, 2048/longest)`), returns unchanged with no step/call when factor ≤ 1.
3. `spark_call_estimate(body)` added and exported in `__all__`; matches the contract's exact figure ($0.02325375 on the fixture body).
4. Both adapters compute the estimate once, pass it to `guard.check` and `with_one_retry`; `SPARK_CALL_ESTIMATE_USD` removed (nothing else used it).
5. Claims `max_tokens` now 16000; label reads stay 4000.
6. Length stops in both adapters raise non-retryable `ProviderError("spark", "Spark reply stopped at the length limit", ...)` with `attempt_trace`, after charging real usage; the message carries no model text.
7. Updated `test_a_paid_spark_reply_with_an_empty_id_is_counted` to compute `2 * spark_call_estimate(seen[0])` from the captured request body (label and claims bounds differ, so no single constant works). New unit tests cover the estimate helper, the enlarger, length-stop text exclusion, and claims `max_tokens`.

One thing in the brief worth flagging: step 2 says "the region-id check on the new reading" comes after the crop note, which I kept — but note the region-id check only runs when the zoom call succeeds, so a drifting zoom that also fails to crop reports "crop failed" rather than "another region". That matches the existing contract test, so no conflict.

One environment note: this repo's Pillow is 13.0.0, where the `Image.Lanczos` alias is gone, so the enlarger uses `Image.Resampling.LANCZOS`.
