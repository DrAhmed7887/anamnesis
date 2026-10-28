# Batch 21: supervisor review

**Prompt.** `evidence/grills/BATCH_SUPERVISOR_PROMPT.md`. The builder was Muse Code (`muse-spark-1.3`). The supervisor is a different model family (Claude Opus, high effort) and was not told the CEO's opinion. It probed offline, in scratch copies of the code from before and after the batch.

## Round 1: CHANGES (2 major, 5 minor)

The CEO reproduced every finding on the after copy.

1. **major** `anamnesis/providers/stated.py`, `_word_amounts`. When no "and" comes before the second hundred word, the new hundred's multiplier stays in the earlier number.
   - Ran: "eight hundred seventy-five one hundred twenty-five milligrams" states **876** and 125, and never 875.
   - End to end, the correct 875/125 strength is dropped and an 876/125 strength is kept. The guard now admits a near-miss dose nobody said.
   - Before the batch, the run stated 87625, which matches no claim.
2. **major** The same code, against SPEC §2 line 41: the rule "after a `و` attached to one of them" is not implemented.
   - Ran: «خمسمية وتلات مية» states **503** and 100.
   - The literal SPEC rule would be wrong too, because Arabic tens always carry `و`.
   - The fix covers both #1 and #2: move only a final plain worth 1–9, and nothing when the hundred word carries `و`. The supervisor tested it on a scratch copy.
3. **minor** One-word Arabic hundreds (ميتين, تلتمية … تسعمية) never start a new number: «خمسمية وميتين» states **700**. This is not a regression.
4. **minor** Nothing pins the label prompt's "Give no advice." The deletion mutant passes all 985 tests.
5. **minor** `_word_amounts` is about 60 lines, resets `last_and` in five branches, and `_since_thousand` repeats `_run_value`.
6. **minor** `_DIGIT_RUN` can sit next to a digit of another set: "１5 mg" states 5. This is not a regression.
7. **minor** The accented alias keys match only NFC input. An NFD "ácido clavulánico" goes unpaired, which fails safe.

**Ran clean:**
- The gate.
- 38 number-word inputs: every contract case behaves as pinned, and single numbers stay single.
- The digit sets.
- Pairing in both pack orders: no input turns a shown disagreement into `match`, and a second Norvasc case that was mis-paired before the batch now gives two correct matches.
- The 52 alias keys: no collisions, and the salt-word set is unchanged.
- Both prompts: each is the old prompt with exactly one sentence swapped.
- The escaped `<bdi>` markup.
- The turn-playback selectors.
- Scope.

**CEO triage:** all 7 accepted for round 2. The fixes are small, they sit in the same functions, and #1–3 and #6 belong to the class this guard exists to stop, a stated value the patient never said.
- **Contract:** round 2 cases added to `tests/contract/test_b21_media_fixes.py` for #1–4, #6 and #7.
- **SPEC:** §2's rule on a new number is reworded to the supervisor's rule. The SPEC wording was the CEO's error.
- **Reference build:** 1,002 passed (scratch `supervisor-21/ref-r2`).
- **No contract case:** #5 is a refactor. The suite must stay green.

## Round 2: CHANGES (1 blocker, 1 major, 2 minor, 2 follow-ups)

The CEO reproduced #1 before the review, prompted by Muse's own note in round 2.

1. **blocker** `stated.py` `_run_value` and `_since_thousand` treat «ألفين» (a plain worth 2000) as an ordinary plain. The round 2 rule, that a plain of 100 or more splits, then breaks every Arabic number from 2100 to 2999.
   - Brute force over Arabic 1–2999 on round 2: **900 numbers not stated**. «ألفين وخمسمية وخمسين» states a **550** nobody said.
   - The CEO's round 2 brief caused it.
   - On base, the «ألفين ومية» family (100 numbers) became 200000.
   - Fix: a plain worth 1000 or more closes the thousands part, in both functions. Result: 0 of 2999 missed.
2. **major** "and a hundred" now moves the earlier number's final units word: "eight hundred seventy-five and a hundred twenty-five" states **870 and 525**. Round 1 gave 875 and 125. Fix: after the filler `a`, nothing moves.
3. **minor** Round 1 fix #6 was wrong; the supervisor corrected its own advice. With `(?!\d)`, the decimal part can backtrack, so "1.5５ mg" states 1. Fix: an atomic group.
4. **minor** No test covered «ألفين» or "and a hundred". That is why #1 and #2 passed all 1,004 tests.
5. **follow-up** NFC is applied only in `_inn_and_salt`. `catalogue.normalise` still splits decomposed accents. It fails safe.
6. **follow-up** A thousand word after a group of 100 or more multiplies it: "two hundred and one thousand" gives 201000. This happens on base and on every round.

**Ran clean:** the round 2 contract; English 1–2999 with and without "and" (0 missed); lists of two numbers apart from #1, #2 and #6; items 4–6; scope.

**CEO triage:**
- #1–4 go into round 3. The contract gets "round 3" cases (10 fail on round 2; all 1,016 tests pass on the supervisor's fix copy) and SPEC §2 lines.
- #5 and #6 are logged as follow-ups for after the freeze. Neither is a regression, and both fail safe or are out of scope.
