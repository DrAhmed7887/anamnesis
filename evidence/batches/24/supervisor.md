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
