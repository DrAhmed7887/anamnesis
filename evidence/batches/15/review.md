# Batch 15 review: clearing the QM M3 HOLD

Built-by: Claude Sonnet subagent (high effort), 3 revision rounds driven by the Opus 5.5 supervisor (see supervisor.md)

Orchestrator: Claude Code (Opus 5.5). Gate: pass, 421 tests (contract 7 failing first, then green; 7 builder unit tests added for the gaps the supervisor found). Contract lock held.

Verdict: PASS (supervisor APPROVE, round 3)

## What changed
- **QM M3 #1 (blocker):** every charged attempt (real or estimated) now travels on the escaping exception (`charged_call_ids`, `charged_usd`): `ProviderError`, `SpendCapExceeded`/`SessionCapExceeded`, and `ValueError` after charged attempts. `IntakeSession` adds them to the report's spend and the step's call ids. **The ledger and the report agree on every path the supervisor could construct.**
- Spark callers validate a non-empty string `id` inside the try, so a malformed 200 is billable-uncertain and charged at the estimate.
- **#2:** conflicted candidates score at most 1 in pairing.
- **#3:** `mentions_moiety` reuses `_matches` (joined brands and Arabic clitics).
- **#4:** a stated tablet strength equals the literal or the nominal amount; ratios apply to intakes only.
- **#7:** the batch 14 reviewer behaviours are now in the contract.

## Process note
The supervisor showed that one of the orchestrator's own contract tests (#4) proved nothing on current data. A direct unit probe now covers it. Lesson: when a fix changes a rule that current data never exercises, test the rule directly.
