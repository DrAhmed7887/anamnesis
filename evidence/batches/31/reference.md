# Batch 31: the CEO's check of the contract (1 Nov, before round 1)

Before Muse built anything, the CEO wrote a throwaway reference of SPEC §8 "The follow-up by itself" in a detached worktree at `ec9087f`, the contract commit. It was deleted afterwards, and none of its code is on the branch.

- **The contract on the reference:** `tests/contract/test_b31_follow_up.py`, 22 of 22 pass. The full suite has 2,779 passing (2,757 earlier and 22 new), and ruff is clean. So the contract can be met, and the new `render_brief` argument and header line break no earlier contract.
- **Deliberate single-rule breaks of the reference, each run alone on a clean copy:** 8 of 8 caught.

| Break | Failed |
|---|---|
| Targets that appear during a round are asked in that round | 2 |
| A repeated photo raises instead of being logged `duplicate` | 1 |
| A target with an open request is asked again | 9 |
| The run approves the review when nothing is open | 4 |
| `render_brief` accepts a log without its review | 1 |
| A target is asked without re-checking that it is still requestable | 4 |
| The caller's image list is appended to | 1 |
| The follow-up's own media check is removed | 1 |

Two first attempts at the last two breaks hit the wrong code: one appended to the run's own copy of the list, and one removed `add_photo`'s check rather than the follow-up's. Rerun on the right code, both were caught.
