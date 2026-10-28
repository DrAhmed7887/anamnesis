# Batch 23: supervisor review

## Round 1 (Opus 5.5, high effort, 28 Oct). Builder: Muse Code (`muse-spark-1.3`)

SUPERVISOR: CHANGES

1. **major: `anamnesis/providers/spark.py:16`. The volume rule doesn't read the Arabic decimal sign `٫`, so it keeps the fivefold error that part 4 exists to remove.**
   - **Inputs:** `"Drops ٢٫٥ مجم/٥ مل"` and `"Drops 2٫5 mg/5 ml"`, each with amount 2.5 and per=ml. Both **KEPT [2.5]**.
   - **Why:** `stated_amounts` reads `٫` as a dot (SPEC §2 Digits), so the printed-amount check passes. `_PER_VOLUME_RE` only allows `[.,]`, so its match starts at the `5` and gets 5, which isn't in the amounts.
   - **Fix:** `_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫", "01234567890123456789.")`. Tried in the after copy: both inputs become NULL, and 1191 still pass. Add both inputs to the contract.
2. **major (a SPEC/brief gap, not Muse's fault): §2 "A volume other than 1 ml" and `spark.py:20`. The rule only catches "amount, then `/`/per/in, then volume", so common syrup wordings keep a strength printed per 5 ml.**
   - **Kept as 250 per ml:** "Each 5 ml contains paracetamol 250 mg"; "كل ٥ مل تحتوي على باراسيتامول ٢٥٠ مجم"; "باراسيتامول ٢٥٠ مجم لكل ٥ مل"; "250 mg in each 5 ml"; "250 mg per teaspoonful (5 ml)".
   - **Lesser misses:** "250mg/5cc", the unit-less "Amoxil 250/5 ml", "100000 IU/5 ml", and the slashes `∕` (U+2215) and `／` (U+FF0F).
   - **Fix (CEO edits the SPEC, then the contract):**
     - add `لكل` as a connector;
     - let `each|كل` sit between the connector and the volume;
     - add a volume-first pattern, `(?:each|every|كل)\s+N\s*(?:ml|مل)` with N ≠ 1 anywhere → null, which fails closed;
     - decide on `cc`, IU/units and the Unicode slashes.
3. **major (design): `anamnesis/agent/loop.py:130–131`. The third concept costs one more call per pack-less photo out of the fixed `max_provider_calls=12`, so on a multi-photo intake a pack that matched before is never examined.**
   - **Input:** a voice note plus 4 photos. In photos 1–3 only `package` finds a region; in photo 4 `medicine box` finds Concor.
   - **Base:** 10 calls, and Concor is `match`.
   - **After:** 12 calls, and `budget_exhausted` at photo 3's `package` call. Photo 4 is never segmented, so Concor (c1) becomes `missing_modality`, which can be requested as "not photographed" although the patient sent it.
   - **After, with `partial` readings:** both reads stay unzoomed and become `unreadable_source`.
   - **Still holds:** nothing flips to `match`, and the brief says the budget ran out.
   - **Fix (a CEO decision):** raise the default budget to cover, per photo, 3 segment calls, the `top_k` reads and the zooms; or record the trade-off in SPEC §4 Budget. Pin either with a contract test.
4. **minor: `anamnesis/review.py:91`. Muse's gap is real.**
   - **The conflict:** SPEC §8 line 258 pins `add_photo(concepts=("medicine box", "label"))`, but line 260 sends the new photo through "§4 steps 0 and 3–5", and step 3 now has three concepts.
   - **Why it matters:** the re-photo for an `unreadable` request is exactly the phone-photo case `package` was added for. On an empty re-photo, `add_photo` asks only `['medicine box', 'label']`.
   - **Fix:** default to three concepts and update §8 line 258. Tried: 1191 pass. Muse was right not to change it against the SPEC.
5. **minor: `spark.py:21`. The volume unit `مل` matches the start of `ملجم`, so an Arabic combination tablet loses its strength.**
   - **Input:** "Augmentin ٨٧٥ ملجم/١٢٥ ملجم أقراص" (875 and 125, a tablet) gives **NULL**. The `مجم` spelling and "875 mg/125 mg" are KEPT. It fails closed, but every Arabic `ملجم/ملجم` combination tablet loses coverage.
   - **Fix:** `(?:ml|مل)(?!جم|غ)`. Tried: KEPT, and 1191 pass.
6. **minor (a test that proves nothing): `review.py:132–134`.**
   - **The gap:** SPEC §4 says "the steps add up to `spend_usd`, also after `add_photo`", but no test checks it.
   - **Mutant:** with Muse's change reverted, so `add_photo` drops the step fields, the suite still gives 1191 passed. With Muse's change, b20 `first_intake` plus `answer()` adds up (0.008 = 0.008).
   - **Fix:** a contract test that sums `step.cost_usd` after `answer()` and compares it with `spend_usd`.

**What I ran, all offline in the scratch copies:**
- **The step costs add up to `spend_usd` on every path tried:** success; a retry after a traced `ProviderError`; a retry after a `billable_uncertain` estimate; two traced and two untraced failures; a traced failure, then `SpendCapExceeded`; a traced failure, then `ValueError`; a bare `ValueError`; the cap refusing the success trace; `budget_exhausted` at 0 calls; and `add_photo`. Without an `attempt_trace` the row shows "—" for the model with a non-zero cost, as SPEC says.
- **Escaping:** hostile target, outcome and model_id values (`</details><script>`, `<img onerror>`, `</td></table><a href="#…">`) are all escaped.
- **Page shape:** exactly 8 sections, one collapsed `<details>`, no `#` link without a target, and `_SCRIPT` unchanged. A pre-23 step loads with the defaults.
- **Contributor ids:** every model id from outside reaches a guard (the two readers, the extractor, `ProviderTrace`). `AgentStep` refuses it too. The voice and SAM constructors take no model argument.
- **`normalise`:** `catalogue.yaml` has no `۰–۹`, so no lookup changes.
- **`package`:** it runs only when the first two concepts return nothing or fail, so it can't add a second set of regions to a photo.
- **Claims:** the volume rule never touches one. `parse_label_json` is called only by the readers and the fixtures.
- **Not reviewed:** `tests/contract/test_b23_round2.py` (an untracked CEO draft) and commits `155dcc6` and `7261a49` (scripts only) appeared while I worked. `anamnesis/` and `tests/unit/` still matched the after copy.

## Round 2 (28 Oct)

SUPERVISOR: CHANGES

Muse's round 2 code does what the round 2 brief and the SPEC ask, and the round 1 inputs now come out right. Two changes are still needed before the merge, both on the CEO's side. The 1269 count reproduces in the after-r2 copy.

1. **major: `scripts/intake_live.py:41, :83, :92`. Round 1 #3 is fixed only for the default budget.** The live intake passes `MAX_CALLS = 12` as `max_provider_calls`, and again as `SessionGuard(max_calls=12)`.
   - **Ran:** the four-photo case with `max_provider_calls=12`. It stops at `budget_exhausted` on photo 3's segment step, and Concor becomes `missing_modality`.
   - **With the default:** 16 calls, and Concor is `match`. With `partial` readings: 19 calls, still `match`.
   - **Fix:** pass the default, and give `SessionGuard` the same formula or a high call cap. `scripts/zoom_live.py` (10 calls, one photo, no audio, needs 9) is fine.
2. **major (a SPEC §2 gap): the volume-first form allows no spoon word or bracket, and no Spanish or French.** All of these kept 250 per ml:
   - "Each teaspoonful (5 ml) contains 250 mg"; "كل ملعقة (٥ مل) تحتوي على ٢٥٠ مجم"; "Each spoonful of 5 ml contains 250 mg";
   - Spanish, which matters most here because the patients are in Spain: "Cada 5 ml contiene 250 mg de amoxicilina" and "Amoxicilina 250 mg por 5 ml";
   - French: "Chaque 5 ml contient 250 mg" and "250 mg par 5 ml";
   - "250 mg per 5-mL teaspoon" and "250 mg in 5 millilitres".

   Muse's bracket gap ("250 mg per (5 ml)", "250 mg/(5 ml)") is rare alone, but the same gap in the volume-first form is common.
   - **Fix:** an optional `(` after the connector, and an optional spoon word with an optional `of` and `(`, in both forms; `cada` and `chaque`, `por` and `par`; and `-` and `millilit(re|er)s?`.
3. **minor (SPEC §2): the new forms drop correct strengths on packs that aren't syrups.** These all fail closed, but cost coverage:
   - dissolving lines through `in`/`في`: "Aspirin 300 mg. Dissolve 300 mg in 100 ml of water"; "فيتامين سي ١٠٠٠ مجم في ٢٠٠ مل ماء"; "Movicol sachet 13.8 g in 125 ml of water";
   - pack-size lines through volume-first `each`/`every`: "Paracetamol 50 mg/ml, each 5 ml bottle"; "Insulin glargine 100 units/ml, each 3 ml pen contains 300 units"; "Insulin 100 IU/ml. Each 3 ml cartridge";
   - and "Every 5 mL use the measuring cup; Concor 5 mg tablets" drops a tablet's 5 mg.

   The SPEC's own "Kept" examples still pass.
   - **Fix:** skip `in`/`في` when water follows within a few words. For volume-first, skip a container word, or require a contains word.
4. **minor (SPEC §4 Budget): the default budget grows with the number of photos, with no limit.**
   - **Ran:** 10 package-only photos with partial readings.
     - At the fixed 12: 12 calls, $0.030.
     - At the new default: 52 calls, $0.157.
     - Under `SessionGuard(max_usd=0.05)`: it stops after 20 calls with `SessionCapExceeded`, at $0.0485, and the steps still add up.
   - **Fix:** cap the photos, or make the SPEC say every live caller wraps the providers in a `SessionGuard`.

**Rerun on after-r2:** round 1 #1 (the Arabic decimal sign), #2 (all its forms), #4 (`add_photo`'s three concepts), #5 (the `ملجم` tablet, kept) and #6 (the step sum after `add_photo`) are all fixed. #3 is fixed with the default budget, but not live (see #1). The 10 session paths still add up. The page is still 8 sections, one collapsed `<details>` and no dangling `#` link. Every input kept in round 1 is still kept. The regexes follow the round 2 brief item by item. Muse made the bracket after a spoon word optional, which is the safe side. `add_photo`'s default budget, `len(concepts) + 2*top_k`, covers every call one photo can make.

## Round 3 (28 Oct)

SUPERVISOR: CHANGES

Round 3 fixes every round 2 input except an OCR'd "5 mI", and Muse's code follows the SPEC text it was given. But the SPEC's volume-first wording still keeps the fivefold error on the commonest suspension wording, so #1–#3 are needed before the merge.

1. **major: the three-word window and the contains-word list miss standard carton wordings.** All of these kept 250 per ml:
   - "Each 5 ml of reconstituted suspension contains amoxicillin 250 mg", the amoxicillin and co-amoxiclav standard;
   - "Each 5 ml of the suspension contains 250 mg";
   - Spanish: «Cada 5 ml de suspensión contienen…», «Cada 5 ml contienen 250 mg» and «… suspensión reconstituida contiene…»;
   - Arabic: «كل ٥ مل تحتوى…» and «يحتوى» (the usual Egyptian spelling), «كل ٥ مل من المعلق بعد التحضير تحتوي…» and «كل ٥ مل بها…»;
   - "Each 5 ml provides 250 mg" and "Each 5 ml containing 250 mg".
2. **major: volume-first needs a starter word, so a bare volume with a contains word, or one after `per`, is kept.** Examples: "5 ml contains…", "Composition: 5 ml suspension contains…", "Per 5 ml: …", "Per 5 ml\n…", "One teaspoonful (5 ml) contains…", "A 5 ml spoonful contains…", and "Chaque cuillère-mesure de 5 ml contient…".
3. **major: the container exemption keeps a container's total read per ml.**
   - "each 2 ml ampoule contains 40 mg", read as 40 per ml, a 2× error;
   - "each 3 ml pen contains 300 units", read as 300 per ml;
   - "Each 5 ml bottle: 250 mg";
   - "Each 5 ml cup contains 250 mg", where the cup is the measuring cup.

   "Insulin 100 units/ml. Each 3 ml pen contains 300 units", read as 100 per ml, is still kept.
4. **minor: the water skip crosses line breaks and matches composition water.** Kept at 120 per ml: "… in 5 ml\nPurified water q.s.", «… في ٥ مل ماء مقطر» and "… in 5 ml water-based syrup".
5. **minor, but fix before the merge: plain `spoon`.** The CEO's uncommitted SPEC edit lists it; the code doesn't; and a unit test pins "250 mg per spoon (5 ml)" as kept.
6. **minor: `scripts/intake_live.py:85–86`.** `SessionGuard(max_calls=calls)` counts every charged attempt, retries included, so retries end a live intake early: 8 loop calls of 11. Fix: `max_calls=2 * calls`.
7. **minor (fails closed, coverage only): correct tablet and dissolving strengths still dropped.** Examples: "… in 200 ml of lukewarm drinking water" (water is the fourth word), "… (a glass) of water", "1000 mg per 200 ml of water", "Each 5 ml = 1 teaspoon. Concor 5 mg tablets", and "Every 10 ml of water: dissolve one tablet. Panadol 500 mg".

**Checked and fine:**
- every round 2 drop and keep case;
- the timeline `<tfoot>` cell has `colspan="9"`;
- the step sums, including `add_photo`;
- the four-photo budget case (16 calls, Concor `match`);
- the live script's loop budget.

**The CEO's response, round 4:**
- **#6:** fixed directly in `intake_live.py` (447a85c).
- **#1–#5 and #7:** handled by replacing the round 1–3 wording patterns with one clause rule (SPEC §2). It asks whether a clause that isn't about water prints a dose volume at all, so no list of starters, connectors, spoons or contains words is needed.

## Round 4 (28 Oct)

SUPERVISOR: CHANGES

The clause rule is a real improvement: every syrup wording from rounds 1–3 is now dropped. Two of its exemptions still keep the fivefold error on common syrup labels: the water clause, on powder-for-suspension cartons, and a spoon dose printed without a volume. Both are SPEC §2 design gaps; Muse's code implements the SPEC as written. Only `anamnesis/providers/spark.py` changed since round 3, and pytest gives 1469 passed.

1. **major: a water word anywhere in a clause exempts every volume in it, including the strength's own `/5 ml`.** Powders reconstituted with water are the commonest syrups in Egypt. All kept at 250 per ml:
   - "Amoxicillin 250 mg/5 ml when reconstituted with water";
   - "Powder for oral suspension 250 mg/5 ml (add 60 ml water)";
   - "Reconstitute with 60 ml of water to give 250 mg/5 ml";
   - «مسحوق لتحضير معلق ٢٥٠ مجم/٥ مل بعد إضافة ماء»;
   - "Cada 5 ml contienen 250 mg (reconstituir con agua)";
   - "Paracetamol 250 mg/5 ml in water" and "Water-free suspension 250 mg/5 ml".
2. **major: a spoon or measure dose printed without a number in ml never counts as a volume.** All kept at 125 per ml or per dose: "Each teaspoonful contains paracetamol 125 mg", «كل ملعقة صغيرة تحتوي على ١٢٥ مجم», "Cada cucharadita contiene 125 mg", "125 mg per teaspoon" and "125 mg per measure".
3. **minor: another product's or an excipient's per-ml line rescues a wrong strength**, because the per-1-ml print is searched by value across the whole text. Kept: "Paracetamol 250 mg / 5 ml. Paracetamol 250 mg/ml drops also available" (read as 250 per ml), "Paracetamol 120 mg/5 ml. Sorbitol 120 mg/ml" and "Ibuprofen 100 mg/5 ml, Ibuprofen 100 mg/ml? 40 mg/ml drops". The whole-text search itself is right: "50 mg/ml, each 5 ml bottle" needs it.
4. **minor: a line break between the amount and its volume, plus a tablet word elsewhere, keeps a per-tablet reading of a syrup.** Kept: "Paracetamol 250 mg\nper 5 ml\nAlso available as 500 mg tablets" and "Paracetamol 250 mg\n/5 ml\nNot for tablets use".
5. **minor (fails closed): Arabic forms with the article or a suffix are missed**, so Arabic effervescent and capsule packs lose correct strengths. Null: "بانادول ٥٠٠ مجم ٢٤ قرصاً. يذاب في ٢٠٠ مل من الماء", "فوار ١٠٠٠ مجم، يذاب القرص في ٢٠٠ مل من الماء" and "أوميبرازول ٢٠ مجم كبسولة، عبوة ١٤ كبسولة، الجرعة ١٠ مل".
6. **minor (fails closed): correct per-ml and per-dose strengths are dropped.** Null: "Lantus 100 U/ml, 3 ml pen", "Insulina glargina 100 unidades/ml, pluma de 3 ml", "Salbutamol inhaler 100 mcg per dose, 200 doses, 10 ml canister", "Nasonex 50 mcg/dose nasal spray, 18 ml" and "Each ml contains 50 mg. 15 ml bottle".
7. **minor (fails closed): the cut at the `.` of an abbreviation separates a volume from its water word.** Null: "Movicol: dissolve one sachet in 125 ml (approx. a quarter glass) of water. 13.8 g".

**Checked and fine:** every round 1–3 drop and keep; decimals, `q.s.`, `e.g.`, `÷`, U+2028 and `。` still drop a 250 mg/5 ml syrup; a `per: null` strength; the step sums, including `add_photo`; the live guard `max_calls=2 * calls`.

**The CEO's response, round 5:** every round has closed one list of wordings and opened the next, because each exemption was a place to hide a volume. Round 5 drops the clauses and turns the question around (SPEC §2). When a volume or spoon counts, the strength is kept only if each amount is printed in the reading's own unit: `250 mg/ml`, `100 mcg per dose`, or `5 mg tablets`. A missing wording now loses a strength; it can't keep a wrong one.
- **#1:** water to dissolve in is now a property of one volume. The water word must follow it, with only `of`/`de`/`من` and a few adjectives between. It is never water for a reading per ml, or when the volume follows an amount through `/` or `per`.
- **#2:** spoons and measures count as volumes.
- **#3:** a rescue is refused when the same amount is also printed over a volume.
- **#4 and #7:** with no clauses, nothing is cut. A tablet print must sit within three words of the amount, with no sentence or line break between them.
- **#5 and #6:** `ال` and the Arabic suffixes, `U`, `unidades`, `unités`, `وحدة دولية`, and a per-dose print.
- **Two earlier keeps move to the drops, on purpose (they fail closed):** "1000 mg per 200 ml of water" (round 4), and "Panadol 500 mg\n24 tablets, 100 ml bottle" (round 1), where a line break comes between the amount and the tablet word.

## Round 5 (28 Oct)

SUPERVISOR: CHANGES

Round 5 drops every harmful keep from rounds 1–4, and Muse's `spark.py` matches the SPEC text. One gap remains in the refusal, and it keeps the fivefold error. Only `spark.py` changed since round 4; pytest gives 1628 passed.

1. **major: the refusal misses the strength in two ways, so a same-amount print in the reading's own unit elsewhere rescues a wrong reading.**
   - The sentence ends at any `.`, including those of abbreviations (`B.P.`, `Ph.Eur.`, `USP.`, `approx.`), so the amount after its volume falls outside the window.
   - The before form allows nothing between the connector and the volume, so `in each 5 ml` isn't caught.
   - **Kept:**
     - "Each 5 ml contains Paracetamol B.P. 250 mg. Also as 250 mg/ml drops", read as 250 per ml;
     - "… Ph.Eur. 250 mg\nParacetamol 250 mg/ml drops also available";
     - the `B.P.` and `USP.` lines with "250 mg tablets also available", read per tablet;
     - "Each 5 ml contains approx. 250 mg. 250 mg/ml drops";
     - "Paracetamol 250 mg in each 5 ml. …", "250 mg base/5 ml. …" and "250 milligrams per 5 ml. …".
   - These are SPEC's own dropped example with `B.P.` added, the way Egyptian composition lines print it.
   - **Fix:** a `.` ends the sentence only before a space and a capital or Arabic letter, or at the end of the text. Allow `each`/`every`/`cada`/`chaque`/`كل` after the connector.
2. **minor: a dosing line or another product's line satisfies the own-unit print.** Kept:
   - "Paracetamol 120 mg/5 ml. Children 6-12 years: 250 mg per dose", read as 250 per dose;
   - "… Equivalent to half a 250 mg tablet", read as 250 per tablet;
   - "Paracetamol 250 mg oral suspension, not tablets. Shake. 5 ml", read per tablet.

   **Fix:** a reading per dose, tablet or capsule is dropped whenever an amount is printed right before a counting volume through `/` or `per`.
3. **minor: no volume found, so nothing counts.** "Cada 5 mililitros contienen 250 mg" and "Each 5 cm3 contains 250 mg" are kept. **Fix:** add `mililitros`, `cm3` and `cm³`.
4. **minor: brackets after a water word exempt everything inside them.** "Reconstitute with water (each 5 ml then contains 250 mg)", read per dose, is kept. **Fix:** exempt only a bracket holding just a volume, optionally with `approx.`.
5. **minor: the CEO's four known losses, rated.**
   - The own per-ml print counted by the refusal is the commonest. It also nulls "Each 10 ml bottle contains 50 mg/ml" and "Each 15 ml dropper bottle contains 40 mg/ml".
   - The bracket that closes after the volume hits effervescents and sachets.
   - Symbicort and `F.C.` are low impact.
   - "Ventolin Evohaler 100 micrograms per actuation, 200 doses, 18 ml" is null, because `micrograms` isn't a unit.
6. **minor (code nits):**
   - `\s*-` refuses "water - shake well", but SPEC means the hyphen of `water-based`;
   - Arabic `مل` has no end check, so `لكل ملعقة` reads as a per-1-ml print (the refusal catches it today);
   - Muse's `(?:ال)?` grouping fix is right, and no other grouping error was found in 25 patterns.

**Checked and fine:**
- About 230 labels from rounds 1–4. All 34 round 4 harmful keeps are now null, and all round 4 over-drops are now kept.
- Seven earlier keeps now drop, including the drop-bottle lines above.
- The step sums; nothing outside `spark.py` changed.

**The CEO's response, round 6:**
- **#1 and #2:** taken as proposed. The before-form also takes up to three words between the amount and the connector (`250 mg base/5 ml`), so it doesn't depend on the sentence window.
- **#2's third input:** a comma now also blocks the tablet print.
- **#3, #4, `micrograms`, and the two nits:** taken.
- **#5, the own print:** for a reading per ml or per dose, the amount's own print in that unit no longer counts as printed beside the volume (`3 ml pen, 100 U/ml`). A tablet print still counts: it is matched by proximity, and excusing it would keep "Each 5 ml contains 250 mg, 500 mg tablets also available" read per tablet.
- **#5, the bracket:** a bracket that closes after the volume may come before the water lead-in.
- **Symbicort and `F.C.`:** recorded as coverage SPEC gives up.

## Round 6 (28 Oct)

SUPERVISOR: CHANGES

Round 6 closes every round 5 input. But the new sentence end still lets an abbreviation keep the fivefold error. Muse's code matches the SPEC line by line, and only `spark.py` changed since round 5; pytest gives 1741 passed.

1. **major: a `.` followed by a space and a capital ends the sentence, and that is how `Ph. Eur.`, `B. P.` and a pharmacopoeia mark before the INN are printed.**
   - **Kept:**
     - "Each 5 ml contains Amoxicillin Ph. Eur. 250 mg. Also 250 mg/ml drops", read as 250 per ml;
     - the same line with "Amoxil 250 mg capsules also available", read per capsule;
     - "… B.P. Paracetamol 250 mg. …" and "… Paracetamol B. P. 250 mg. …";
     - "Each 5 ml contains: Paracetamol Ph. Eur.\n250 mg\n250 mg/ml drops also available".
   - **Fix:** don't end a sentence at a `.` after a word of at most three letters.
2. **The CEO's known round 7 gaps, rated:**
   - **brackets in the before-form: major.** "Amoxicillin 250 mg (as trihydrate) per 5 ml. Amoxil 250 mg capsules", read per capsule, is kept. Apply the brackets to the always-counts form too.
   - **the Arabic dual: minor**, but unconditional, because no volume is found at all;
   - **the line break after a `.`:** fails closed, so it's fine.
3. **minor (fails closed, common packs): prefilled syringes and pens read per dose are null.** Examples: "Clexane 40 mg/0.4 ml prefilled syringe", "Humira 40 mg/0.4 ml pre-filled pen", "Fragmin 5000 IU/0.2 ml", "Metoject 10 mg/0.2 ml", and "Ozempic 0.25 mg dose, 1.34 mg/ml, 1.5 ml pen". **Fix:** for a reading per dose, exempt a volume when a single-dose container is named, and accept `amount unit dose` with no connector.
4. **minor (fails closed): a spelled-out Arabic milligram reads as ml.** «كونكور ٥ مللي جرام ٣٠ قرص», «… ملليجرام أقراص» and «أملور ١٠ ملي جرام أقراص» are null. **Fix:** exclude `مل` before these forms, and add them and `ميكروجرام` to the units.
5. **minor (fails closed):**
   - "Vitamin D3 1000 IU per drop, 10 ml", read per dose, is null. Add `drop`, `gota`, `goutte` and «نقطة» as dose words.
   - "Disperse each 500 mg tablet in 10 ml of milk or juice" is null. It's rare, so accept it.

**Checked and fine:**
- all round 5 inputs, 26 of them changed as intended;
- the round 5 over-drops are now kept: the drop bottles, Ventolin "micrograms", Fosfomycin, and «ماء -»;
- the own-print skip passes only self-contradicting labels;
- the lone-volume bracket after water;
- the per-volume rule for `/`, `per` and `لكل`;
- the step sums; nothing outside `spark.py` changed.

**The CEO's response, round 7:**
- **#1, #2, #4 and #5's drop words:** taken. The before-form now skips bracketed text entirely, so a longer salt name, "250 mg (as amoxicillin trihydrate)/5 ml", is caught as well. The always-counts form allows bracketed text between the amount and the connector.
- **The stricter sentence end of round 6:** a `.` before a line break doesn't end a sentence. Muse's reading was the stricter one, and it is now SPEC.
- **#3, not taken; recorded as coverage SPEC gives up.** An exemption keyed to `syringe` or `pen` would also cover a syrup's oral measuring syringe and multi-dose insulin and GLP-1 pens. Dropping these strengths fails closed: the brief asks for the pack.

## Round 7 (28 Oct)

SUPERVISOR: CHANGES

Round 7 closes every round 6 input, with no regressions across about 330 probe labels from rounds 1–7. One fail-open remains. It is the same class as the "another product's line" cases the contract already treats as realistic. If the CEO judged a same-amount sibling line unrealistic on a single pack photo, the batch would meet the merge bar. Only `spark.py` changed since round 6; pytest gives 1821 passed.

1. **major (fails open): a salt phrase of four or more words without brackets, between the amount and the connector, escapes the before-form.**
   - **Kept:**
     - "Amoxicillin 250 mg as amoxicillin trihydrate per 5 ml oral suspension. Amoxil 250 mg capsules also available", read per capsule;
     - the same line with `;`;
     - two Arabic forms with «على هيئة … لكل ٥ مل»;
     - "… as amoxicillin trihydrate BP per 5 ml. 250 mg/ml drops", read per ml.
   - **Fix:** raise the word limit from three to five, and stop those words at a sentence end. Otherwise the change would drop "Euthyrox 50 µg tablets; crush and suspend in 10 ml of liquid".
2. **minor (fails open, rare):** «معلقة», the colloquial Egyptian spelling of «ملعقة», isn't a spoon. «باراسيتامول ٢٥٠ مجم لكل معلقة» is kept for any `per`. The stem «معلق» alone means a suspension.
3. **minor (fails open, contrived):** a sentence end SPEC allows, followed by a same-amount line: a four-letter `Ph.Helv.`, "BP 2009.", and "paracetamol. Strength 250 mg." No change needed.
4. **minor (fails closed, recorded as given up): prefilled syringes and pens read per dose.** Accepted under the merge bar; the CEO's reason against a container exemption is sound.

**Checked and fine:**
- every round 6 input, now dropped or kept as intended;
- bracket and abbreviation variants: two groups, nested brackets, non-breaking spaces, blank lines;
- the Arabic volumes and spoon variants;
- the new units and dose words, which create no false own print a syrup could use;
- Muse's code against SPEC, including the one-group form, which is harmless;
- the step sums; nothing outside `spark.py` changed.

**The CEO's response, round 8:**
- **#1 and #2:** taken. The before-form takes up to five words, none of them across a sentence end, and the colloquial spoon spellings count as whole words.
- **#3:** no change, as the supervisor advises.
- **#4:** stays recorded as coverage given up.

## Round 8 (28 Oct)

SUPERVISOR: APPROVE

No realistic label keeps a wrong strength. The one remaining item is a correct tablet strength that now drops (#1). SPEC records only part of it, so either record the rest or take the two-line fix before merge; neither is a safety change. Only `spark.py` changed since round 7; pytest gives 1851 passed.

1. **minor (fails closed): a tablet line followed within five words by a dissolving or dispersing volume that names no water drops a correct per-tablet strength.** Kept in round 7, null in round 8:
   - "Vitamin C 1000 mg effervescent tablet, dissolve in 200 ml", and its Arabic form;
   - "Prednisolone 5 mg soluble tablets: dissolve in 10 ml", plain and "of juice";
   - "Zithromax 500 mg dispersible tablets disperse in 30 ml liquid";
   - "Euthyrox 50 µg tablets, crush and suspend in 10 ml";
   - "Omeprazole 20 mg capsules: open and mix in 15 ml of apple juice".

   Lines that name water still keep. **Fix, either:**
   - **(a)** record "a dissolving or dispersing line that names no water" in SPEC;
   - **(b)** have the before-form not refuse when the bracket-stripped gap holds a tablet or capsule word. Tried in a mutant: all the drops above keep, no harmful probe changes, and one constructed Muse unit case flips.
2. **minor (fails open, very rare):** the colloquial dual «معلقتين» isn't a spoon, consistent with SPEC's whole-word rule. No fix needed unless wanted.

**Checked and fine:**
- all 6 round 7 fail-opens are now null;
- about 360 probes from rounds 1–6 are unchanged, apart from #1;
- more salt and gap edges are all null: a six-word salt, "equivalent to … 287 mg per 5 ml", `Ph. Eur.`, `;` or `!` in the gap;
- `_gap_has_sentence_end` and the spoon pattern match SPEC;
- the step sums; nothing outside `spark.py` changed.

**The CEO's response, round 9:** (b) and #2 are taken. These are exactly the effervescent and soluble tablets a real medicine bag holds, and a syrup's salt phrase never contains a tablet word. Text in brackets is stripped first, so "250 mg (equivalent to half a tablet) per 5 ml" still refuses; a contract test pins it.

## Round 9 (28 Oct)

SUPERVISOR: APPROVE

Both of Muse's round 9 changes match SPEC, and no realistic label keeps a wrong strength. The tablet-word carve-out does open a narrow fail-open, but only on wordings the supervisor doesn't consider realistic for a syrup pack. Only `spark.py` changed since round 8, and it equals the supervisor's round 8 mutant (b) plus the dual; pytest gives 1890 passed.

1. **minor (fails open, unrealistic wordings): a tablet word outside brackets between a syrup's amount and its volume disables the refusal.** When that word also makes a tablet print, a per-tablet reading survives.
   - **Kept in round 9, null in round 8:**
     - "Paracetamol 250 mg = 1 tablet per 5 ml";
     - "Amoxicillin 250 mg capsules or suspension per 5 ml";
     - "Calpol 250 mg tab/5 ml";
     - «… ما يعادل قرص لكل ٥ مل»;
     - "… comprimido por 5 ml".
   - **Still null:** the same lines read per ml or per dose, and the bracketed tablet word.
   - **Optional hardening:** apply the carve-out only when the connector is `in` or `في`, as every dissolving line has it. Tried in a mutant: all but one of these become null, 1890 still pass, and all of round 8's dissolving keeps stay kept.

**Checked and fine:**
- the 7 dissolving and dispersing lines from round 8 are kept;
- the colloquial duals are null;
- about 380 earlier probes are unchanged;
- Muse's two changes match SPEC;
- the step sums; nothing outside `spark.py` changed.

**The CEO's response:** batch 23 merges on this APPROVE. The `in`/`في` hardening is the first item for the follow-up batch, together with whatever the Gemini 4 check of the merged batch finds. No label it would change is a wording printed on a syrup pack.
