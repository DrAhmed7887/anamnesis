# The fresh Muse audit of batch 26: what it changed

**What ran:** a second Muse Code session (muse-spark-1.3, standard mode) audited round 1's build, read-only, on 30 Oct at 20:26 CET (`scripts/grill.sh b26-muse-audit`). Round 1's diff was given inline, and its own copy of the repository sat at the contract commit. It read nothing under `evidence/` or the fine-tune data (`goal_check.py`). It cost $0.36.

**Verdict:** "Sound build: served engine/decoding match the eval, charging and guards fail closed; six findings, all low/medium, none blocking." The independent Opus supervisor approved the same build (`evidence/batches/26/supervisor.md`).

| # | Muse's finding | Outcome |
|---|---|---|
| 1 | Medium: the server accepts any schema and `max_tokens`, so a token holder could decode differently from the eval | Not changed. The server takes the schema as `evaluate` does, as an argument. Only proxy-token holders can call it, and the product's request is pinned by the contract |
| 2 | Low: a body that isn't JSON gets a 500, which the client charges twice as estimates; an over-long prompt fails inside vLLM | Round 2, item 2: a 400 for both, before generating |
| 3 | Low: stop reasons other than `"length"` fail open | Round 2, item 1: only `"stop"` counts. The product's checks would still have run on any such reply |
| 4 | Low: the served prompt is duplicated by hand from the training prompt | Not changed. The contract pins the two equal, so a drift fails the gate |
| 5 | Low: `completion_tokens` includes the reasoning pass | Not changed. That is the intended count, as Spark's usage counts reasoning tokens |
| 6 | Info: one GPU stays warm up to 10 minutes, and could overlap a training-app eval | Not changed. No eval is planned, and Modal's billing is reconciled after each session |

**Its open questions:**
- **The SPEC section:** it exists at the contract commit; the audit's search missed it.
- **A timeout:** the client's 120 s timeout raises a retryable error, charged as an estimate (`MetaClient.post`).
- **What the byte-identical check covered:** clean replies only. The length-stop and no-answer paths are covered by the contract's fakes, not live.
