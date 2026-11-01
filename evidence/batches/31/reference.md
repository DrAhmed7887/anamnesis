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

## Round 2 (after the supervisor's review)
The SPEC narrowed the follow-up to medicines mentioned but not photographed (supervisor #2), and it took #1, #3, #4, #7 and a stricter `max_rounds`. The contract was rewritten to 43 cases. The CEO's reference was Muse's round-1 code plus those rules, in a detached worktree that was deleted afterwards.
- **The contract on the reference:** 43 of 43 pass. The full suite has 2,800 passing.
- **Muse's round-1 code against the round-2 contract:** it fails at collection (no `PhotoAlreadyGiven`), as it should.
- **Deliberate breaks of the new rules, each run alone:** 6 of 6 caught.

| Break | Failed |
|---|---|
| `reply` gets the review's own request object | 1 |
| A withdrawn request's target is asked again | 1 |
| Unreadable packs are asked for too | 14 |
| A `bool` passes as `max_rounds` | 2 |
| The brief doesn't check an outcome against its request's status | 2 |
| The brief allows a step twice | 1 |

## Round 3 (after the supervisor's round-2 APPROVE with five points)
The contract was raised to 46 cases. The changes:
- the new header text;
- a late answer must keep the log valid;
- a step of a kind the follow-up never makes is refused;
- the same-round skip (the supervisor's round-2 #2);
- the invariant that after the follow-up the findings are those of an intake given every photo at once (round-2 #1).

**Results:**
- **Muse's round-2 build on it:** 40 of 46 pass, and the 6 failures all need round 3's code (the text, the late answer, the kind).
- **The CEO's reference** (Muse's round-2 build plus those three changes, in a detached worktree, deleted afterwards): 46 of 46 pass, and the full suite has 2,808 passing.
- **The same-round skip deleted from the reference:** caught (1 failed).
