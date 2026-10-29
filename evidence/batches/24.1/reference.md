# Batch 24.1: the CEO's reference build, 29 Oct

- **Contract:** `test_b24_1_codes.py`, 18 tests.
  - First proof: on the code after batch 24's reference build.
  - Proved again at 23:45 CET on main at 9099fd1, after batch 24 merged: 14 fail and 4 pass. The 4 that pass are the SNOMED and NOTICE guards and the unknown-name case.
- **Reference build:** a scratch clone of main outside the repo, with both parts done by the CEO. **2,408 passed**, ruff clean.
- **A fix to the contract file itself:** its import block failed ruff's ordering in the repo layout (a missing blank line before the first-party imports). That would have failed the gate. It was fixed before this commit.

## Found while building it
- **The fine-tune reads every catalogue entry** (`finetune/drugs.py`). With three new entries, r1's data no longer regenerates byte for byte, and the noise-rate test fails.
  - **The fix, in this contract commit:** the vocabulary is pinned to the nine entries it was built on (`FINETUNE_BRANDS`). On today's catalogue that is a no-op.
- **A test fixture:** the fake reader needs a second reading when an unreadable pack is zoomed. The brief tests give it one.
- **Nolotil's RxCUI is 3523,** RxNorm's ingredient "dipyrone", the US name for metamizole. The engine's shell sandbox can't reach RxNav, so it was read in the browser on 29 Oct:
  - `rxcui.json?name=metamizole&search=2` gives 3523;
  - `rxcui/3523/properties.json` gives TTY IN, not suppressed.

## One mutant per behaviour
Each mutant was applied alone to the reference build on main at 9099fd1. The count is the failures in `tests/contract` plus the two fine-tune data tests.

| Mutant | Failures |
|---|---|
| The loader drops `rxcui` | 10 |
| Nolotil splittable | 1 |
| Sortis without codes | 1 |
| The reference line on every page | 1 |
| No codes line in the box | 3 |
| RxCUIs joined without a comma | 1 |
| A SNOMED id in the catalogue | 1 |
| The fine-tune vocabulary unpinned | 3 |
