# Batch 27, round 3: six fixes from the supervisor's review

Round 2 passed the gate. The Opus supervisor fuzzed 16,000 replies and found no crash and no path where the checks keep an amount the value check drops, but it found six gaps. The SPEC now settles each one (SPEC.md §2, "Relation checks (batch 27)"), and new contract tests pin them at the end of `tests/contract/test_b27_relations.py` ("round 3"). The contract commit is the latest `test(contract): batch 27`.

## Do, in `anamnesis/providers/relations.py`
1. **"ten a day":** a run with no unit word that ends in the word "a" (which `has_number_role` takes into the run) starts its per-day phrase at that "a". Today "I take Concor 10 a day, 5 in the morning and 5 at night" keeps 10.
2. **«ملي», «مللي», «ميكرو» alone right after a run are the run's unit word, with the unit left open.** `_run_unit` should give them a length of 1 and no unit, so that:
   - rule 3 sees a unit word after the run (no count): «باخد حباية كونكور خمسة ملي» keeps 5;
   - rule 4's "of" check comes after it: «باخد كونكور وخمسمية ملي من البنادول» gives Concor no 500;
   - rule 6's per-day phrase comes after it: «عشرة ملي في اليوم، خمسة الصبح وخمسة بالليل» drops 10.
3. **The Arabic thousands mark «٬» stays inside a digit run,** as in `stated.py`'s `_DIGIT_RUN`: «مش واحد، ١٬٠٠٠» must not leave a stray "١" mention.
4. **The prefix exception narrows:** a word blocks only when it starts with the first word of another medicine's name and that first word has 4+ letters. Drop the reverse direction and the other name words. "para", "sort", "extra" and "acid" must no longer block.
5. **Words of knowing:** a negation word followed by one of the SPEC's words of knowing ("sure", "know", "remember", «عارف» …, normalised; "weiß" normalises to "weiss") negates that word, not the number after it.
6. **An "of" naming the claim wins:** when the word after the run and its unit is an "of" word and the claim's own name starts right after it, the run is the claim's own, whatever the walk-back finds.

Update your own tests where they pinned the old behaviour, and keep the word lists as module constants with SPEC references. Everything else in the hard rules of `briefs/27.md` still holds.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass from the repo root, and `git status --porcelain tests/contract` prints nothing. Reply with a short report and the final test count.
