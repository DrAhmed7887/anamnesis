# Batch 34: the CEO's check of the contract (2 Nov, before round 1)

**The source:** the Spanish names come from Spain's medicines registry, AEMPS CIMA. The CEO queried its list of active substances (`maestras?maestra=1&nombre=…`) for each catalogue moiety on 2 Nov, and saved the replies in `evidence/data/cima_salts.json`.

**The reference:** before Muse built anything, the CEO wrote a throwaway reference of SPEC §3, rule 6's "Spanish salt names (batch 34)", in a detached worktree of `main` at `fe30402`. In `reconcile.py` a table of the SPEC's Spanish words maps each to its English salt, and `_loose_salts` accepts a curated salt when its English name or one of its Spanish words stands as whole words. The worktree was deleted afterwards, and none of its code is on the branch.

- **The contract on the reference:** `tests/contract/test_b34_spanish_salts.py`, 53 of 53 pass, and the earlier suite passes 2,925 of 2,925. So the contract can be met, and no earlier contract breaks.
- **On today's code** (before the reference): 31 of the 53 fail, all of them the new behaviour; the 22 that pass pin what must not change.
- **The saved live reports:** all 205 `evidence/live/*/report_*.json`, re-reconciled from their saved claims and packs, give the same findings on the reference as on `main`. That includes the Spanish hero's runs, whose boxes now carry a salt (fumarate on Emconcor, tartrate on Lopresor) but whose claims name none.
- **Deliberate single-rule breaks of the reference, each run alone on a clean copy:** 8 of 8 caught.

| Break | Failed |
|---|---|
| No accent-less forms ("calcica", "calcica trihidrato") | 2 |
| "hemifumarato" read as fumarate | 1 |
| "calcio", the noun, added | 1 |
| No moiety-or-brand check for a Spanish word | 1 |
| Each Spanish word kept as its own salt ("succinato"), not the English one | 16 |
| Spanish words read only right after the moiety's name | 6 |
| No suppression of "cálcica" inside "cálcica trihidrato" | 5 |
| The Spanish names also added to `INN_ALIASES` (they become catalogue names) | 3 |

With Spanish words not read at all, `main`'s behaviour, 31 fail.

**One test added during the check:** the accent and hemifumarate cases first asserted only `match`, which a build that ignored the words would pass. `test_each_spanish_name_reads_as_its_english_name` asserts that each Spanish name gives exactly what its English name gives, whatever that is, so it doesn't pin the known limit that calcium and calcium trihydrate count as two salts.

## Round 2 of the contract (after the supervisor's review)
The supervisor approved round 1 (`supervisor.md`). Its #1: a text naming calcium in one language and calcium trihydrate in the other now reads one salt, so "Lipitor calcium (cálcica trihidrato)" against a calcium trihydrate pack moved from `formulation_mismatch` to `match`, against the brief's "nothing newly agrees". The CEO checked it: the all-English "Lipitor calcium (calcium trihydrate)" was already `match` on `main`, so the build does what the SPEC says, a Spanish name gives what its English name gives. The SPEC now names it as the one move toward `match`, and the contract gained 5 cases at `a83e843` that pin a mixed text to its all-English wording.
- **Muse's round-1 build against the round-2 contract:** 58 of 58 pass.
- **The supervisor's alternative fix, as a break** (a salt shortened only by a longer one read in the same language): 2 of the 58 fail, so the contract pins the SPEC's choice.
