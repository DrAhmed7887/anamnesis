# Batch 21 review: three digit sets, the salt-or-release question, the live-run fixes (prompts, ingredient aliases, pairing by intake) and number words (SPEC §2, §3, §7)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 3 rounds, goal pinned with its goal tool in each

**Who did what:**
- Claude Code (Opus 5.5), as CEO, wrote the contract in two parts:
  - part 1, before any real media existed: the QM M4 round 2 items and the supervisor's 19.1 pins;
  - part 2, after the first live runs on the old code (`live-before.md`, 28 Oct). Those runs found that every dose spoken in words had been dropped since batch 20, that French and Latin ingredient names never paired, and that "Norvasc 5 mg" was paired with the 10 mg box.
- The CEO also wrote the SPEC lines, the brief and the round 2 and 3 briefs.
- Before each round, the CEO proved the contract with a throwaway reference build: 921, then 973, then 1,002 passed. For round 3 the proof was the supervisor's fix copy, 1,016.
- Muse wrote all the code.
- An independent Opus supervisor reviewed every round: CHANGES, CHANGES, then APPROVE (`supervisor.md`).

**What the review rounds found:**
- **Round 1:** the new number-word split let "eight hundred seventy-five one hundred twenty-five" state **876**, a dose nobody said.
- **Round 2:** the CEO's own rule for one-word Arabic hundreds broke 900 numbers from 2100 to 2999, and "and a hundred" moved a units word. Muse flagged the «ألفين» gap in its own report.
- **The fixes:** each one was pinned by contract cases. The supervisor then brute-forced 1–2999 in both languages and fuzzed 60,000 digit strings.
- **The CEO's errors:** two of the bugs came from the CEO's own spec wording: the «و» rule in round 1 and the plain ≥ 100 rule in round 2.

**Privacy:** the round 1, 2 and 3 Muse exports carry no personal skill names. Three personal skills were disabled in Muse on 28 Oct, and the remaining personal skills live under `~/.claude/skills`, which `--no-foreign-personal-context` excludes.

**Spend:** Muse $1.83320, $0.79609 and $0.49624, **$3.12553 for the batch** (estimated). The live "before" runs cost $0.33919 on the adapter ledger.

**Follow-ups, after the freeze:**
- NFC in `catalogue.normalise`.
- A thousand word after a group of 100 or more, or after a thousands part: "two hundred and one thousand", «ألفين وألف».
- `_word_amounts` is one line over 50.
- The Dutch "clavulaanzuur" alias.

**Next:** all pre-registered cases run again, unchanged, on the merged code (`manifest.md`, `live-before.md`), and the results go into `live-after.md` in the same table shape.

Verdict: PASS
