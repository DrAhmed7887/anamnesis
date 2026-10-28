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
