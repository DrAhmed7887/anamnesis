# Batch 4 review: provider adapters (offline)

Reviewer: Claude Code (Opus 5.5). Builder: codex `gpt-6-sol`, 45,546 tokens. Gate: pass, 165 tests (164 from the builder plus 1 regression test from the reviewer).

Verdict: PASS

## Checked against the brief and SPEC.md §1, §4, §5
- `ProviderTrace` is strict and **rejects `*-contributor` model ids**, so no call can quietly run in train-on-my-data mode. ✅
- `cost_usd` uses the documented price table (Spark $1.25/$4.25 per 1M tokens, SAM $2.50 per 1,000 images, Voice $0.18 per hour in whole seconds). Unknown models raise. ✅
- `SpendGuard` is an append-only JSONL ledger. The total reloads from disk, and it refuses *before* crossing the cap; a refused charge isn't written. ✅
- Voice keeps the raw transcript exactly as received and uses turn-level timing only. A malformed payload raises a non-retryable error. ✅
- Spark label JSON is checked against the closed schema. Invalid output is **retryable**, so the agent loop retries once. Every reading is grounded in one `region_id`. ✅
- The fixture adapters use the same interface with `fixture:` model ids, $0 cost and deterministic call ids. Missing fixtures are non-retryable. ✅

## Reviewer fix (on this branch)
- **Defect:** the SAM parser ended a mask payload at the first `|`. Masks are base85, and Python's base85 alphabet includes `|` and `>` (checked locally). A valid SAM response could have been rejected as malformed.
- **Fix:** the payload now ends only where the next record starts (`,<id><|box;`) or where the text ends.
- Regression test: `test_sam_mask_payload_may_contain_pipes_and_angle_brackets`. It failed before the fix (gate red) and passes after it.

## Notes for the live adapters (day 2)
- Check the mask encoding against a real SAM response, or switch to Meta's `meta-sam-parser` package (published by Meta Platforms), before decoding masks. Today we only parse boxes.
- `SpendGuard` is single-process: one writer at a time, which is fine for the solo runner.
