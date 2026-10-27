# Batch 13 (B12b) review: clearing the QM M2 blockers

Built-by: Claude Sonnet subagent (Claude Code), at Ahmed's request. The first attempt on plain `codex` (ChatGPT login, `gpt-6-chat-thinking`) was stopped before it changed any file; its log shows no profile reads.

Reviewer: Claude Code (Opus 5.5). Gate (run by the reviewer, not the builder): pass, 370 tests. The contract started with 9 failing tests, and the contract lock held.

Verdict: PASS

## Checked against the brief and the QM2 table
- **QM2 #1 (blocker):** an `intake_amount` against a pack with more than one ingredient → `insufficient_information`, before the single-ingredient intake check. Combination claims with only a strength still compare. ✅
- **QM2 #2 (blocker):** `_side_salts` is one collection path (strength, intake, scalar `inn`, **free text**). Text salts use the catalogue's own `normalise` and whole-word curated aliases; nested aliases are deduplicated. A side holding 2 salts for one ingredient is an extraction conflict in rule 3, even when the other side names no salt. ✅
- **QM2 #3:** a scalar `inn` whose moiety isn't in the strength's ingredient set is a conflict. A salt form of the same moiety isn't. ✅
- **QM2 #5:** a country match sorts first, case-insensitively, then brand, so the result is deterministic. ✅
- **QM2 #8:** Arabic clitic and joined-form pins pass. ✅
- The builder's three interpretation choices are reasonable and recorded: the salt conflict sits in rule 3; the combination intake overrides only `match`; pairing scores are unchanged.

## Known limitation (logged, not blocking)
- Labels that print **both** salts ("metoprolol succinate … equivalent to 100 mg metoprolol tartrate", common on US labels) now count as a one-side salt conflict → `insufficient_information`. That is safe, because the pack goes to review rather than a false match, but it is noisy. Fix later with a curated "equivalent to" pattern, not by loosening the conflict rule.
