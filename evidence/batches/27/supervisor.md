# Batch 27: the Opus supervisor

## Round 2 review (31 Oct): SUPERVISOR: CHANGES
**What's clean.** The scope is right: the hook in `claims.py`, the new `relations.py` and the new test file; the ledger line is spend, not code. The checks only ever tighten. They run only on amounts the value check kept and can only null them. In 16,000 fuzzed EN/AR/ES/DE replies there were 0 crashes, 0 new ProviderErrors and 0 amounts kept that the value check alone would drop. Labels are never own names, and rule 2 holds outside the catalogue. All four CEO probes give the required result. Muse's 12 tests are meaningful and weaken nothing, and ruff is clean.

1. **HIGH: rule 6 misses a bare "a day"** (`relations.py:292`, `:321`). `has_number_role("a")` is True, so the run takes in the "a" and the per-day check starts at "day". "I take Concor 10 a day, 5 in the morning and 5 at night." keeps an intake of 10; "ten per day" drops it.
2. **MEDIUM: «ملي»/«مللي»/«ميكرو» alone are not treated as the run's unit word for position** (`relations.py:300`, `:465`, `:569`). «عشرة ملي في اليوم، خمسة الصبح وخمسة بالليل» keeps 10; «باخد كونكور وخمسمية ملي من البنادول» keeps Concor 500; «باخد حباية كونكور خمسة ملي» drops a correct 5.
3. **LOW: «٬» splits a digit run** (`relations.py:200`). «باخد كونكور مش واحد، ١٬٠٠٠» keeps a claim of 1 through a stray "١" mention.
4. **MEDIUM, a SPEC hole: the 4-letter prefix match reaches common words** ("para", "sort", "extra", "acid", "meta"). It only ever keeps an amount, so it is no worse than before batch 27, but it is a hole, not acceptable leniency. Fix: block only on a token that starts with a name's first word.
5. **LOW, SPEC behaviour that fails safe:** «باخد كونكور مش عارف خمسة تقريبا» with no comma drops the 5; "I take Panadol. Five milligrams of Concor" drops Concor's 5. Both end as `insufficient_information`.

The supervisor proved fixes 1–3 with a scratch monkeypatch outside the worktree (all 2,591 tests passed with it).

**The CEO's effect:** all five taken into round 3 (`round3-brief.md`), each settled in the SPEC and pinned by a new contract test; fix 5 as two SPEC rules (words of knowing after a negation; an "of" naming the claim wins over the walk-back). A CEO scratch build with all six fixes passed every batch 27 contract test, lost 0 of 1,452 scored replies, changed 0 of 120 saved claims, and kept the ten traps safe.

## Round 3 re-check (31 Oct): SUPERVISOR: APPROVE
1. **The earlier failing probes now give the right answers:** "Concor 10 a day, 5 in the morning and 5 at night" drops 10 and keeps 5; «عشرة ملي في اليوم، خمسة الصبح وخمسة بالليل» drops 10; «وخمسمية ملي من البنادول» drops Concor's 500; «حباية كونكور خمسة ملي» keeps 5; «مش واحد، ١٬٠٠٠» drops 1; all nine "para", "sort", "extra", "acid" and "meta" probes drop; «مش عارف خمسة» and "Panadol. Five milligrams of Concor" keep 5; the four original CEO probes still hold.
2. **Fuzzer and suite:** 32,000 fuzzed replies, half with knowing words, of-forms, «ملي», «٬» and brand slips: 0 crashes, 0 new ProviderErrors, 0 amounts kept that the value check alone would drop. 2,610 tests pass, ruff clean, `tests/contract` untouched, `claims.py` the same as in round 2.
3. **The six fixes match the new SPEC text** (`relations.py:338`, `:327`/`:601`, `:209`, `:570–579`, `:367`, `:468`). The narrowed prefix match blocks nothing the SPEC wouldn't, so it can't keep an amount the SPEC drops; the "of" rule only overrides rule 4.
4. **LOW, fails safe:** "I take Concor ten a day for five years" drops 10, because rule 6 takes "five years" as a splitter; «عشرة ملي في اليوم من خمس سنين» too.
5. **LOW, fails safe:** German "ich weiß nicht fünf Milligramm" drops the 5: the knowing rule covers only a negation before the knowing word.
6. **Muse's six new tests** use phrasings of their own and weaken nothing.

**The CEO's effect:** the supervisor's request to re-measure was already met: the CEO's three measurements ran on round 3 (0 of 1,452 replies lose a fully-right score, 0 of 120 saved claims change, ten of ten traps fail safe). Items 4 and 5 fail safe and go to a batch 27.1 after batch 28: a number followed by a duration word is a duration, never a mention; and a negation right after a word of knowing ("weiß nicht") is cancelled too.
