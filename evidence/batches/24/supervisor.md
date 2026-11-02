# Batch 24: supervisor review

## Round 1 (Opus, independent context, 29 Oct). Builder: Muse Code (`muse-spark-1.3`)

SUPERVISOR: CHANGES

1. **Blocker:** `anamnesis/providers/claims.py:295-298`, reaching `anamnesis/core/reconcile.py:31` and `:97`. A junk second ingredient line can now reach `match`.
   - **Input:** turn "I take Panadol, 500 mg with 65 mg, two tablets in the morning."
     - Reply strength: `[{"inn":"caffeine","amount":"65"},{"inn":"paracetamol","amount":"500"}]`, per tablet.
     - Pack: "Panadol 500 mg tablets" (paracetamol 500).
   - **Got:** `match`, with `needs_clinician_review` false.
     - "caffeine" was never said, so it is relabelled "Panadol".
     - The Strength duplicate check compares `canonical_inn` ("panadol" against "paracetamol"), so it passes.
     - `_resolve_inn` then maps both lines to paracetamol. `_identity` keeps one INN, and `_strength_type`'s dict keeps only the last line.
     - The pre-batch copy gives `insufficient_information`.
   - **Junk variant:** turn "Concor. I used to take ten milligrams, now five milligrams."
     - Lines `("bisoprolol","5"),("","10")` give `match` against a Concor 10 mg pack.
     - Lines `("bisoprolol","10"),("string","5")` give `match` against a Concor 5 mg pack.
     - The pre-batch copy gives `insufficient_information` for both. Line order decides the result.
   - **Why:** SPEC §3 defines `match` as "every comparison that could be made agreed", but one line is never compared. The brief's rule "Two labels relabelled to the same brand make the strength invalid" has to hold when the brand and the INN name the same moiety.
   - **Fix:**
     - After relabelling, resolve each label as `_resolve_inn` does. If two lines resolve to one moiety, the strength fails validation and is dropped, so the intake goes with it.
     - In `_identity`, also flag a conflict when `len(inns) < len(strength.ingredients)`.
2. **Major:** `anamnesis/providers/stated.py:76` and `:252`. `mil` is a thousand word with no language gate.
   - **Input:** "Panadol, I take five mil twice a day."
   - **Got:** it states {5, 1000, 5000}; the pre-batch copy states {5}.
     - A reply intake of paracetamol 1000 mg against a Panadol 1000 mg pack gives `match`.
     - The pre-batch copy drops that intake and gives `insufficient_information`.
     - "ten mil syringe" now states 10, 1000 and 10000; "a mil" states 1000.
   - **Why:** brief item 8 says "English and Arabic behave exactly as before", and §2 says "A number a model writes is kept only if the source states it". In English speech "mil" means millilitre, the same kind of clash that kept `once` out.
   - **Fix (needs a SPEC line):** `mil` is a thousand word only when:
     - a Spanish number word comes before it in the run ("dos mil");
     - or a Spanish number or unit word comes right after it ("mil doscientos", "mil miligramos").

     Otherwise it ends the run. The contract cases stay green.
3. **Major:** `anamnesis/providers/claims.py:273`, with the prefix rule at `:230`. A salt the patient said is lost.
   - **Input:** turn "Ich nehme Beloc-Zok, das ist Metoprololtartrat, 50 mg am Morgen."
     - Reply: `inn` "metoprolol tartrate", intake `{"inn":"metoprolol","amount":"50"}`.
     - Pack: "Beloc-Zok 50 mg Metoprololsuccinat Retardtabletten" (metoprolol succinate 50, modified).
   - **Got:** `inn` becomes null, because "tartrate" sits inside the compound and begins no turn word. The tartrate salt is lost and the pair is `match`. The pre-batch copy gives `formulation_mismatch`.
   - **Why:** §3 rule 6 says "named salts for the same canonical ingredient differ" gives `formulation_mismatch`. `_inn_and_salt` maps both "metoprolol tartrate" and "Metoprololtartrat" to (metoprolol, tartrate).
   - **Fix (needs a SPEC line):** a field is also grounded when its `(canonical_inn, salt_of)` pair equals that of a word or run in a cited turn.
4. **Minor:** `stated.py:308-309` (a half word joins any number before it) and `:264` (`coma`).
   - "zwei halbe Tabletten" means two half tablets (1 tablet), but states {0.5, 2, 2.5}.
   - English "two media reports said five" states {0.5, 2, 2.5, 5}; the pre-batch copy states {2, 5}.
   - "she was in a coma two years ago" states {0.2, 2}; the pre-batch copy states {2}.
   - **Why:** nobody said 2.5 or 0.2. §2 joins `medio`/`media` to a number only through `y`, and German writes n + ½ as one word (`zweieinhalb`).
   - **Fix:**
     - A Spanish or German half word joins a number before it only through `y`. Otherwise it closes the run and states 0.5 on its own.
     - `coma`/`komma` act as the decimal point only inside an open run.
5. **Minor:** `stated.py:215` (`_digit_value`).
   - "zwei Komma null fünf" states {2, 5} and misses 2.05, while "dos coma cero cinco" gives 2.05.
   - **Why:** brief item 5 says "the digit words after them may be English, Spanish or German", and German zero is `null`. It fails closed.
   - **Fix:** accept `null` as a digit, but only after a decimal word.
6. **Minor:** `stated.py:421-429`.
   - Decomposed-accent (NFD) text states nothing: "veintitrés miligramos", "fünfhundert Milligramm", "dieciséis". `normalise` turns the combining accent into a space. It fails closed.
   - **Fix:** `unicodedata.normalize("NFC", text)` at the start of `stated_amounts`, as the alias table already does.
7. **Minor:** `claims.py:205-212`. The "only numbers" check lets amount-only labels through.
   - Labels "milligrams", "five milligrams", "units", "treinta y cinco", "two and a half" and "dos coma cinco" are kept as the INN.
   - With the turn "Concor five milligrams every morning", label "milligrams" gives `insufficient_information`, while label "string" gives `match`.
   - **Why:** the SPEC says a field "made only of digits, unit words or number words … is never grounded". English unit words and the joiners `y`, `and`, `a`, `coma` and `point` get through. It fails closed.
   - **Fix:** skip the joiners and the English unit words (milligram(s), gram(s), microgram(s), millilitre(s), unit(s), iu) in this check.
8. **Minor (test):** `tests/unit/test_b24_extra.py:30-42`.
   - The second-turn label is accepted through the catalogue route, because bisoprolol is Concor's ingredient, so turn grounding of a label is never tested.
   - **Fix:** use a `name_text` that doesn't resolve to a catalogue entry.

Repro scripts (`p2.py`, `p5.py`, `p6.py`, `p8.py`) were kept in the CEO's scratchpad. The worktree was left unchanged.

**Checked and clean, by probe area:**
- **Number words:** apart from findings 4–6, every probe is clean:
  - trescientos veinticinco gives 325, ciento uno 101, mil doscientos 1200, dos mil quinientos 2500 and veintiún 21. Accent-free and upper-case forms behave the same.
  - "una vez y media" states only 0.5, which fails closed.
  - dreihunderteins gives 301, siebenundsiebzig 77, neunhundertneunzig 990 and "drei Komma eins" 3.1. anderthalb states nothing and "ein halb" states 0.5.
  - "2 y medio" states only its parts.
  - Runs broken by a comma or line break, "cinco cien", "diez y cincuenta", the articles, zweimal and Achtung all follow the SPEC.
- **English and Arabic:** every English and Arabic number input gives the same result as before the batch. That covers once, twice, "two and a half", "ten and fifty", the 875/125 forms, "a hundred", «خمسمية وخمسين», «ألفين وخمسمية» and «اتنين ونص». Only Spanish or German homographs differ: mil, media, medio, coma, dos, uno, elf.
- **Grounding:** apart from findings 1, 3 and 7:
  - A clitic on the turn's word, a combination said by its brand, salts, a wrong INN (relabelled to the name) and "paracetamol" (two entries) all behave as the SPEC says.
  - The empty strength keeps the intake and drops its release.
  - Every other drop still nulls both amounts.
  - Short or prefix-grounded junk such as "a" or "Concora" fails closed.
- **Release:**
  - The six words are added, and no enteric word was: "magensaftresistent" and "gastrorresistente" claims stay `insufficient_information`.
  - Glucophage and Augmentin are `unknown`, the other entries are unchanged, and Glucophage against an XR pack is `insufficient_information`.
- **Outside the brief:** the prompts, contract tests, conftest, `pyproject.toml` and `uv.lock` are untouched. No dependency was added, and no existing test was changed. The only side edits are a harmless int-tuple check in `_hundred_cut` and a renamed loop variable (`cited_id`).

**CEO's triage:** all eight accepted. Findings 1–3 come from the CEO's own SPEC design, not from Muse's build: the CEO's reference build had the same three. All eight are pinned in `tests/contract/test_b24_round2.py`, proved on a reference build (2,188 passed), with one mutant per fix, each caught.

## Round 2 (Opus, independent context, 29 Oct). Builder: Muse Code (`muse-spark-1.3`)

SUPERVISOR: CHANGES. All eight round 1 fixes hold; it reran the full suite (2198 passed) and changed nothing in the worktree. One way to a false `match` was still open.

1. **Major: English "media" counted as a half, so an invented 0.5 could reach `match`.** `providers/stated.py` (`SPANISH_HALF`).
   - **Input:** the turn "I take alprazolam at night, I read about it on social media.", with Spark writing an alprazolam intake of 0.5 mg. The pack is Alprazolam 0.5 mg.
   - **Got:** `stated_amounts` gave {0.5}, so the amount was kept, and the result was `match`. Before the batch it was `insufficient_information`. "por medio de" and "medio ambiente" also stated 0.5.
   - **Fix:** give `medio` and `media` the `mil` rule. They are a half only after `y`, after a Spanish number word or `un`/`una`, or before a Spanish unit or dose word.
2. **Minor: the amount-only label check missed number words that need a neighbour.**
   - **The words:** `mil` (after the round 2 fix), `ein` and `un` before a unit, `null` after `komma`, and `zero`/`cero`.
   - **The effect:** "mil miligramos", "ein Gramm", "cero coma cinco", "zero point five" and "null Komma fünf" were kept as labels. That fails closed.
   - **Fix:** count every word the number reader classifies, plus `null`.
3. **Minor: `mil` before an English unit abbreviation multiplied.**
   - **Inputs:** "five mil ml" stated 5000, "ten mil mg" 10000, and «خمسين» "mil mg" 50000.
   - **Fuzz:** of 21,747 English and Arabic phrases compared with 161d411, 21 differed, and every one was this pattern.
   - **Fix:** after `mil`, only Spanish unit words count.

**Round 1 findings, rechecked:**
- **1–8 are fixed,** each with probes beyond the contract.
- **On pack readings, only those whose own lines collapse to one ingredient change.** Example: [Panadol 1000, paracetamol 500] was a false `match` before batch 24 and is now `insufficient_information`.

**English and Arabic against 161d411:** 118 of 140 hand-picked inputs give identical results. Each of the other 22 has a Spanish or German homograph, or `mil` before a unit.

**CEO's triage:** all three accepted and pinned in `tests/contract/test_b24_round3.py` (18 tests, 13 fail on round 2). They were proved on a reference build (2,206 passed), with one mutant per fix, each caught. Still recorded as limits: the rare English homographs `dos`, `uno` and `elf` (German 11). Each states only its own small number, and none was found in a real transcript.

## Round 3 (Opus, independent context, 29 Oct). Builder: Muse Code (`muse-spark-1.3`)

SUPERVISOR: CHANGES. All three round 3 fixes held as written, and every earlier fix held. Three false `match`es were still open, each reproduced end to end, and each from batch 24's own Spanish and German code.

1. **Major: a half absorbed the number after it.**
   - "um halb zwei" (1:30) stated 2.5, so a 2.5 mg intake reached `match` against Concor 2.5 mg.
   - Also: "halb zwölf" stated 12.5, "eine halbe Zehn-Milligramm-Tablette" 10.5, and "uno y medio diez miligramos" 11.5.
   - **Fix:** a Spanish or German half ends its run.
2. **Major: "por ciento" stated 100.** "me bajó la ansiedad un veinte por ciento" reached `match` against Sertralina 100 mg.
   - **Fix:** `cien` and `ciento` right after `por` state nothing.
3. **Major: round 3's own contexts still let non-number `medio`/`media` through.** Each of these stated 0.5:
   - "en un medio sobre salud";
   - "una media de dos al día";
   - "es un medio para dormir";
   - "trabajo y medio ambiente";
   - "un nivel medio sobre el tema".

   **Fix:** count `y` only after a number word, drop `un`/`una` as contexts, and drop `sobre` from the dose words.
4. **Minor:** a one-letter word was grounded as a prefix ("vitamin d" by "de"). This is the same on 161d411, which had no grounding at all.
5. **Backlog, the same on 161d411:**
   - "at some point two years ago" states 0.2, and "at this point five" states 0.5;
   - British "half two" states 2.5;
   - a `name_text` "Panadol" cut from "Panadol Extra 500 mg" matches a Panadol 500 mg pack.

**CEO's triage:**
- **1–4 accepted and pinned** in `tests/contract/test_b24_round4.py` (26 tests, 18 fail on round 3).
- **One more case of the same kind:** before writing round 4, the CEO swept 66 everyday Spanish and German phrases (times, dates, ages, percentages, idioms) on the reference. One more phrase stated a value nobody says: clock time, "a las dos y media" (2:30) stated 2.5. It is pinned too.
- **What the sweep left:** every remaining stated value is a number someone says, as English already allows ("halb so schlimm" 0.5, "tausend Dank" 1000).
- **Proof:** a reference build (2,232 passed), with one mutant per rule, each caught.
- **Not in batch 24:** the backlog items (5) are older than this batch. They are recorded for after the freeze: the English "point" and "half two" forms, and a cut `name_text`.

## Round 4 (Opus, independent context, 29 Oct). Builder: Muse Code (`muse-spark-1.3`)

SUPERVISOR: CHANGES. Every earlier fix held, but four round 4 idioms still led to a false `match`, each run end to end with an invented amount.

1. **High: two adjacent Spanish or German number words added up.**
   - "a las diez treinta" (10:30) stated 40, and 40 mg reached `match` against Lipitor 40 mg; "um zehn dreißig" did the same.
   - "dos tres pastillas" and "zwei drei Tabletten" stated 5, and "zweieinhalb Fünf-Milligramm-Tabletten" stated 7.5.
   - "dos cincuenta" stated 52.
   - **Fix:** a word under 100 after a word under 100 closes the run unless `y` joins them.
2. **High: a half before a dose word joined the clock hour.** "a las dos y medio comprimido" stated 2.5.
   - **The CEO's error:** the reference had a check for this inside `_y_joins`, which round 4 removed as redundant after its mutant survived. The surviving mutant pointed to a missing test, not to dead code.
3. **Medium: German `Acht` meaning "care".** "in Acht nehmen" and "außer Acht lassen" stated 8, and candesartan 8 mg reached `match`.
4. **Minor, fails closed:** a decomposed (NFD) label and turn skipped the amount-only check.
5. **Minor, fails closed:** "una y media" stated 1, never 1.5.

**CEO's triage:** all five accepted and pinned in `tests/contract/test_b24_round5.py` (23 tests, 17 fail on round 4). They were proved on a reference build (2,255 passed), with one mutant per fix. Every mutant is caught: the NFC mutant counts only when it takes NFC off both the field and the turns, since the fix is the pair.

## Round 5 (Opus, independent context, 29 Oct). Builder: Muse Code (`muse-spark-1.3`)

SUPERVISOR: CHANGES. Every earlier fix held. Three more paths to a false `match` were open, each run end to end with an invented amount.
1. **High: an article counted as 1 still added to the number before it.**
   - "vier Ein-Gramm-Tabletten" stated 5, "a las cuatro un gramo" 5, and "um neun ein Gramm" 10.
   - An English word after a Spanish one added too: "a las diez thirty" stated 40.
2. **High: German `Acht` meaning "care" in finite forms stated 8.** For example "ich gebe Acht", "gib Acht" and "nimm dich in Acht"; candesartan 8 mg then reached `match`.
3. **Medium, a SPEC decision:** "um sechs hundert Milligramm" stated 600 through the "fünf hundert is 500" rule.
4. **Minor:** "seit zweitausendzehn fünf Milligramm" stated 2015.

**CEO's triage: a structural rule instead of a sixth list of idioms.** Five rounds in a row found new idioms that stated a number nobody said, so round 6 changes how Spanish and German are read:
- a Spanish or German run states its values only when a unit or dose word follows it;
- German number words never combine;
- `hundert` and `tausend` are plain numbers;
- an article joins no number.

**What this closes:** every finding of rounds 1–5, and the whole class (times, dates, ages, percentages, idioms) whatever the phrasing.

**What it costs:** a bare Spanish or German amount ("Panadol de quinientos") states nothing. That fails closed.

**The contract:**
- **Earlier tests rewritten:** those that expected bare Spanish or German numbers to state a value now say them with a unit or dose word.
- **New:** `tests/contract/test_b24_round6.py` (35 tests, 22 fail on round 5).
- **Proof:** a reference build (2,289 passed), with one mutant per rule.
- **English and Arabic:** they still give exactly what the code before batch 24 gave on all 21,747 fuzz phrases.

## Round 6: no supervisor review, on purpose
Round 6 passed its gate (2,299 tests). Before any review, the CEO ran two checks of his own:
- the probe of the round 6 reference on the open surface (a number nobody said, right before a unit word);
- the differential of Muse's round 6 against the CEO's reference, on 25,292 Spanish, German and mixed phrases.

They found the gaps a review would have reported. So round 7 went straight to the builder, and the supervisor reviews round 7, covering rounds 6 and 7. The gaps:
1. **A Spanish or German number added an English one after it.** "cinco five mg" stated 10, and an invented 10 mg reached `match` against Concor 10 mg. "diez thirty milligrams" stated 40.
2. **An adjacency close skipped the amount rule.** "elf cinco miligramos" stated 11.
3. **An English "point" with Spanish or German digit words made a decimal outside any amount.** "la point seis" stated 0.6.
4. **In the CEO's own reference only:** an English "hundred" after a Spanish number stated the Spanish part without an amount ("ochocientos hundred" stated 800). Muse's code didn't have this. It is pinned anyway.

On the same corpus, English and Arabic gave exactly the results of 161d411, in both Muse's code and the reference.

## Round 7 review (covers rounds 6 and 7): SUPERVISOR: CHANGES
1. **High: a Spanish or German number joined an English hundred, thousand, half or point after it.**
   - "Ich nehme Ibuprofen und um sechs hundred Milligramm ASS." stated 600, and an invented 600 mg reached `match` against Ibuprofen 600 mg.
   - "Tomo meloxicam a las siete point five milligrams." stated 7.5, "cinco and a half mg" 5.5, "zwei thousand Milligramm" 2000 and "treinta y five mg" 35.
2. **High: Spanish `mil` joined a clock hour.** "a las cinco mil miligramos" stated 5 and 5000, and an invented 5 mg reached `match` against Concor 5 mg.
3. **High: `y` joined clock minutes to a count.** "a las ocho y cuarenta y dos pastillas" stated 40 and 42, and an invented 40 mg reached `match` against Lipitor 40 mg.
   - The supervisor's caveat: 2 and 3 could be read as numbers said before a unit or dose word, which was out of scope. Finding 1 alone justifies CHANGES.
4. **Minor, fails closed:** English "coma" ("GCS eight coma three" stated nothing) and "two point cinco" (nothing).
5. **Minor:** "null Komma fünf Milligramm" stated only 5.
6. **Minor:** `_close` in `stated.py` is unused.

**Held:** round 6's three rules, round 7's fixes 2 and 3, every earlier fix, and English and Arabic, unchanged on 10,328 inputs.

**CEO's triage:**
- **Findings 2 and 3 share one cause, the Spanish clock time.** So they get one rule, not two point fixes: an hour after `la` or `las` and its minutes state nothing unless a unit or dose word follows. The minutes are a Spanish number after `y`, or a Spanish 10–59 said straight after the hour.
- **Finding 1:** an English or Arabic hundred, thousand, half or point closes an open Spanish or German run first.
  - **A decimal begun in Spanish or German with an English point states nothing.** The close alone made "dos point cinco miligramos" state 0.5, a value 161d411 never stated.
- **No German clock rule:** German numbers never combine (round 6), so the close covers "um sechs hundred". An `um` rule would also have made "um acht Komma fünf Milligramm" (raised by 8.5 mg) state only 5.
- **Finding 4:** English "coma" reads as 161d411 did again. "two point cinco" stays: it fails closed.
- **Finding 5:** fixed in round 8.
- **Finding 6:** the round 8 brief asks for the cleanup.

## Round 8 review: SUPERVISOR: CHANGES
1. **High, plausible: a Spanish or German number of 100 or more joined an English number after it.**
   - "Ich nehme Pregabalin zweihundertfünfzig two hundred fifty Milligramm." stated 150, and Pregabalin 150 mg reached `match`.
   - So did "vierhundertzwanzig four hundred twenty" (120), "dos mil quinientos two thousand five hundred" (1500), "quinientos fifty milligrams" (550) and "fünfhundert fifty Milligramm" (550).
   - Round 7's pair check needed both numbers under 100.
2. **High, plausible: the clock rule read the English "LA" of long-acting brands as an hour, so English no longer read as before batch 24.**
   - "I take Cardizem LA four hundred twenty milligrams of diltiazem." stated 120, and Cardizem LA 120 mg reached `match`. "Inderal LA two hundred fifty mg" stated 150.
   - "Adalat LA 30 ملغ" lost its 30.
3. **Minor (word salad, or amounts no tablet has):**
   - `menos` minutes;
   - compound minutes joining `mil` ("hasta la una y treinta y cinco mil doscientos miligramos" stated 5200);
   - German before Spanish `mil` ("um sieben mil quinientos pastillas" stated 7500);
   - English before Spanish ("two hundred cincuenta milligrams" stated 250);
   - "null point fünf Milligramm" stated 0.5, "ocho coma three milligrams" 8.3, and "treinta y ein mg" 31.

**Held:** the Spanish clock rule (hours, minutes, `y media`, `y cuarto`, digit hours), no German clock rule, the closes before English and Arabic multipliers, halves and points, the mixed decimal, `y`, `coma`/`komma`, German `null`, and every earlier fix except round 7's no-join for numbers of 100 or more.

**CEO's triage:**
- **Finding 1 becomes one rule:** a run never mixes languages, in either direction. It replaces round 7's pair check and round 8's close.
- **Finding 2:** `la` is an hour only before `una`, and `las` only before a number up to 24. Spanish says "la" only for one o'clock, so no English "LA" can trigger it.
- **From item 3, fixed:** `menos` minutes, compound minutes, English before Spanish (covered by the no-mixing rule), and `y` with German `ein`. All four are in the clock and join rules that round 9 touches anyway.
- **From item 3, recorded and not fixed:**
  - German before Spanish `mil` is word salad.
  - "ocho coma three" states the number said.
  - "null point fünf Milligramm" is 0.5, which is right.
- **Also recorded:** a digit time with a colon ("a las 8:40") states its minutes in every language. The code before batch 24 does the same in English.

## Round 9 review: SUPERVISOR: CHANGES
1. **High, plausible: after `las`, an English number lost its first word to the hour rule, and the rest added up to a new number.**
   - "Me tomo las two hundred fifty milligram tablets de Pregabalin." stated 150, and Pregabalin 150 mg reached `match`.
   - "Tomo Cardizem LA, las four hundred twenty milligram capsules de diltiazem." stated 120.
   - The English plural "LAs" lowercases to `las`, so "I take two Cardizem LAs four hundred twenty milligrams each of diltiazem." also stated 120, in English-only text.
2. **Minor: an article joined a number of 100 or more before it.** "zweihundert Ein-Gramm-Tabletten" stated 201, "two hundred un miligramos" 201 and "one thousand un gramo" 1001. On these two the CEO's reference already closed the English run, and Muse's code didn't.

**Backlog (161d411 does the same):** the catalogue route for amount labels keeps a salt that contradicts the one said.

**Held:** no mixed runs for plain numbers, multipliers, halves and points (about 78,000 random mixed phrases); `la` and `las` for Spanish words and digits; digit hours; minutes; `y`; and every earlier fix. English and Arabic matched 161d411 on 100,000 phrases, apart from phrases with `las` (#1) or `un`/`una` (#2).

**CEO's triage:**
- **Finding 1 comes from the CEO's own round 8 SPEC,** which let English number words be an hour after `las` to catch "a las eight y cuarenta". Round 10 removes that.
  - After `las`, only a Spanish number word or digits make an hour.
  - The round 8 contract's word-salad pin "a las eight y cuarenta y dos pastillas" is removed.
  - This was picked over the supervisor's lookahead, which would still have suppressed English words after "LAs", because it leaves English text untouched. The one exception is digits after "LAs" with no unit, which fail closed.
- **Finding 2:** round 6's "an article joins no number" now covers numbers of every size. Only Spanish `y` joins an article.

## Round 10 review: SUPERVISOR: APPROVE
Three minors, none on a plausible input. All are recorded in `review.md` for after the freeze.
1. **An English decimal with Spanish digits:** an English number, an English `point` and Spanish digit words read as one decimal. "Tomo indapamida, at one point cinco miligramos." states 1.5.
2. **German and Spanish in one number:** "hundert veinticinco microgramos" states 125, and "acht y medio comprimido" 8.5. This is the family of the recorded "um sieben mil quinientos".
3. **An English hour inside Spanish clock syntax:** "a las eight y cinco mil miligramos". It follows from round 10's design, and the same sentence with a Spanish or digit hour states only 1000.

**Held:**
- Both round 10 rules, on 20,000 generated LA/LAs/las phrases.
- English and Arabic, unchanged from 161d411 on 40,000 random inputs.
- Every earlier fix.
- A 90,000-input concatenation fuzz found no new family.
