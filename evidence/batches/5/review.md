# Batch 5 review: live Meta adapters behind SpendGuard

Reviewer: Claude Code (Opus 5.5). Builder: codex `gpt-6-sol`. Gate: pass, 195 tests. All of them run offline through `httpx.MockTransport`.

Verdict: PASS

## Checked
- The key is sent only in the `Authorization` header. It's redacted from every `ProviderError` message, and `repr(MetaClient)` doesn't show it. ✅
- HTTP mapping: 4xx errors are non-retryable; 429, 5xx, timeouts and transport errors are retryable. ✅
- **Voice:** WAV, mono, 16-bit and 16/24 kHz are checked *before* upload, along with the 10-minute and 32 MB limits. The request is multipart `request` JSON (ENDPOINTING, `languageBias`, `keywords`) plus the `audio` part. The cap is checked on the clip's duration; the charge uses the billed `audioDurationMs`. ✅
- **SAM:** a single-noun-phrase check runs before any call. The request goes to `/responses` with string-valued `metadata`, the text is joined from the `output_text` parts, and `call_id` is the response id. ✅
- **Spark:** contributor model ids are refused. The JSON schema is flat (no `$ref`), and the region box is included in the prompt. A call is **charged before parsing**, so an invalid reply is paid for, then retried exactly once. ✅
- The spend cap stops a call *before* any request is sent. ✅

## Notes (not blocking)
- Voice and SAM don't retry on 429 or 5xx themselves; only Spark retries, on invalid JSON. Batch 6's agent loop owns the retry policy.
- Combining `strict` JSON schema output with image input isn't documented by Meta (`docs/muse/muse-spark.md`). The live smoke test checks it.
- A non-default Spark model id without a price entry surfaces as "malformed Spark response". The message is misleading, but nothing breaks.
