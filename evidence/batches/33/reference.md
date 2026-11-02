# Batch 33: the CEO's check of the contract (2 Nov, before round 1)

Before Muse built anything, the CEO wrote a throwaway reference of SPEC §3, rule 6's "A salt said inside a longer label (batch 33)", in a detached worktree of `main` at `9e95d9a`: in `_side_salts`, each strength ingredient's and intake's `inn` also goes through `_text_salts`. The worktree was deleted afterwards, and none of its code is on the branch.

- **The contract on the reference:** `tests/contract/test_b33_label_salts.py`, 38 of 38 pass, and the earlier suite passes 2,877 of 2,877. So the contract can be met, and no earlier contract breaks.
- **On today's code** (before the reference): 25 of the 38 fail, all of them the new behaviour; the 13 that pass pin what must not change.
- **The saved live reports:** all 205 `evidence/live/*/report_*.json` re-reconciled from their saved claims and packs give the same findings on the reference as on `main`. No real run said a salt inside a longer label.
- **Deliberate single-rule breaks of the reference, each run alone on a clean copy:** 6 of 6 caught.

| Break | Failed |
|---|---|
| Curated aliases only, no loose salt words (`_loose_salts`) | 10 |
| Intake labels only | 12 |
| Strength labels only | 14 |
| No label read unless the claim has an intake (so no pack or stated label) | 12 |
| The whole label normalised and looked up as one alias | 22 |
| The pack's salt-basis lookup (rule 7) also reads labels, so a pair could newly agree | 1 |

## Construction note
The contract builds each ingredient as the product does: a model reply carries no `salt` key, so `IngredientAmount`'s validator splits an exact alias (`"metoprolol succinate"` → `inn="metoprolol"`, `salt="succinate"`). Passing `salt=None` explicitly skips that split, so the salt of an exact alias is lost. No product path does that: the claim parser's shape check allows only `inn`, `amount` and `unit` (`anamnesis/providers/claims.py`:125–148), and a label reply's strength refuses a `salt` key (SPEC §2). The CEO's first quick check built claims that way and briefly read the exact label "metoprolol succinate" as a `match`. Recorded here so no later check repeats it.

## Round 2 of the contract (after the supervisor's review)
The supervisor approved round 1 and found one gap in the contract (#3): no case had a claim with both a strength and an intake, and a build that read only the first part's label passed all 46 tests while letting such a claim `match` a tartrate pack. The CEO added two cases at `33e6bd9`, and the SPEC names the supervisor's #1 and #2 as known limits of rule 6. Muse's code wasn't changed.
- **Muse's round-1 build against the round-2 contract:** 40 of 40 pass; the gate passes 2,925 tests.
- **Deliberate breaks of Muse's build, each run alone and then restored:** 2 of 2 caught.

| Break | Failed |
|---|---|
| Only the first part's label read (`parts[:1]`) | 1 |
| No moiety-or-brand check for a loose salt word | 1 |
