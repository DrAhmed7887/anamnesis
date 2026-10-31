# Batch 27.1, round 2: narrow the two new exceptions, and back a tablet count only with this claim's counts

Round 1 passed the gate. A fresh Muse audit and the Opus supervisor each found a gap, and the supervisor found one that re-opens a false `match`. In every case the code followed the SPEC's wording, and the wording was too broad. The SPEC now settles all three (§2, the places marked "batch 27.1"), and new contract tests pin them at the end of `tests/contract/test_b271_relations.py`. The contract commit is the latest `test(contract): batch 27.1`.

## Do, in `anamnesis/providers/relations.py` (and the hook in `claims.py` for 3)
1. **Only German "weiß" cancels a negation right after it** ("ich weiß nicht fünf"). After any other word of knowing, the negation still negates: "sicher nicht fünf" means "certainly not five", and «متأكد مش خمسة» means "I'm sure it's not five". Both must drop the 5. Remove your unit test's assertion that "sicher nicht fünf" keeps 5.
2. **Duration words are plurals only** (the SPEC's new list). A singular after a number is a dose's context: «خمسمية ساعة ما راسي توجعني», «خمسة يوم ويوم لا» and "10/day" all keep their amount.
3. **A count backs a tablet count only if it is this claim's count:** a run rule 3 reads as a count, that rule 1 doesn't negate and rules 4 and 5 keep for the claim. "not two tablets" and Panadol's "two tablets" must not back Concor's count of 2. Pass the claim's own names, another medicine's names and its status through. Reuse the mention loop rather than repeating its gate-word logic: the fresh audit flagged that duplication as a drift risk.

Update your own tests where they pinned the old behaviour. Everything else in the hard rules of `briefs/27.1.md` still holds.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass from the repo root, and `git status --porcelain tests/contract` prints nothing. Reply with a short report and the final test count.
