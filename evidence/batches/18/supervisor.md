# Batch 18 supervisor (Claude Opus 5.5, high effort, read-only)

Prompt: `evidence/grills/BATCH_SUPERVISOR_PROMPT.md`. The builder was Muse Code (`muse-spark-1.3`); the supervisor is a different model family and was not told the CEO's opinion. It probed offline, in scratch copies of the code before and after the batch.

## Round 1: SUPERVISOR: APPROVE
No code change was required before merge.

1. **minor** `anamnesis/providers/meta.py` `spark_call_estimate`, as SPEC §5 defines it. It isn't a strict upper bound for a text-only call. The `response_format` schema (1,611 characters for the claims schema) and the chat-template overhead are billed as prompt tokens but not counted. The live claim calls of 27 Oct had a bound of 383 and 391 input tokens against 559 and 550 billed. On a normal reply the 16,000-token output allowance hides the gap. On a length stop it doesn't: the supervisor ran a stop at 559 + 16,000 tokens against a cap set to the bound, and the ledger ended $0.0002 over the cap. The charge was still recorded. Fix: also count the characters of `json.dumps(response_format)` (SPEC first).
2. **minor** Two brief items have no test. Setting the label read's `max_tokens` to 16,000, or the zoom's Lanczos to nearest-neighbour, still passes the whole suite (both ran). Fix: assert the label body's `max_tokens == 4000`, and compare `enlarge_crop` against a Lanczos resize on a crop with detail.
3. **minor** `scripts/zoom_live.py` tells a first read from a zoom by `cropped`, and since this batch every read is cropped. Its evidence table puts the first read in the zoom column, and `--compare` skips every region (ran it with fakes). It touches evidence tooling only, never a patient. The full-photo branch of `MetaLabelReader.read` is now reached only by `scripts/smoke_live.py`.

The builder's flagged point (the region-id check runs only on a zoom reading that exists) is not a problem. When the re-cut fails no call is made, so provenance can't drift. Mutations the contract catches: no exhausted check in `_read_photo`, no claims length stop, and the crop cut inside the call lambda. The edited b14 and b15.5 contracts fail on the pre-batch tree (5 failures), so they test the change.

**CEO triage:** all three accepted, none blocking.
- #1 and #2 go into the next batch's SPEC and contract commit, since #1 changes SPEC §5's formula.
- #3 is CEO tooling (Muse may not edit `scripts/`), fixed on main right after this merge.
- The full-photo branch stays: the b14 contract pins both prompts.
