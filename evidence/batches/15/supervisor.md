# Batch 15: Opus 5.5 supervisor reviews (high effort, read-only, independent of the orchestrator)

Prompt: `evidence/grills/BATCH_SUPERVISOR_PROMPT.md`. Three rounds.

## Round 1: CHANGES
- **Blocker:** charges were lost when a cap refused attempt 2 after a charged attempt 1. Ran: SAM timeout then `SessionGuard(max_usd=0.003)` gave ledger 0.0025 vs report 0; a paid invalid Spark reply then `max_calls=1` gave ledger 0.0021 vs session 0.
- **Minor:** the #4 contract test passes even with the old ratio logic, because no curated entry has nominal = k × literal. A direct `_strength_type` probe does distinguish them.
- **Minor:** simplify `_strength_basis`.

## Round 2: CHANGES
- Round-1 inputs re-run: the ledger and the report now agree.
- **Major:** a paid Spark reply with an empty `id` failed validation outside the try. The paid call missed the ledger, and the `ValueError` branch ignored the attached charges. Ran: ledger 0.03 vs session 0.

## Round 3: APPROVE
- Empty-id inputs re-run for both Spark callers: ledger 0.06, session 0.06, both estimated ids on the step.
- Final scan: no path to a false match, lost provenance, unrecorded spend or advice leakage. `with_one_retry` retries only a retryable `ProviderError` on attempt 0 and re-raises the original exception.
- Minor, not blocking: (1) an unexpected `TypeError`/`KeyError` from a provider would crash `run_intake` instead of under-reporting; (2) numeric ids are now treated as malformed, so they're charged at the $0.03 estimate, which over-counts rather than under-counts.
