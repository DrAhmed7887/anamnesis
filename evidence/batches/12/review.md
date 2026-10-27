# Batch 12 (B12a) review: ledger integrity and retries

Built-by: codex gpt-6-luna (about 30 rate-limit retries; finished)

Reviewer: Claude Code (Opus 5.5). Gate: pass, 343 tests. The contract started with 9 failing tests. This batch answers the QM M2 **blocker #8** and finding #4.

Verdict: PASS

## Checked
- **One retry helper** (`with_one_retry` with guard, model and estimate) is shared by Voice, SAM, Spark labels and claims. It runs at most 2 attempts, with `guard.check` before each. ✅
- **Billing-uncertain failures** (timeout, transport error, 5xx, malformed 200) charge the pre-call estimate through `SpendGuard.charge_estimate`. The ledger line is marked `estimated: true` with a `reason`, gets an `estimated-<uuid>` call id, and counts toward the cap. ✅
- **Rejected requests** (4xx, 429) are never charged. A 429 is retried once. ✅
- **Traces:** the final trace carries `prior_call_ids` and `prior_cost_usd`. A failed Spark parse keeps its real trace as the prior attempt. ✅
- **`charge_prechecked`**, added by the builder, records a call that was actually billed **without** a second cap check. That's better than the brief: the cap is enforced before the call, and a real bill must never be dropped from the ledger, which the old `charge` would have done if the real cost ran slightly past the cap. ✅

## Note
- SPEC §4 now states the retries as built. The agent loop itself (B12b/B12) is still unbuilt, and the section header says so.
