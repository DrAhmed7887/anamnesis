# Batch 8 review: claim extraction from transcript turns

Reviewer: Claude Code (Opus 5.5). Builder: codex `gpt-6-luna`, used because Sol was rate-limited. One 429 occurred during the run and was retried. Gate: pass, 242 tests.

Verdict: PASS

## Checked
- `CLAIMS_SCHEMA` is flat (no `$ref`). Its enums come from the schema enums. ✅
- `parse_claims_json` checks the raw shape (extra fields rejected at every level). Every `turn_id` must exist, with at least one per claim. Claim ids are `c1…cn`. All failures are retryable. ✅
- The system prompt matches the brief:
  - one claim per medicine, names as spoken, no INN inferred from a brand
  - an amount spoken with a frequency is an intake
  - "stopped" means discontinued, and anything unsaid stays null
  - cite the turns, and give no advice ✅
- The extractor refuses contributor models, makes no call without turns, checks the cap before each attempt, pays for both attempts on a retry, and keeps the key redacted. ✅
- Offline end to end: the extracted claims against the **live** pack readings give Concor `match`, metoprolol `intake_differs`, and Panadol (stopped, no pack) `missing_modality`. ✅

## Risk for the live run
- `intake_amount.inn` must be non-empty, but the prompt says not to infer an INN from a brand. For "Concor five milligrams", Spark may write `inn: "Concor"`. The reconciler compares canonical INNs, so "concor" vs "bisoprolol" would give a false `strength_mismatch`. The live smoke test decides whether this needs a fix.
