# Batch 24 review: Spanish and German number words, grounded ingredient fields, the empty strength and two catalogue releases (SPEC §2, §3)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 10 rounds, goal pinned with its goal tool in each

**What the batch adds:**
- **Spanish and German number words:**
  - in `stated_amounts` and `parse_amount_text`, with `coma` and `komma` as the decimal point;
  - Spanish `y` joins only a ten to a unit, or a number to a half;
  - the articles count as 1 only before a unit word;
  - German numbers are read as whole tokens, with the halves (`eineinhalb` 1.5, `einhalb` 0.5).
- **Grounded ingredient fields:** an unsaid claim `inn` becomes null. An empty or ungrounded amount label takes the claim's grounded `inn`, or its name, unless it names an ingredient of the claim's own catalogue entry.
- **The empty strength:** a `strength` with no ingredients is no strength, and no longer drops the intake beside it.
- **Release:** `prolongada`, `modificada`, `retardtablette(n)` and `retardkapsel(n)` count as release words. Glucophage and Augmentin imply no release.

**Who did what:**
- **Claude Code (Opus 5.5), as CEO,** wrote:
  - the SPEC lines;
  - the brief;
  - the contract (11bf9de), amended after the CEO's reference build and before any Muse run (43a7e84, `reference.md`).

  The reference build found four problems in the CEO's own contract, all fixed before the build:
  - the SPEC's `einhalb` as 1.5;
  - Spanish `once` against English "once";
  - grounding that broke the combination and salt pins of batches 8 and 21;
  - "cinco cien" stating 105.

  One mutant per behaviour was applied, and the contract caught all ten.
- **Muse wrote all the code:**
  - `providers/stated.py`, `providers/numbers.py`, `providers/claims.py`, `core/reconcile.py` and `core/catalogue.yaml`;
  - its unit tests, in `tests/unit/test_b24_extra.py`.
- **The held-out guard** (16cab05, before the run): Muse's export shows no read under `evidence/` or the fine-tune data (`goal.md`).
- **A separate Opus supervisor** (a Claude subagent of the engine session) reviewed each round (`supervisor.md`):
  - **Round 1: CHANGES,** with 1 blocker, 2 majors and 5 minors. The CEO accepted all eight. Findings 1–3 came from the CEO's own SPEC: the CEO's reference build had them too.
    - **The blocker:** an unsaid second ingredient line, relabelled to the brand, reached a false `match`.
    - **The majors:** English "five mil" stated 1000, and a salt said inside a German compound was lost.
  - **Round 2's contract** (`test_b24_round2.py`, 26 tests) pins all eight. It was proved on a reference build (2,188 passed) with one mutant per fix.
  - **Round 2: CHANGES.** All eight fixes held, with 1 major and 2 minors left:
    - **The major:** English "social media" stated a Spanish half, so an invented 0.5 mg alprazolam intake reached `match`.
    - **The minors:** `mil` before an English abbreviation multiplied, and number words that need a neighbour slipped past the amount-only label check.
  - **Round 3's contract** (`test_b24_round3.py`, 18 tests) pins those three. It was proved on a reference build (2,206 passed) with one mutant per fix.
  - **Round 3: CHANGES.** All three fixes held, with 3 majors left: "um halb zwei" (1:30) stated 2.5, "por ciento" stated 100, and `medio`/`media` in their other senses (a means, a medium, an average) stated 0.5.
  - **The CEO's own sweep:** before writing round 4, the CEO checked 66 everyday Spanish and German phrases and found one more: the clock time "a las dos y media" (2:30) stated 2.5.
  - **Round 4's contract** (`test_b24_round4.py`, 26 tests) pins all four. It was proved on a reference build (2,232 passed) with one mutant per rule.
  - **Round 4: CHANGES,** with 2 highs, 1 medium and 2 minors:
    - adjacent Spanish or German number words added up ("diez treinta", 10:30, stated 40);
    - a half before a dose word joined a clock hour. The CEO had removed that check as redundant in round 4, when its surviving mutant really pointed to a missing test;
    - German "in Acht nehmen" stated 8.
  - **Round 5's contract** (`test_b24_round5.py`, 23 tests) pins all five. It was proved on a reference build (2,255 passed) with one mutant per fix.
  - **Round 5: CHANGES,** with 2 highs, 1 medium and 1 minor:
    - an article added to a number ("vier Ein-Gramm-Tabletten" stated 5);
    - finite forms of `Acht`;
    - "um sechs hundert Milligramm" stated 600.
  - **Round 6 is structural.** Five reviews in a row had found new idioms, so the CEO replaced the idiom lists with one rule: a Spanish or German number states an amount only right before a unit or dose word. German number words never combine, and an article joins no number. Bare Spanish or German amounts now fail closed. 35 contract tests; the earlier tests that expected bare numbers to count now say them with a unit or dose word.
  - **Round 6 had no review, on purpose.** The CEO's own probe and differential had already found its last gaps: a Spanish or German number joined an English one after it ("cinco five mg" stated 10), and one close path skipped the amount rule. Round 7 (13 contract tests) closed them.
  - **Round 7 (covering 6 and 7): CHANGES,** with 3 highs and 3 minors:
    - a Spanish or German number joined an English hundred, thousand, half or point after it ("sechs hundred Milligramm" stated 600, and Ibuprofen 600 mg reached `match`);
    - a clock hour joined `mil` ("a las cinco mil miligramos" stated 5 and 5000, and Concor 5 mg reached `match`);
    - clock minutes joined a count ("a las ocho y cuarenta y dos pastillas" stated 40 and 42, and Lipitor 40 mg reached `match`).
  - **Round 8 (31 contract tests):**
    - **One rule for the Spanish clock time,** not two point fixes: an hour after `la` or `las` and its minutes state nothing unless a unit or dose word follows.
    - **An English or Arabic multiplier, half or point closes a Spanish or German run first,** and a decimal begun in Spanish or German with an English point states nothing.
    - **No German clock rule:** it was redundant with round 6.
    - **Proof:** a reference build (2,333 passed) with one mutant per rule. One mutant survived the first run, and a missing pin was added for it.
  - **Round 8: CHANGES,** with 2 highs on plausible inputs:
    - a Spanish or German number of 100 or more joined an English number after it ("zweihundertfünfzig two hundred fifty Milligramm", a German strength repeated in English, stated 150);
    - the clock rule read the English "LA" of long-acting brands as an hour ("Cardizem LA four hundred twenty milligrams" stated 120). That was a regression in English.
  - **Round 9 (31 contract tests):**
    - **No mixed runs:** a number run never mixes languages, in either direction. That replaces round 7's pair check and round 8's close.
    - **The hour:** `la` is an hour only in "la una", and `las` only before a number up to 24.
    - **Minutes:** `menos` minutes and compound minutes.
    - **Proof:** a reference build (2,364 passed) with one mutant per rule. One mutant survived the first run, and a missing pin was added for it.
    - **English and Arabic:** unchanged on all 21,747 fuzz phrases.
  - **Round 9: CHANGES,** with 1 high on plausible inputs and 1 minor:
    - after `las`, an English number word was read as an hour ("Me tomo las two hundred fifty milligram tablets" stated 150). The English plural "Cardizem LAs" did the same in English-only text. That came from the CEO's round 8 SPEC, which allowed an English hour after `las`;
    - an article joined a number of 100 or more ("zweihundert Ein-Gramm-Tabletten" stated 201).
  - **Round 10 (14 contract tests):**
    - **No English hour:** after `las`, only a Spanish number word or digits make an hour, and English after `las` reads as before batch 24. The CEO removed the round 8 word-salad pin that had asked for an English hour.
    - **Articles:** an article joins no number before it, of any size; only Spanish `y` joins one.
    - **Proof:** a reference build (2,377 passed) with one mutant per rule.
  - **Round 10: APPROVE,** with 3 minors, none on a plausible input:
    - an English number, an English `point` and Spanish digit words read as one decimal ("at one point cinco miligramos" states 1.5);
    - German and Spanish inside one number ("hundert veinticinco microgramos" states 125);
    - an English hour inside Spanish clock syntax ("a las eight y cinco mil miligramos"), which follows from round 10's design.

    **What the review covered:**
    - Both round 10 rules held on 20,000 generated "LA", "LAs" and "las" phrases.
    - English and Arabic matched 843f64f on 40,000 random inputs.
    - Every earlier fix held.
    - A 90,000-input fuzz found no new family.

**The gate:**
- **Round 1:** pass, 2,172 tests.
- **Round 2:** pass, 2,198 tests.
- **Round 3:** pass, 2,216 tests.
- **Round 4:** pass, 2,242 tests.
- **Round 5:** pass, 2,265 tests.
- **Round 6:** pass, 2,299 tests.
- **Round 7:** pass, 2,313 tests.
- **Round 8:** pass, 2,344 tests.
- **Round 9:** pass, 2,376 tests.
- **Round 10:** pass, 2,390 tests, ruff clean, contract untouched (`gate.json`).
- **Muse's own goal:** inside its sandbox, one test needs a local socket the sandbox forbids, so in round 1 it closed the goal as "blocked". The gate, run outside the sandbox, passed both times. In round 10 the export shows the goal pinned but never closed, though Muse's last check reports it marked complete; the gate passed.

**A differential check (rounds 3–10):** `stated_amounts` was run on two corpora.
- **21,747 English and Arabic phrases** (the round 2 supervisor's fuzz set): Muse's rounds 3 to 10 give exactly what the code before batch 24 gave on every one.
- **25,292 Spanish, German and mixed phrases:** Muse and the CEO's reference disagree on 6 after round 3, 2 after rounds 4 and 5, 8 after round 7, and none after rounds 8 to 10. Through round 5 the reference was the looser one, and Muse follows the SPEC: the reference used a half as the base of a decimal ("medio coma siete" as 1.2) and accepted German `null` after English "point". After round 7 the reference was the stricter one: Muse keeps the English value of an English word said after a dropped Spanish one ("quinientos hundred" states 100), as the SPEC's "English unchanged" rule requires. Round 6's differential also found the reference's own bug, an English "hundred" stating a Spanish part, which round 7 pins.

**A behavioural check beyond the contract.** Every committed fine-tune reply was re-scored with Muse's parser after each of the ten rounds, against the prediction committed before the build (`rescore-prediction.md`, 7007699). All ten rounds match it number for number:
- **Spark 1.3, fully right:** 193 → 203 on r1's splits, and 38 → 40 on test_spain.
- **Base Glimmer's harmful claims after the checks:** 54 → 0, and 9 → 0, with the scorer counting on the product's output.
- **r1 and r2:** unchanged, with 0 harmful claims.

**Found, not fixed here:**
- A brand outside the catalogue, said with a strength, becomes its own ingredient, so it's reported as `missing_modality`, not `unresolved_name` (`reference.md`). It fails safe.
- A bare Spanish or German amount ("Panadol de quinientos") states nothing, by design. It fails closed.
- A decimal begun in one language and ended in another ("dos point cinco miligramos", "two point cinco") states nothing. It fails closed.
- In a mixed phrase, the English words state what the code before batch 24 stated for them ("seis hundred milligrams" states 100, "zweihundertfünfzig two hundred fifty Milligramm" states 250, 2, 100 and 50).
- Word salad that still states a number nobody said ("um sieben mil quinientos pastillas" states 7500), and a Spanish decimal that ends in English digits ("ocho coma three milligrams" states 8.3, the number said).
- A digit time with a colon ("a las 8:40") states its minutes in every language, as the code before batch 24 does in English. Recorded for after the freeze.
- Two cases fail closed:
  - digits up to 24 after the English plural "LAs" with no unit after them ("two Cardizem LAs 4 times a day") state nothing;
  - "doscientos un miligramos" states 1, never 201.
- Older than this batch: the catalogue route for amount labels keeps a salt that contradicts the one said.
- **The round 10 supervisor's three minors,** recorded for after the freeze:
  - an English `point` with Spanish digit words after an English number ("at one point cinco miligramos" states 1.5);
  - German and Spanish inside one number ("hundert veinticinco microgramos" states 125, "acht y medio comprimido" 8.5);
  - an English hour inside Spanish clock syntax ("a las eight y cinco mil miligramos" states 5 and 5000).
- Older than this batch, and recorded for after the freeze: English "point" and "half two" forms, and a `name_text` cut from a longer brand.

**Cost:** Muse $3.15, $0.83, $0.76, $0.65, $0.98, $1.09, $0.84, $1.03, $1.02 and $0.62 for rounds 1–10, so $10.97 in all (`evidence/spend/muse_ledger.jsonl`).

Verdict: PASS
