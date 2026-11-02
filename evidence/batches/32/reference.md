# Batch 32: the CEO's check of the contract (1 Nov, before round 1)

Before Muse built anything, the CEO wrote a throwaway reference of SPEC §3 "Spanish speech (batch 32)" in a detached worktree at `3878912`, the contract commit: in `Catalogue._matches`, Latin-script names get `[bv]` for each `b` or `v`, and an optional attached form of *tomar* before them, inside the whole-word boundaries. The worktree was deleted afterwards, and none of its code is on the branch.

- **The contract on the reference:** `tests/contract/test_b32_spanish_names.py`, 45 of 45 pass. The full suite has 2,854 passing (2,809 earlier and 45 new). So the contract can be met, and no earlier contract breaks.
- **On today's code** (before the reference): 25 of the 45 fail, all of them the new behaviour; the 20 that pass pin what must not change.
- **Deliberate single-rule breaks of the reference, each run alone on a clean copy:** 6 of 7 caught.

| Break | Failed |
|---|---|
| `b` and `v` not folded | 17 |
| No attached form of *tomar* | 18 |
| Any attached letters before a name | 13 |
| Two attached forms | 1 |
| No leading word boundary | 5 |
| One form missing (`toman`) | 1 |
| *Tomar* forms also allowed before Arabic names | 0 |

The last break can't change a result: `normalise` already splits Latin from Arabic script with a space, so a Latin form can never be joined to an Arabic name. It needs no test.

## Round 2 (after the supervisor's review)
The supervisor found one Major: a salt name spelled with `b`/`v` or a joined *tomar* form lost its salt, so a pair that used to abstain could `match` ("tomometoprolol succinate" against a tartrate pack: `insufficient_information` → `match`). The SPEC now matches a name that carries a salt only as written, pins that only `b` and `v` fold and only the five forms attach (#3), and states the older label limit (#2). The contract gained 13 cases (58 in all). The CEO's reference was Muse's round-1 code plus the salt rule, in a detached worktree that was deleted afterwards.
- **The contract on the reference:** 58 of 58 pass. The full suite has 2,873 passing; the 3 that fail are Muse's own round-1 unit tests that assert the fold on salt names, which round 2 must change.
- **Muse's round-1 code against the round-2 contract:** 5 fail, the salt cases, as they should. The code from before batch 32 fails the 25 new-behaviour cases and passes the salt cases.
- **Deliberate breaks of the round-2 rules, each run alone:** 3 of 3 caught.

| Break | Failed |
|---|---|
| Salt names folded too | 5 |
| `p` and `w` fold with `b` and `v` | 4 |
| "tome", "tomó" and "tomaba" attach | 3 |
