# Anamnesis contract (v3.7, 28 Oct 2026)

A pre-visit intake agent. It takes the patient's voice note (Voice Transcribe supports 25 languages; **tested live so far only on synthetic text-to-speech notes: English, and Egyptian Arabic text with brand names in Latin or Arabic script, spoken by a macOS voice; no human speech yet**) and photos of their medicine packs (tested live on rendered test packs and, from batch 21, public photos of real packs: Wikimedia Commons, DailyMed and Cairo University), and gives the clinician a one-page brief. Every fact in the brief links to the audio turn and the image region it came from. **It reports where sources disagree. It never gives medical advice.** The voice notes are synthetic so far; the photos of real packs are public, and Ahmed's own photos and voice, when recorded, follow `docs/DATA_HANDLING.md` (batch 23, QM M5 #2).

## 1. Evidence (independent IDs, no forced chain)
| Model | Fields | Rules |
|---|---|---|
| `AudioTurn` | `turn_id`, `start_ms`, `end_ms`, `transcript`, `speaker?`, `lang_hint?` | `end_ms > start_ms ≥ 0`. Turn-level timing only (Voice Transcribe has no word timestamps) |
| `ImageRegion` | `region_id`, `image_sha256`, `object_id`, `x1,y1,x2,y2`, `frame_w`, `frame_h`, `confidence?` | Source pixels, inclusive corners (SAM 3.1 format). `0 ≤ x1 ≤ x2 < frame_w`, same for y. `confidence` in [0,1]. Hash is 64 lowercase hex chars |

## 2. Medication facts
| Model | Fields | Rules |
|---|---|---|
| `IngredientAmount` | `inn`, `salt?`, `amount`, `unit` | `amount > 0` (Decimal). `unit` ∈ `mg, mcg, g, ml, iu`. `inn` holds the **active moiety**: a curated alias table splits salt names (`"Metoprolol succinate"` → `inn="metoprolol"`, `salt="succinate"`). Synonyms are handled the same way (acetaminophen → paracetamol). So are the French, Spanish, German and Latin forms that packs print for the catalogue's ingredients (batch 21, staged cases U2 and U8): `amoxicilline`, `amoxicilina`, `amoxicillinum`; `acide clavulanique`, `ácido clavulánico`, `Clavulansäure`, `acidum clavulanicum`; `paracétamol`, `paracetamolum`; `métoprolol`, `metoprololum`, `metoprololi succinas`, `Metoprololsuccinat`, `metoprololi tartras`, `Metoprololtartrat`; `bisoprololum`, `bisoprololi fumaras`, `Bisoprololfumarat`; `amlodipino`, `amlodipinum`, `amlodipini besilas`, `Amlodipinbesilat`; `metformina`, `metformine`, `metforminum`, `metformini hydrochloridum`, `Metforminhydrochlorid`; `atorvastatina`, `atorvastatine`, `atorvastatinum`, `atorvastatinum calcicum`; `caféine`, `cafeína`, `Coffein`, `coffeinum`. Each salt form gives the same moiety and salt as its English one. Keys match after Unicode NFC normalisation, so decomposed accents resolve too (supervisor 21 #7). An unknown suffix is never stripped |
| `Strength` | `ingredients: list[IngredientAmount]`, `per`, `release` | ≥1 ingredient (combinations: Augmentin 875/125) and **no duplicate canonical INNs**. `per` ∈ `tablet, capsule, ml, dose`. `release` ∈ `immediate, modified, unknown` (default `unknown`) |
| `DoseRegimen` | `units_per_intake?`, `intakes_per_day?`, `as_needed?` | Decimals > 0 when present (0.5 means half a tablet). `as_needed` defaults to `None`: unknown, not "no" |
| `PatientClaim` (from audio) | `claim_id`, `name_text`, `inn?`, `strength?`, `intake_amount?`, `regimen?`, `status`, `audio_evidence` | `audio_evidence` has ≥1 turn_id. `status` ∈ `active, discontinued, unknown`. `intake_amount` (what they take per intake) is kept separate from `strength` (what the tablet contains) |
| `PackObservation` (from image) | `observation_id`, `label_text?`, `inn?`, `strength?`, `readability`, `country?`, `visual_evidence` | `visual_evidence` has ≥1 region_id. `readability` ∈ `readable, partial, unreadable`. `readable` requires `label_text` |

`AudioTurn.transcript` and `speaker` are non-empty when present.

### Model replies (batch 16)
Every string a model writes is checked at the parser, before it can reach a report:
- **Numbers** arrive as strings. `"2.5"` and the decimal comma `"2,5"` both parse; a comma is a decimal mark only when 1–2 digits follow it (`"1,000"` is ambiguous and does not parse). A dot followed by exactly three digits with a non-zero whole part (`"1.000"`, `"2.500"`) is ambiguous the same way (a European thousands mark) and does not parse; `"0.125"` does. Ranges (`"1-2"`), words, zero and negatives don't parse. The Arabic decimal sign `٫` (U+066B) is read as a dot, under the same rules, and Arabic-Indic digits parse like ASCII ones (`"٢٫٥"` is 2.5, `"١٠٠"` is 100); the Arabic thousands sign `٬` doesn't parse (QM M4 code #3; batch 19.1). **Digits are exactly three sets:** ASCII `0–9`, Arabic-Indic `٠–٩` (U+0660–U+0669) and extended Arabic-Indic `۰–۹` (U+06F0–U+06F9), so `"۵"` is 5 and `"۲٫۵"` is 2.5. `catalogue.normalise` maps both Arabic-Indic sets to ASCII as well (batch 23, QM M5 #6). Any other digit (`"５"`, `"५"`) doesn't parse (QM M4 code round 2 #2; batch 21). **A single number word, the whole amount, parses as its value** (batch 22, live 28 Oct: Spark still sometimes writes "five"). So "five" is 5, «خمسة» 5, «خمسمية» 500 and «واحد» 1. Two or more words never parse ("five hundred", "eight seventy-five", «خمسة وعشرين»), and neither do zero, half, hundred and thousand words on their own. The word must be bare, letters only (tatweel allowed): with a sign, a comparator, punctuation or any tashkeel it never parses, so "<five" ("less than five") is not 5 and «خُمس» (a fifth) is not «خمس» (five) (batch 22 round 2, supervisor finding 1). The stated-amount check still applies.
- **An optional field that doesn't parse becomes null; it never fails the whole reply.** Optional fields: `regimen.units_per_intake`, `regimen.intakes_per_day`, `intake_amount` (null if its amount doesn't parse or it fails validation, e.g. an empty `inn`), `strength` (null if any of its ingredient amounts doesn't parse, or if it fails validation, e.g. an equivalence line read as two salts of one INN), and the label's `country`.
- **A dropped claim amount takes the other one with it.** When a claim's reply sent a `strength` or an `intake_amount` and either one is dropped, both become null, so the claim can't reach `match` on what is left (supervisor 16 #1: a combination whose caffeine amount didn't parse, or an intake range, would otherwise have matched). From batch 17, rule 8 also uses `regimen.units_per_intake`, so a sent `units_per_intake` that is dropped (`"1-2"`, `"half or one"`) nulls `strength` and `intake_amount` the same way.
- **`name_text`** must occur in the text of a turn the claim cites (both sides through `catalogue.normalise`, substring match, so `الPanadol` contains `Panadol`). Otherwise the reply is malformed (retryable), like an uncited turn.
- **`country`** is kept only as an ISO 3166-1 alpha-2 code (two letters, stored upper-case); anything else becomes null.
- **A label reply's strength carries no key beyond `LABEL_SCHEMA`'s**, like the claim parser's shape check: `ingredients`, `per`, `release`, and for each ingredient `inn`, `amount`, `unit`. Any other key, `salt` included, makes the reply malformed (retryable); a missing `release` still defaults to `unknown`. A pack's salts come only from the curated split of `inn`, so no model-written salt can reach the brief (supervisor 19.1 #1).
- **`assert_no_advice`** runs over `name_text`, the claim's `inn`, the label's `inn` and every ingredient `inn` (strength and intake). A hit makes the reply malformed (retryable). Its Arabic words (`يجب`, `خذ`, `تناول`, `توقف`, `ضاعف`, `ينصح`) also match with an attached clitic (`و`, `ف`, `ب`, `ل`, `ال`, `وال`, `بال`, `فال`, `لل`) and after diacritics and tatweel are removed as `normalise` removes them: `وتناول`, `فيجب`, `تَناوَل` (QM M4 code #7; batch 19.1). They stay whole words: `يتناول`, `المتناول`, `تناولت` and `أخذ` pass. `label_text` is exempt: it is quoted source text, and real packs print directions ("Take one tablet daily").

### Amounts must be stated (batch 20)
A number a model writes is kept only if the source states it. The workshop rule (a quote is refused unless it is on the page) applies to every amount, not just to `name_text`.
- **`stated_amounts(text) -> frozenset[Decimal]`** (`anamnesis/providers/stated.py`) is every positive number the text states:
  - **Digits.** The same three digit sets count as digits, and `٫` as a dot. Each run of digits, with at most one `.`, `,` or `٬` and more digits after it, and no digit, `.`, `,` or `٬` just before it, is read with `parse_amount_text`. A run never touches a digit of another set, and it is matched as a whole: `"１5"`, `"5５"` and `"1.5５"` state nothing, not 1 (supervisor 21 #6 and round 2 #3). So `"2,5"` is 2.5, `"100mg"` is 100, `"875 mg/125 mg"` is 875 and 125, and the ambiguous `"1,000"` or `"1.000"` states nothing. So do `"١٬٠٠٠"` and `"٢٬٥"`, since `٬` doesn't parse (they used to state 1, or 2 and 5), and `"۵ ملغ"` states 5 (batch 21).
  - **Number words** in English and Egyptian or Modern Standard Arabic, matched on the tokens of `catalogue.normalise(text)` (so `ة` is `ه` and `أ` is `ا`). A word with the Arabic `و` ("and") attached in front counts as the word.
    - English: `zero`–`nineteen` (zero states nothing on its own), `twenty`–`ninety` by tens, `hundred`, `thousand`, `half`.
    - Arabic: 1 `واحد واحده احد`; 2 `اتنين اثنين اثنان اتنان اثنا اثني`; 3 `تلاته ثلاثه تلات ثلاث`; 4 `اربعه اربع`; 5 `خمسه خمس`; 6 `سته ست`; 7 `سبعه سبع`; 8 `تمانيه ثمانيه تماني ثماني تمن ثمان`; 9 `تسعه تسع`; 10 `عشره عشر`; 11–19 `حداشر اتناشر تلتاشر اربعتاشر خمستاشر ستاشر سبعتاشر تمنتاشر تسعتاشر`; the tens 20–90 `عشرين عشرون`, `تلاتين ثلاثين ثلاثون`, `اربعين اربعون`, `خمسين خمسون`, `ستين ستون`, `سبعين سبعون`, `تمانين ثمانين ثمانون`, `تسعين تسعون`; 200 `ميتين مايتين مئتين مئتان مائتين مائتان`; 300–900 as one word, a stem (`تلت ثلاث`, `ربع اربع`, `خمس`, `ست`, `سبع`, `تمن ثمان`, `تسع`) followed by `ميه`, `مايه`, `مائه` or `مئه` (`خمسميه` is 500); 2000 `الفين`. Hundred `ميه مايه مائه مئه ميت`, thousand `الف الاف`, half `نص نصف`.
    - **A run** is consecutive number words, also joined by `and` or `و` (`a` is allowed only after `and`, as in "and a half"). **A run also ends at any of `, . ; : ! ? ، ؛ ؟` or a line break in the raw text** (a hyphen or a slash doesn't end it), so "five, two" states 5 and 2, never 7 (supervisor 20 #5); the digit pass is unaffected. Its value: start with total = current = 0; a plain number adds to current; hundred sets current to (current or 1) × 100; thousand adds (current or 1) × 1000 to total and resets current; half adds 0.5 to current. In English, `point` followed by digit words (`zero`–`nine`) adds them as decimals and ends the run. The run states total + current, and **each of its words also states its own value** (a hundred or thousand word states 100 or 1000, half 0.5).
    - So "five" is 5, "twenty-five" 25, "two hundred and fifty" 250, "two and a half" 2.5, "two point five" 2.5, "خمسة" 5, "خمسين" 50, "خمسه وعشرين" 25, "ميتين وخمسين" 250, "اتنين ونص" 2.5, "تلات ميه" 300 and "خمسمية" 500. "once" and "twice" state nothing.
    - **A second hundreds group starts a new number** (batch 21; round 2, supervisor 21 #1–3).
      - **The trigger:** a hundred word, or a one-word Arabic hundred (`ميتين`, `تلتمية` … `تسعمية`), that comes when the run's value since its last thousand is already 100 or more. It closes the earlier number.
      - **What moves:** only a final plain word worth 1–9, just before a hundred word, goes with the new number as its multiplier ("… one hundred", "… وتلات مية"). Nothing moves when the hundred word carries its own `و` ("ومية").
      - **Examples:**
        - "eight hundred seventy-five (and) one hundred twenty-five" states 875 and 125, never 876 or 87625;
        - "خمسمية وتلات مية" states 500 and 300, never 503;
        - "خمسمية وميتين" states 500 and 200, never 700;
        - "تمنمية خمسة وسبعين ومية خمسة وعشرين" states 875 and 125.
      - **Origin:** found while writing the staged case U2 (`evidence/batches/21/manifest.md`).
      - **Unchanged:** "two hundred and fifty", "twelve hundred", "one hundred one", "ألف وميتين" and "two thousand five hundred and fifty" each stay one number.
      - **Thousands and the filler "a"** (round 3, supervisor 21 round 2 #1–2):
        - A plain word worth 1000 or more («ألفين») closes the thousands part like a thousand word. So «ألفين وخمسمية» is 2500, «ألفين ومية» is 2100 (not 200000), and «ألفين وخمسمية وخمسين» is 2550, never 550.
        - After the filler `a` ("and a hundred"), nothing moves. So "eight hundred seventy-five and a hundred twenty-five" states 875 and 125, never 870 or 525.
- **Claims.** Each `strength` ingredient amount and the `intake_amount` amount must be in the union of `stated_amounts` over the turns the claim cites (only those). An amount that isn't stated is treated as one that doesn't parse: that field becomes null, and the existing rule then nulls the other one too. Live, 27 Oct: "Concor five milligrams" and "كونكور خمسة ملي جرام" both keep their 5 mg.
- **Labels.** Each label `strength` ingredient amount must be in `stated_amounts(label_text)`; otherwise the label's `strength` becomes null (no `label_text`, no strength). The reading itself is kept. A `label_text` that is neither a string nor null makes the reply malformed (retryable), as before batch 20: it never reaches `stated_amounts` (supervisor 20 #1).
- **A volume other than 1 ml** (batch 23). Rounds 1–3 listed wordings; round 4 cut the text into clauses; round 5 asked instead whether each amount is printed in the reading's own unit; round 6 closed the gaps the supervisor's round 5 review found in that rule; round 7 tightened three places where this SPEC's own wording was loose, and took the supervisor's round 6 findings; round 8 widened the before-form to five words and added the colloquial spoon; round 9 kept tablet strengths whose dissolving line names no water. Both Arabic-Indic digit sets and the Arabic decimal sign `٫` are read as ASCII first, and matching ignores case.
  - **A volume** is a number other than 1 (`5`, `2,5`), an optional `-`, and `ml`, `cc`, `cm3`, `cm³`, `millilitre(s)`, `milliliter(s)`, `mililitro(s)`, or `مل`, but not where it starts `ملجم`, `ملغ`, a spoon (`ملعق`) or a spelled-out milligram (`مللي جرام`, `ملي جرام`, `ملليجرام`). `ملي` alone counts, as Egyptian labels write it.
  - **A spoon counts as a volume too:**
    - `teaspoon`, `tablespoon`, `dessertspoon` and `spoon`, each with `ful` or a plural; `tsp`; `tbsp`;
    - `measure` after `per`, `each`, `every`, `a`, `one` or `1`;
    - the stem `ملعق` with any letters after it (`ملعقة`, the dual `ملعقتين`), and `ملاعق`, each with or without `ال`;
    - the colloquial Egyptian spelling `معلقة`, `معلقه`, the dual `معلقتين` or `معلقتان`, or `معالق`, as a whole word, with or without `ال`. The stem `معلق` alone means a suspension and isn't a spoon;
    - `cuchara`, `cucharada`, `cucharadita`, `cuillère`, `cuillerée` and `cuillère-mesure`, with their plurals.
  - **Water to dissolve in doesn't count, but only for a reading per `tablet`, `capsule` or `dose`.** It is either of these:
    - **a volume or spoon followed by a water word.** Text in brackets isn't counted, and a bracket that closes after the volume may come first (`a glass (200 ml) of water`). Only these may come between: an optional `of`, `de`, `d'`, `du` or `من`, then any of `warm`, `lukewarm`, `cold`, `cool`, `cooled`, `boiled`, `drinking`, `tap`, `fresh`, `clean` and `plain`;
    - **a volume alone in brackets right after a water word,** optionally after `approx`, `aprox`, `about`, `ca`, `env`, `environ` or `حوالي` (`a glass of water (200 ml)`, `water (approx. 200 ml)`).
  - **The water words** are `water`, `agua`, `eau`, and `ماء` with or without `ال`. They aren't water words when followed by:
    - a hyphen joined to a word (`water-based`; a dash with spaces around it doesn't count);
    - `for injection`;
    - `purificada`, `destilada`, `estéril`, `purifiée`, `distillée` or `stérile`;
    - `مقطر`, `معقم` or `للحقن`.
  - **A volume or spoon right after an amount always counts, water or not.** That is a number, its unit if any, any text in brackets (`250 mg (as trihydrate) per 5 ml`), one of `/`, `∕`, `／`, `per`, `por`, `par` or `لكل`, an optional `(`, then the volume or spoon: `250 mg/5 ml when reconstituted with water`. For a reading per `tablet`, `capsule` or `dose`, such a volume nulls the strength outright. The pack prints a strength per volume, so a dosing line or another product's line can't stand in for the reading's own print (`120 mg/5 ml. Children: 250 mg per dose`).
  - **The strength becomes null** when a volume or spoon counts, unless both of these hold:
    - each ingredient's amount is printed in the reading's own unit;
    - no amount of the reading is also printed beside a volume or spoon. That means either of these:
      - **right before it:** the amount, at most five words not counting text in brackets (its unit, `base`, `as amoxicillin trihydrate BP`; `(as amoxicillin trihydrate)` isn't counted) with no sentence end among them (as defined in the next bullet), and with no tablet or capsule word among them, because then the volume is for dissolving (`1000 mg effervescent tablet, dissolve in 200 ml`), one of the connectors above or `in` or `في`, an optional `each`, `every`, `cada`, `chaque` or `كل`, an optional `(`, then the volume or spoon (`250 mg / 5 ml`, `250 mg base in each 5 ml`; but not `Euthyrox 50 µg tablets; crush and suspend in 10 ml`);
      - **later in its sentence.** A sentence ends at `;`, `!`, `?` or `؛`; at a `.` followed by spaces (not a line break) and a capital, accented or Arabic letter, unless the `.` comes right after a word of one to three Latin letters; and at the end of the text. So `B.P. 250 mg`, `Ph. Eur. 250 mg`, `B. P. Paracetamol 250 mg` and `approx. 250 mg` stay in the sentence, and so does the next line. For a reading per `ml` or `dose`, the amount's own print in that unit doesn't count here (`3 ml pen, 100 U/ml`). A tablet or capsule print still counts, because it is matched by proximity (`Each 5 ml contains 250 mg, 500 mg tablets`).
  - **The reading's own unit:**
    - **per `ml`:** the amount, its unit if any, a connector or `in` or `في`, an optional `1`, then `ml`, `millilitre`, `milliliter`, `mililitro` or `مل` (with the same rule as in a volume) (`50 mg/ml`, `100 U/ml`);
    - **per `dose`:**
      - per 1 ml as above; or
      - the amount, its unit if any, a connector, an optional `1` or `metered`, then `dose`, `dosis`, `actuation`, `spray`, `puff`, `inhalation`, `pulverización`, `pulvérisation`, `drop`, `gota`, `goutte`, `بخة`, `جرعة` or `نقطة` (`100 mcg per dose`, `1000 IU per drop`);
    - **per `tablet` or `capsule`:** the amount and its unit, then at most three words, then a tablet or capsule word, with no `.`, `,`, `،`, `;`, `!`, `?`, `؛` or line break between them (`5 mg tablets`, `500 mg 24 tablets`, `٢٠ مجم كبسولة`).
  - **The units:** `mg`, `mcg`, `µg`, `μg`, `g`, `IU`, `UI`, `U`, `unit(s)`, `unidades`, `unités`, `milligram(s)`, `microgram(s)`, `gram(s)`, `miligramo(s)`, `microgramo(s)`, `gramo(s)`, `milligramme(s)`, `microgramme(s)`, `gramme(s)`, `مللي جرام`, `ملي جرام`, `ملليجرام`, `ميكروجرام`, `جرام` (the two-word forms with or without the space), `مجم`, `ملجم`, `ملغ`, `مغ`, `جم`, `غ`, `وحدة` and `وحدة دولية`.
  - **The tablet and capsule words:**
    - `tablet`, `tab`, `capsule`, `caps`, `comprimido`, `cápsula`, `comprimé` and `gélule`, with their plurals;
    - `قرص`, `أقراص`, `اقراص` and `كبسول`, with or without `ال` and with any suffix.
  - **Why:** the schema can't say "per 5 ml". The readers wrote per ml, per dose or per tablet; live on 28 Oct, Spark 1.3 and Spark Open both read a 250 mg/5 ml syrup as 250 mg per ml, a fivefold error. Every round that listed wordings, or the places where a volume doesn't count, missed some. A print in the reading's own unit is what makes a reading trustworthy, so a missing wording now loses a strength rather than keeping a wrong one. The reading itself is kept.
  - **Dropped, for example:**
    - `Each 5 ml of reconstituted suspension contains 250 mg`;
    - `Amoxicillin 250 mg/5 ml when reconstituted with water`;
    - `Each 5 ml reconstituted with water contains 250 mg`;
    - `Cada 5 ml contienen 250 mg (reconstituir con agua)` and `Reconstitute with water (5 ml contains 250 mg)`;
    - `Each teaspoonful contains 125 mg` and `كل ملعقة صغيرة تحتوي على ١٢٥ مجم`;
    - a per-ml line of another product, read as 250 per ml: `250 mg / 5 ml. 250 mg/ml drops also available`, `Each 5 ml contains 250 mg. 250 mg/ml drops also available` and `Each 5 ml contains Paracetamol B.P. 250 mg. Also as 250 mg/ml drops`;
    - a dosing line on a syrup, read as 250 per dose: `120 mg/5 ml. Children 6-12 years: 250 mg per dose`;
    - `Each 5 ml contains 250 mg. Tablets also available`, read per tablet;
    - a container's total read per ml: `each 2 ml ampoule contains 40 mg`;
    - a reading per ml beside a dissolving line: `120 mg in 5 ml of water`.
  - **Kept, for example:**
    - **printed per 1 ml or per dose:**
      - `50 mg/ml, each 5 ml bottle`;
      - `Lantus 100 U/ml, 3 ml pen` and `Lantus SoloStar 3 ml pen, 100 U/ml`;
      - `Each 2 ml ampoule contains 40 mg (20 mg/ml)`, read as 20 per ml;
      - `100 mcg per dose, 200 doses, 10 ml canister`;
    - **printed per tablet or capsule:** `Ibuprofen 100 mg tablets, 100 ml` and `أوميبرازول ٢٠ مجم كبسولة، الجرعة ١٠ مل`;
    - **water to dissolve in:**
      - `Dissolve 500 mg in 200 ml (a glass) of water`;
      - `200 ml of lukewarm drinking water`;
      - `يذاب في ٢٠٠ مل من الماء`;
      - `Dissolve one tablet in a glass of water (200 ml)` and `… in a glass (200 ml) of water`;
    - **no volume:** `٨٧٥ ملجم/١٢٥ ملجم`.
  - **Coverage it gives up, on purpose:**
    - an amount printed only after its volume or unit word, beside a pack volume: `Each ml contains 50 mg. 15 ml bottle`, `Each tablet contains 5 mg. 5 ml spoon`;
    - a line break, a comma or an abbreviation's `.` between the amount and the tablet word, beside a pack volume: `Panadol 500 mg\n24 tablets, 100 ml bottle`, `5 mg 30 F.C. Tablets`;
    - **two products on one label:**
      - when the reading is per tablet, capsule or dose and the other product's strength is printed per volume: `Brufen 400 mg tablets. Brufen syrup 100 mg/5 ml`;
      - when the amount follows the volume: `5 ml syrup\n500 mg capsules`;
    - a pack that prints a dose volume and names no tablet or capsule, read per tablet: `Every 5 ml: shake well. Concor 5 mg`;
    - a dissolving line after `per`: `1000 mg per 200 ml of water`;
    - a combination printed with one unit, beside a pack volume: `160/4.5 mcg per inhalation, 10 ml`, where 160 isn't printed per dose;
    - a prefilled syringe or pen read per dose, whose strength is printed per its volume: `Clexane 40 mg/0.4 ml prefilled syringe`, `Ozempic 0.25 mg dose, 1.34 mg/ml, 1.5 ml pen` (the supervisor's round 6 #3). An exemption by container word would also let a syrup's oral syringe or a multi-dose pen through.
- **Prompts.** Both prompts say "never convert units", because "half a gram" written as 500 mg would not be stated.
  - **Claim prompt** (batch 21): "Write every amount and count as digits, even when the patient said it in words ('five' is 5, 'خمسة' is 5, 'twice a day' is 2), with the unit the patient said, and never convert units."
  - **Label prompt** (batch 21): "Copy all of its printed text into label_text, including every amount you report. Write each amount as digits with the unit printed on the pack, and never convert units. Name each ingredient by its English INN (amoxicillin, not amoxicilline or amoxicillinum), even when the pack prints it in another language or script."
  - **Both prompts keep their advice sentences word for word** (supervisor 21 #4): "Give no medical advice. Only report what the patient said." and "Give no advice. Use unreadable or partial rather than guessing."
  - **Why** (live, 28 Oct): batch 20's wording, "with the number … the patient said", made Spark copy number words (`"amount": "five"`, `"intakes_per_day": "once a day"`). Those never parse, so every dose spoken in words was dropped. Another reader transcribed only "Panadol TABLETS", so the label rule above dropped the 500 mg it reported. The stated-amount checks are unchanged: they still confirm that each digit amount was said or printed. `evidence/batches/21/live-before.md` has the runs.
- **Known limits.** Only the value is checked, not its unit or the word next to it: "one tablet, 50 mg" also states 1. `regimen` numbers are not checked; `units_per_intake` can never produce `match` (rule 8). A single number word there parses like its digit (batch 22) and isn't checked either, so an unstated "two" can still produce `intake_differs_from_unit_strength`, never `match` (pinned in batch 23, QM M5 #5). A check would drop intakes said with an Arabic dual such as «حبايتين» (two pills), which names no number. Spanish number words, digit-group speech ("eight seventy-five") and mixed forms ("2 and a half") state only their parts, so such an amount is dropped and the finding becomes `insufficient_information`. The rule fails closed.

## 3. Findings (closed enum, lowercase)
| `DiscrepancyType` | Needs both sides | Meaning |
|---|---|---|
| `match` | yes | Same identity, and every comparison that could be made agreed |
| `strength_mismatch` | yes | Stated strength ≠ pack strength, or an intake that the pack can't give |
| `intake_differs_from_unit_strength` | yes | Intake is 0.5× (only for a tablet the catalogue marks splittable), 2×, 3× or 4× the unit strength. Possibly fine: ask |
| `ingredient_mismatch` | yes | Different canonical INN sets (Panadol vs Panadol Extra with caffeine) |
| `ratio_mismatch` | yes | Same combination, different ratio (Augmentin 875/125 vs 500/125) |
| `formulation_mismatch` | yes | The named salts differ, or both release forms are known and differ (immediate vs modified) |
| `insufficient_information` | yes | Names agree, but the evidence can't confirm a match: no comparable amounts, release unknown against modified, unknown splittability, liquids, or contradictory extraction |
| `discontinued_but_present` | yes | Patient says they stopped; the pack is in the photo |
| `unreadable_source` | visual required | Label is unreadable or partial: abstain, never guess from shape or colour |
| `unresolved_name` | at least one side | Name not found in the catalogue, or the text names 2+ products |
| `missing_modality` | exactly one side | Only audio or only image evidence exists |

`Finding`: `finding_id`, `type`, `claim_id?`, `observation_id?`, `audio_evidence`, `visual_evidence`, `needs_clinician_review`, `clinician_note`, `patient_question_id?`.
- Every type except `match` requires `needs_clinician_review = true`.
- `claim_id` is set exactly when `audio_evidence` is non-empty, and `observation_id` exactly when `visual_evidence` is non-empty.
- **Text is enforced, not just advised:** `clinician_note` must equal `TEMPLATES[type]`, and `patient_question_id` must equal `QUESTION_FOR[type]`. Both tables live in `anamnesis/schema/templates.py`. The blocklist (`assert_no_advice`) is a regression check, not the safety boundary.
- The `match` template is narrowed to what was actually compared: **"The compared identity and strength details agree."** (QM M3 r2 #5; batch 17)
- The `formulation_mismatch` note names both causes: **"Reported and pack formulations differ (salt or release form)."** It used to say "release forms differ" even when only the salts did (QM M4 code #5; batch 19.1). Its patient question asks about both as well: **"What salt or release form is shown on your medicine pack?"** (QM M4 code round 2 #4; batch 21).

### Identity of one side
- Every ingredient field uses one resolver: a known catalogue moiety is canonicalised with `canonical_inn`; otherwise a name resolving to a single-INN catalogue entry resolves to that INN; otherwise the canonicalised input stays unchanged (unknown names remain unknown).
- **Identity set:** the resolved INNs of `strength.ingredients` if a strength exists. Otherwise the resolved scalar `{inn}`, otherwise the INNs of the catalogue entry that `name_text` (or `label_text`) resolves to.
- If a side has a strength and a resolvable name, or (when strength is absent) a scalar `inn` and a resolvable name, and their INN sets differ, that is an extraction conflict and the result is `insufficient_information`.
- When a side has both a strength and a scalar `inn`, the `inn`'s resolved moiety must be in the strength's ingredient set, otherwise it is an extraction conflict. A salt form of the same moiety is not.
- **Brand-implied facts** (`release`, `splittable`) come from the catalogue only when the text matched a **brand** name, never an INN. "Beloc-Zok" implies modified release; "metoprolol" implies nothing.
- **A text that names 2+ different catalogue products** (`name_text` or `label_text`, e.g. a label read as "Beloc-Zok 100 mg Concor 5 mg") is an extraction conflict on that side, even when the side's identity comes from its strength. (C4; batch 17)
- **Claim-side release is trusted only when the claim says so** (C8; batch 17): a claim's explicit `strength.release` counts only if `name_text` contains a curated release word (whole word after `normalise`: `retard`, `depot`, `xr`, `xl`, `sr`, `er`, `cr`, `mr`, `prolonged`, `extended`, `modified`, `sustained`, `controlled`, `slow`, `immediate`, `ممتد`, `بطيء`, and the feminine `ممتدة`, `بطيئة` (matched after `normalise`, which writes them `ممتده`, `بطيئه`; QM M4 #3, batch 19.1); the Arabic words also with the attached clitics `ال`, `وال`, `بال`, `فال`, `لل`, `و`, `ف`, `ب`, `ل`) or matches a catalogue brand. An unsaid explicit release still counts when it **disagrees** with the pack, so it can raise `formulation_mismatch`, but never when it agrees: then the claim's release is the brand-implied one (usually `unknown`), so a guessed release can't make a `match`. (Batch 17: the older contracts, b3 `release_ir_vs_er` and b10 `f01b`, keep a bare-name `immediate` claim against a modified pack as `formulation_mismatch`.) Pack-side release is read from the label and trusted as before.

### Decision order for one claim and one pack (`reconcile_pair`)
The first rule that applies wins.
1. Pack `partial` or `unreadable` → `unreadable_source`.
2. Either identity set can't be built → `unresolved_name`.
3. Extraction conflict on either side → `insufficient_information`. This includes one side naming two different salts of the same ingredient (checked here, before any cross-side comparison, even if the other side names no salt).
4. The identity sets differ → `ingredient_mismatch`.
5. The claim's status is `discontinued` → `discontinued_but_present`.
6. **Known formulation conflicts:** named salts for the same canonical ingredient differ, or both release forms (explicit, otherwise brand-implied) are known and differ → `formulation_mismatch`. Salts for each side come from one shared path: strength ingredients, `intake_amount` (claim only), `salt_of(inn)` and whole-word curated salt aliases found in `name_text` / `label_text` after `catalogue.normalise` (a longer alias suppresses a shorter one it contains).
7. Both sides have a strength: compare amounts in mg (g ×1000, mcg ×0.001; `ml` and `iu` only against the same unit). When the claim names no salt, curated pack salt-basis equivalents compare against the nominal amount for both strength and intake. A stated tablet strength is exact: it matches the literal pack amount or the nominal amount, never a multiple or fraction of either; only intakes use the 0.5, 2, 3 and 4 dose ratios. Formulation checks still apply first. Unequal → `strength_mismatch` or `ratio_mismatch`.
8. The claim has an `intake_amount` and the pack strength has more than one ingredient → `insufficient_information` (a single amount can't be checked against a combination; strength-only combination claims still compare under rule 7). Otherwise, when the claim has an `intake_amount` (also when 7 found equal strengths): compare its INN, resolved by the same ingredient resolver, with a single-ingredient pack strength; a mismatch → `insufficient_information`.
   - `per` ∉ {tablet, capsule} → `insufficient_information`.
   - Compute r = intake / unit strength. r = 1 → continue.
   - r ∈ {2, 3, 4} → `intake_differs_from_unit_strength`.
   - r = 0.5 on a tablet. Splittability is per product, because some scored ER tablets such as Beloc-Zok may be halved: `splittable: true` → `intake_differs_from_unit_strength`; `false`, or a capsule → `strength_mismatch`; unknown → `insufficient_information`.
   - Otherwise → `strength_mismatch`.
   - **Units per intake (C1, batch 17).** When `regimen.units_per_intake` = u with u ≠ 1, u is the ratio r against one pack unit and the same mapping applies (`per` ∉ {tablet, capsule} → `insufficient_information`; u ∈ {2, 3, 4} → `intake_differs_from_unit_strength`; u = 0.5 → by splittability as above; any other u → `strength_mismatch`). This runs after rule 7 found equal strengths (or the claim has no strength) and after an `intake_amount` comparison came out at r = 1 (or there is none): a model often copies the tablet strength into `intake_amount` for "half of the 20 mg", so the intake alone can't rule the units out (supervisor 17 #1). It never produces `match` and doesn't count as a comparison for rule 9. ("Half of the 20 mg Lipitor": strength 20 + u 0.5 against non-splittable Lipitor 20 → `strength_mismatch`, was `match`.)
9. No amount comparison was possible on either rule 7 or rule 8 → `insufficient_information`.
10. One release is `modified` and the other is `unknown` → `insufficient_information`.
11. Otherwise → `match`.

### Pairing (`reconcile_all`)
- Only readable packs can pair. Candidate pairs have overlapping identity sets.
- Score each candidate: 3 = same identity and equal strength, 2 = same identity, 1 = overlap. **A claim with no strength whose intake amount reconciles as `match` with the pack scores 3 as well** (batch 21). Live, 28 Oct, "Norvasc 5 mg in the evening" against a 10 mg box and a 5 mg box tied at 2. The tie went to the 10 mg box by id, so the 5 mg box was reported as not mentioned (staged case U5).
- **A named brand is compared with its own pack first** (batch 19): before the score, a pair whose claim `name_text` and pack `label_text` match the same catalogue brand comes first. With Panadol and Gelocatil both paracetamol, ID order alone could pair Panadol's claim with Gelocatil's pack. Ranking by score first could pair "Panadol 1 g" with an equal-strength Gelocatil 1 g pack and hide that the Panadol pack says 500 mg (supervisor 19 #4).
- Take candidates greedily by that preference, then score, then `claim_id`, then `observation_id`. Ties are broken by **ID**, not by list position, so the set of findings doesn't depend on the order of claims or packs. Findings come back sorted by `finding_id`.
- Leftovers:
  - an unreadable pack → `unreadable_source`
  - an unresolvable name → `unresolved_name`
  - otherwise → `missing_modality`

### Catalogue resolution
- `-` and `/` count as spaces and matching is on whole words. Each match records its character span; a match is suppressed only when its span is contained inside a longer match's span. Brand matches also cover INN or alias matches whose INN sets are within the brand's INNs. Text that names 2+ different brands or products → `None`; INN/alias-only matches sharing one INN set resolve deterministically by brand name.
- Arabic names remove diacritics and tatweel, normalize alef/ya/ta marbuta and Arabic-Indic digits, split Arabic/Latin boundaries, and accept the attached clitics `ال`, `وال`, `بال`, `فال`, `لل`, `و`, `ف`, `ب` and `ل`; curated Arabic brand aliases retain the brand's release and splittability.
- The country is a preference, never a filter: candidate entries sort country-match first (case-insensitive), then by brand, so the result is deterministic.
- Entries carry `release` and `splittable` (`true`, `false` or `null`). All entries are synthetic.

## 4. Agent loop (`anamnesis/agent/`, batches 14 and 15.5)
`run_intake(audio, images, ...)` runs a **fixed order**; no model chooses actions, nothing a model wrote is surfaced except source data (transcripts, label text), and there are no outer retries (adapters retry once themselves).
0. **Prepare** every photo before any model sees it (`prepare_image(data, mime) -> (data, mime)`, `anamnesis/agent/media.py`). Phones store the pixels sideways and record the turn in EXIF; SAM applies it and Spark does not (live, 27 Oct: on a portrait photo, 2 of 3 labels were read from the wrong pack). Preparation turns the pixels upright for every EXIF orientation (1–8) and drops all metadata (EXIF including GPS and camera tags, XMP, IPTC, ICC profiles, comments, PNG text chunks, and any extra frames such as an HDR gain map), so SAM, Spark, the crop and the brief see the same pixels and no location leaves the machine. A JPEG or PNG that is already upright and carries none of these is returned byte for byte. Otherwise a JPEG (including a multi-picture MPO, primary frame only) is re-encoded as JPEG (quality 95, 4:4:4 chroma), and anything else as PNG. Preparation is deterministic and idempotent; region hashes and `intake_id` use the prepared bytes, and callers that show a photo (the brief) show the prepared bytes. Bytes that can't be decoded raise `ValueError`; the loop then logs one `segment` step `error: image cannot be decoded` with no call ids, sends that photo to no model, and goes on with the next.
1. `transcribe` if there is audio. 2. `extract_claims` if there are turns.
3. Per image, `segment` with each concept in order (`medicine box`, `label`, `package`), stopping at the first that returns a region. `package` came in batch 23: on 28 Oct SAM 3.1 found no region with the first two in 19 of 30 Cairo University phone photos, `package` found one in all 19, and Spark 1.3 read 15 of those crops right (`evidence/batches/22/comparison.md`).
4. **Read the crop first (Z8, batch 18).** For each of the `top_regions(k=3)` of each image: only regions whose `image_sha256` and frame size match the prepared photo are kept, ranked and published in the report; each other region gets one `read` step `error: region does not match the photo` and is dropped. Each kept region is cut with `crop_region` (padded by 5% of the box size on each side, i.e. 10% in total, rounded down and clamped to the frame; refused unless the sha256 and frame size match the region) and the reader is called on the **crop only**, as PNG, with `cropped=True`. The reader never sees the full photo, so a reading can only describe the pixels of its own region (provenance by construction; live, 27 Oct: 8/8 crop reads correct at 465–1,001 input tokens against about 4,300 for the full photo). A crop that fails logs one `read` step `error: crop failed` (no provider call) and the region gets no reading. Once the session is exhausted, no crop is cut and nothing is logged.
5. Each `unreadable` or `partial` reading gets **one** `zoom_read`: the same crop, upscaled 2× (Lanczos; the factor is lowered so the longest side is at most 2,048 px; if that factor is ≤ 1 there is no zoom and no step), read with `cropped=True`. The new reading keeps the **source** `region_id`, so provenance stays in source pixels. SAM never runs on a crop. At most 2 reads per region (`max_grounding_iters = 2`). Both the read and the zoom cut their crop through the name `crop_region` in `anamnesis/agent/loop.py`.
6. `reconcile` with `reconcile_all`.
- **Budget:** every provider call, including failed ones, counts 1 against `max_provider_calls`. Its default (batch 23 round 2, supervisor 23 #3) is enough for every call the loop can make: 2 for the voice note, plus, per photo, one per concept and two per region (a read and a zoom), so `2 + (len(concepts) + 2 × top_k) × photos`, 29 for three photos with the defaults. The dollar caps (`SessionGuard`) bound the spend. With a fixed 12, batch 23's third concept ran the budget out on a four-photo intake, and a pack the patient had sent was reported as not photographed. An explicit `max_provider_calls` still sets the budget. Without a dollar cap the default grows with the number of photos, so every caller that spends real money wraps the providers in a `SessionGuard` with `max_usd` (`scripts/intake_live.py` does, with `--session-usd`; supervisor 23 round 2 #4). The call that would exceed it is skipped, a `budget_exhausted` step is logged (it is then the last step, whatever fails afterwards, including a crop), and every remaining provider call is skipped. Reconciliation still runs on what exists.
- **Errors:** a provider error becomes a step whose `outcome` is `error: <provider> <ExceptionName>` (no message text); the loop continues with the next item.
- **Report** (batch 20 adds `superseded`, §8): one `ReconciliationReport` (`anamnesis/schema/report.py`): turns, claims, regions, observations (`o0, o1, ...` in reading order, `visual_evidence=[region_id]`), findings, steps, `calls`, `spend_usd` (sum of `cost_usd + prior_cost_usd` over every returned trace) and a sha256 `intake_id` of the inputs. A validator rejects any evidence, claim or observation id that points nowhere.
- **Each step records its call** (batch 23): `model_id` (`None` without a trace), `input_tokens`, `output_tokens` and `latency_ms` (0 without a trace), and `cost_usd`, everything the step was charged: `cost_usd + prior_cost_usd` of its trace, or the `charged_usd` of a failed call. The model, tokens and latency come from the returned trace, or from a failed call's `attempt_trace` when it has one. So the steps add up to `spend_usd`, also after `add_photo` (§8). A step without a call costs 0, and a step from before batch 23 loads with these defaults. A step's `model_id` with `-contributor` anywhere, in any case, is refused.
- **Session caps:** `SessionGuard(parent, max_usd, max_calls)` wraps the ledger guard with a per-session dollar and call cap and still writes every charge to the parent.
- Voice, SAM, and Spark calls retry once on retryable errors and use a 30 s timeout.

### Open-weight label reader (`anamnesis/providers/openweight.py`, batch 22)
On 28 Oct Ahmed added a zero-shot comparison with Meta's open-weight **Muse Spark Open**. The training research (`evidence/decisions.md`, 28 Oct) found no time for a fine-tune before the freeze. Glimmer joins the comparison if an endpoint is up in time.
- **The provider.** `OpenWeightLabelReader` reads a pack exactly as `MetaLabelReader` does, through an OpenAI-compatible endpoint (`PRESETS`):
  - Fireworks: `https://api.fireworks.ai/inference/v1`, model `accounts/fireworks/models/muse-spark-open`, JSON mode on.
  - Baseten: `https://inference.baseten.co/v1`, model `meta-models/muse-spark-open`, JSON mode off.
- **The same request and checks.** It uses the same `_SYSTEM_PROMPT`, user text and image, the same `response_format` where JSON mode works, and the same `parse_label_json`. So the shape check, the advice check and the "amount printed on the label" rule all apply unchanged.
- **Without JSON mode,** the user text adds one sentence: "Reply with only one JSON object that matches this JSON schema: " followed by `LABEL_SCHEMA` as sorted JSON. One surrounding code fence is stripped before parsing.
- **The same control flow.** The same estimate, the cap check before the request, the charge after it, one retry on a malformed reply, and no retry after a length stop.
- **Spend.** Prices are $1.25 per 1M input and $4.25 per 1M output tokens (`muse-spark-open@fireworks`, `muse-spark-open@baseten`). The trace, the ledger and every estimated ledger line name the model with its provider. A model id with `-contributor` anywhere, in any case, is refused, as `scripts/batch.sh` refuses it. Every error the reader raises names its provider (`fireworks` or `baseten`), never `spark`. The client waits 60 s by default. The API key is redacted from every error, and it comes only from the Keychain or the environment.
- **The comparison is zero-shot.** No model is trained. SAM 3.1 segments each photo once, and every reader reads the same crops. The 39 public photos were pre-registered before any run: 30 Egyptian phone photos (CC BY 4.0) and 9 Wikimedia Commons photos. **Ahmed's own photos never go to these providers**: they go only to Meta's API (`docs/DATA_HANDLING.md`).
- **Licence.** Muse Spark Open is used under the Muse Model License, and the README carries "Built with Muse Spark Open".

## 5. Every model call logs
- **Ledger** (`evidence/spend/ledger.jsonl`): `call_id`, `model_id`, `cost_usd`, `time_utc`, `estimated` (+ `reason`). Lines from before batch 12 have no `estimated` field; all of them are real charges.
- **Trace** (saved with each live result in `evidence/live/<date>/*.json`): latency and tokens as listed below.
- Muse Code grill runs (the `muse` CLI) are billed by Meta **outside** our adapters, so they are not on the ledger (see `evidence/decisions.md`).

`model_id`, `latency_ms`, `input_tokens`, `output_tokens`, `cost_usd` → `evidence/`.
**No contributor model** (batch 22 round 2, batch 23; QM M5 #7): `MetaLabelReader`, `MetaClaimExtractor`, the open-weight reader, `ProviderTrace` and `AgentStep` all refuse a model id with `-contributor` anywhere in it, in any case, surrounding whitespace ignored, as `scripts/batch.sh` does.
 Hosted Meta models are the default. Open weights (Glimmer on Modal, Spark Open on Baseten) are for comparison only.
Billing-uncertain failures are recorded at the pre-call estimate. Rejected 4xx and
429 requests are not charged.

**Spark estimates and length stops (C6, C7, batch 18; reply schema, batch 19).** A Spark call's pre-call estimate is an upper bound, not a constant, computed by `spark_call_estimate(body)` in `anamnesis/providers/meta.py` from the request body it will send: `cost_usd(model, input_tokens = (characters of all text in the messages + characters of json.dumps(body["response_format"]) when the body has one) // 2 + 5,000 per attached image, output_tokens = max_tokens)`. The reply schema is billed as prompt tokens: without it, the live claim calls of 27 Oct were bounded at 391 and 383 input tokens against 550 and 559 billed, and a length stop at that size ended $0.0002 over a cap set to the bound (supervisor 18 #1). The same figure is checked against every cap before the call and charged when billing is uncertain. Claim extraction uses `max_tokens = 16000` (reasoning counts toward it; live 3-medicine notes already used about 2,700); label reads use `max_tokens = 4000`. A reply with `finish_reason: "length"` is charged at its real usage and raised as a **non-retryable** `ProviderError` carrying its call id: a retry would stop on length again.

## 6. Build rules
- All models use `extra="forbid"`. No recursive JSON schemas.
- Tests pass offline, with no keys and no network.
- `tests/contract/` is written by the reviewer before each batch. A batch that edits it is rejected.

## 7. Clinician brief (`anamnesis/brief.py`, batch 19)
`render_brief(report, images, audio, catalogue) -> str` turns one `ReconciliationReport`, plus the photos and the voice note that were given to `run_intake` (`images: list[(bytes, mime)]`, `audio: (bytes, mime) | None`), into **one self-contained static HTML page** that can be hosted as it is (J3). Every `src` is a `data:` URI and every `href` an in-page `#` link; there is no `<link>` element, and the only script is one inline `<script>` that plays a turn (no `on…` event attributes). It calls no model, and the same inputs give the same string. **It refuses media the report wasn't made from:** `render_brief` and `coverage_lines` first recompute `intake_id` exactly as `run_intake` does (the loop's own photo preparation, in input order, and the audio bytes) and raise `ValueError` if it differs from the report's. Otherwise a report could be shown against another recording or photo (supervisor 19 #3). Its fixed text comes from `anamnesis/schema/templates.py`. Source data (transcripts, `name_text`, label text, model-read values) is HTML-escaped and shown verbatim, never paraphrased.

**Order: disagreements first** (supervisor #1, #6). After a `<header id="scope">`, the page has these `<section id="…">` elements, always all of them and in this order. An empty section shows "None.".
| `id` | What goes in it |
|---|---|
| `disagree` | `strength_mismatch`, `intake_differs_from_unit_strength`, `ingredient_mismatch`, `ratio_mismatch`, `formulation_mismatch`, `discontinued_but_present` |
| `across` | cross-medication observations (below) |
| `unconfirmed` | `insufficient_information`, `unreadable_source`, `unresolved_name`, `missing_modality` (except the `stopped` row) |
| `agree` | `match` |
| `stopped` | `missing_modality` findings with only a claim, whose status is `discontinued` (historical statements) |
| `coverage` | the coverage lines (below) |
| `photos` | each photo that could be opened, upright, with its SAM boxes, then each region's crop |
| `voice` | the voice note and its turns |

**A finding** is `<article id="finding:<finding_id>" data-type="<type>">`, in report order, with:
- its heading, an `<h3>`: the first non-blank line of the claim's `name_text`, otherwise of the label text, otherwise "Unnamed pack";
- `TEMPLATES[type]`, and the patient question when there is one;
- the two sides **side by side**: `data-side="patient"` (name, the scalar `inn` when there is one, strength and intake amount with each ingredient's salt, regimen and status, verbatim) and `data-side="pack"` (label text, the scalar `inn` when there is one, strength with each ingredient's salt, readability, country). A salt-only `formulation_mismatch` must show both salts, wherever rule 6 found them, including a salt named only in `name_text` or the label text (QM M4 code #5 and round 2 #1; supervisor 19.1 #3). The Name, Ingredient and Label text rows are HTML-escaped and marked `dir="auto"` (supervisor 19.1 round 2; batch 21). On both sides, each amount and its unit is wrapped in `<bdi dir="ltr">`, so an Arabic row reads "50 mg", never "mg 50" (judge-facing session, 28 Oct; batch 21). Amounts print as plain decimals with their unit and never with a trailing zero ("100 mg", never "100.0 mg"; "0.5", never ".5"), the safe-notation rule for doses. A missing side says "Not mentioned." or "Not photographed.";
- A3 wording: a `missing_modality` finding is labelled "Mentioned, not photographed" or "Photographed, not mentioned", and one in `stopped` "Reported as stopped, not photographed";
- a link to every piece of its evidence: `href="#turn:<turn_id>"` for each audio turn, `href="#region:<region_id>"` for each region.

**Evidence on the page.**
- Each photo that opens is `<figure id="photo:<i>">` (input order, from 1), with one `<img>` of the **prepared** bytes (§4 step 0) under an `<svg viewBox="0 0 <frame_w> <frame_h>">`. The svg has one `<rect>` per report region of that photo, at `x1, y1`, `x2 − x1 + 1` wide and `y2 − y1 + 1` high, inside `<a href="#region:<region_id>">`. A box is an outline with a transparent fill, so the pack under it stays visible and the whole box is clickable. No image makes the page wider than the screen.
- Each report region is `<figure id="region:<region_id>">` showing `crop_region(prepared photo, region)`. For a region that was read, these are exactly the pixels of the reader's first read (a `zoom_read` saw the same crop enlarged 2×); this is the click-to-zoom view. A report region whose photo isn't among the given photos is refused with `ValueError`, never skipped.
- The voice note is one `<audio src="data:…">`. Each turn is `<li id="turn:<turn_id>" data-start-ms="…" data-end-ms="…">` with its time range and transcript. Clicking it plays that turn only, from its start to its end, and starting another turn ends the first. The contract runs the script in Node against a small DOM, so the script uses only `querySelector`/`querySelectorAll` with tag and attribute selectors, `getElementById`, `getAttribute`, `dataset`, `closest` and `addEventListener`.
- Every `#` link on the page points to an element on the page.

**Cross-medication observations** (`cross_medication(claims, catalogue)` in `anamnesis/core/overlap.py`; supervisor #2, J2). Pairwise reconciliation can't see two medicines that overlap each other: the showcase patient reports Concor and Beloc-Zok, two beta-blockers. Only **claims** count, never the photos, because a pack can't show use and repeated photos never imply duplicate use.
- A claim counts unless its status is `discontinued`, and only if its identity set (§3) can be built. **A claim with an extraction conflict counts only by the ingredients its identity set shares with the catalogue entry its `name_text` resolves to.** When the name doesn't resolve to one entry, or they share none, it doesn't count. An observation built on one of two disagreeing readings could name the wrong medicine (QM M4 code #2; supervisor 19.1 #2):
  - "Concor" with a metoprolol strength doesn't count, rather than being listed as metoprolol;
  - "Panadol" with a paracetamol + caffeine strength counts as paracetamol. Its *product* is the catalogue brand when `name_text` matches a brand or alias name, otherwise `normalise(name_text)`. A brand said twice, in either script, is one product.
- `same_ingredient`: for each INN, the counted claims whose identity set contains it, when they name 2+ different products (Panadol + Gelocatil, Panadol + "paracetamol", Panadol + Panadol Extra).
- `same_class`: for each class in the curated `DRUG_CLASSES` (only `beta-blockers`: bisoprolol, metoprolol), the counted claims whose identity set contains a member, when they hold 2+ different members and name 2+ different products.
- One observation per INN or class, with `kind`, `key` (the INN or the class name), `claim_ids` (sorted), the claims' `audio_evidence` (sorted, no repeats) and its `note`. Order: `same_ingredient` by key, then `same_class` by key.
- Notes (fixed): `same_ingredient`: "More than one product the patient mentioned, and did not report as stopped, contains this ingredient. Concurrent use is unconfirmed." `same_class`: "More than one medicine the patient mentioned, and did not report as stopped, belongs to this class. Concurrent use is unconfirmed."
- In the brief, each observation is `<article data-kind="<kind>">` in `across`, with its note, its key, and each claim's `name_text` linked to that claim's turns.

**Coverage** (`coverage_lines(report, images, audio) -> list[str]`; supervisor #4, Z5: a photo where nothing was found is never silent). A photo is prepared as the loop does it: `prepare_image`, then decoded; a `ValueError` or `OSError` means it could not be opened. A photo's `segment` steps are those whose target starts with the first 12 hex characters of its prepared sha256 followed by ":". Each line is one `<li>` of the `coverage` section. The lines, in order:
1. `Photos received: <n>.`
2. One line per photo, in input order from 1, the first that applies:
   - `Photo <i>: could not be opened; no model saw it.`
   - `Photo <i>: not examined; the call budget ran out first.` (no `segment` step for it)
   - `Photo <i>: pack detection failed.` (every `segment` step for it is an error)
   - `Photo <i>: no pack found.` (no report region on it)
   - `Photo <i>: packs found <r>, labels read <o>, not fully readable <u>.` (r report regions on it, o observations of those regions, u of them `unreadable` or `partial`)
3. The voice note, the first that applies: `Voice note: none.` (no audio), `Voice note: not transcribed.` (no turns), `Voice note: turns <t>; medicines could not be extracted.` (the `extract_claims` step is missing or an error), `Voice note: turns <t>, medicines mentioned <c>.`
4. Only when the report has a `budget_exhausted` step: `The intake stopped early: the call budget ran out, so later steps were skipped.`

**How it got here** (batch 23). After the last section and before the script, one `<details id="timeline">`, collapsed (no `open` attribute), so the page still has exactly the sections above. Its `<summary>` is `TIMELINE_HEADING` ("How it got here"), then one `<table>`:
- `<thead>`: one row of `<th>`, the `TIMELINE_COLUMNS`: `#`, `Step`, `Target`, `Outcome`, `Model`, `Tokens in`, `Tokens out`, `Time`, `Cost`.
- `<tbody>`: one row of `<td>` per report step, in order: `n`, the action, the target, the outcome; then the model, tokens in, tokens out, and the time in seconds with one decimal (`6.5 s`), each `TIMELINE_NONE` (`—`) when the step has no `model_id`; then the cost, `$` and the amount formatted `.5f` (`$0.00811`).
- `<tfoot>`: one row with one cell, `TIMELINE_TOTAL` (`Total: {calls} calls, ${usd}`) with the report's `calls` and its `spend_usd` formatted `.5f`.
Every value is HTML-escaped; the labels are fixed templates in `anamnesis/schema/templates.py`. Nothing a model wrote appears here.

**Scope lines**, in the header, always (supervisor #3, #4):
- "Anamnesis reports where the patient's account and the pack photos disagree. It gives no medical advice."
- "Prescribed directions, timing, adherence and supply were not assessed."
- "Over-the-counter, herbal and non-tablet products may be missing from this brief: ask about them."
- "Checks across medicines cover shared ingredients and one curated class (beta-blockers); interactions were not assessed." (QM M4 code #8; batch 19.1)

**Catalogue:** one synthetic entry for the hero case (J2): Gelocatil (ES; paracetamol; immediate release; splittability unknown; Arabic aliases جيلوكاتيل and جلوكاتيل).

**Review (batch 20):** the review status, open photo requests, replaced packs and the request count on the brief are specified in §8 "On the brief".

## 8. Clinician review and photo requests (`anamnesis/review.py`, batch 20)
Nothing in a brief is final until a clinician approves it. Before approving, the clinician can ask the patient for **one new photo** of a pack that couldn't be read, or of a medicine the patient mentioned but didn't photograph. Only that photo is processed, and the intake continues from the saved report. This is the workshop's "the run pauses for a person, then resumes", without letting a model choose anything: the clinician chooses, and the code checks the choice is allowed.

**Schema** (`anamnesis/schema/review.py`, `extra="forbid"`):
- `RequestKind`: `unreadable` (the target is an `observation_id`), `not_photographed` (the target is a `claim_id`).
- `RequestStatus`: `open`, `answered`, `withdrawn`.
- `PhotoRequest`: `request_id` (`r1`, `r2`, … in the order they were made), `kind`, `target_id`, `status`, `photo_index` (the 1-based position of the answering photo in the full photo list; set exactly when `answered`).
- `ReviewStatus`: `draft`, `awaiting_patient`, `approved`.
- `Review`: `intake_id` (of the report it is about), `status`, `requests` (default empty). A validator enforces that `status` is `awaiting_patient` exactly when a request is `open`, and that an `approved` review has no open request.
- `ReconciliationReport.superseded: list[str]` (default empty): observation ids replaced by an answered `unreadable` request. Each must name an existing observation, and no finding may cite one.

**Functions.** All of them are pure: each returns new objects and never changes its inputs. Each raises `ValueError` when refused, and a refusal changes nothing.
- `new_review(report) -> Review`: `draft`, no requests.
- `requestable(report) -> list[tuple[RequestKind, str]]`, in report finding order: an `unreadable_source` finding with an observation gives `(unreadable, observation_id)`; a `missing_modality` finding with only a claim, whose claim is not `discontinued`, gives `(not_photographed, claim_id)`. Nothing else can be requested: a model's reading can't be argued with by asking again.
- `request_photo(review, report, target_id) -> Review` adds an `open` request with the next `request_id`. Refused when the review's `intake_id` isn't the report's, the review is `approved`, the target isn't in `requestable(report)`, or an `open` request for that target already exists.
- `withdraw(review, request_id) -> Review`: an `open` request becomes `withdrawn`; anything else is refused.
- `request_message(report, request) -> str`: the text sent to the patient, from `templates.py`. `unreadable`: "Please send one new photo of this medicine pack, with the label facing the camera, in good light." `not_photographed`: "Please send one photo of the pack of the medicine you mentioned as “{name}”.", where `{name}` is the first non-blank line of the claim's `name_text`, verbatim.
- `add_photo(report, review, request_id, photo, images, audio, *, segmenter, reader, catalogue, concepts=("medicine box", "label", "package"), top_k=3, max_provider_calls=None) -> (ReconciliationReport, Review)` answers one `open` request with one photo. Its concepts are the loop's, one shared default (batch 23 round 2: Muse's report, supervisor 23 #4, QM M6 #6), and its budget defaults to `len(concepts) + 2 × top_k` (9): every call one photo can need.
  - It is refused when the review's `intake_id` isn't the report's (supervisor 20 #2: a review of another report could otherwise hide a pack that was read), when the request isn't `open`, when `images` and `audio` aren't the media of `report` (recomputed exactly as the brief does), or when the photo's prepared bytes equal one already given (region ids would collide).
  - The new photo goes through §4 steps 0 and 3–5 alone, with its own `IntakeSession(max_provider_calls)`. Turns and claims are kept and no other photo is sent to any model. An undecodable photo logs the same `segment` error step as in the loop.
  - The new steps are appended to the report's, numbered on from the last `n`; a final `reconcile` step is logged unless the new session is exhausted. `calls` and `spend_usd` add the new session's.
  - New observations are numbered on from the existing ones (`o<len>` …) and new regions appended, de-duplicated by `region_id` as the loop does (supervisor 20 #3). An `unreadable` request adds its target to `superseded`, **but only when the new photo gave at least one observation**: a photo that can't be opened, shows no pack or runs out of budget never hides the pack it was meant to replace. Then `reconcile_all(claims, observations not superseded, catalogue)` replaces the findings.
  - The new `intake_id` is the loop's `_intake_id(audio bytes, prepared images + [prepared photo])`, so `render_brief(report, images + [photo], audio, …)` accepts it and nothing else.
  - The request becomes `answered` with `photo_index = len(images) + 1`. The returned review carries the new `intake_id`, and its status is recomputed. The request counts as answered whatever the photo shows: a photo with no pack, or one that is again unreadable, is reported as such and can be requested again.
- `approve(review, report) -> Review` → `approved`. Refused when the `intake_id`s differ or a request is `open`. An approved review is final: nothing more can be requested or withdrawn.

**On the brief** (`render_brief(..., review=None)`):
- The `scope` header gains `<p id="review-status">`. With no review, or a `draft` one: "Draft: not yet reviewed by a clinician." With `awaiting_patient`: "Waiting for the patient: new photos requested {n}." (`n` open requests). With `approved`: "Reviewed and approved by the clinician." A review whose `intake_id` isn't the report's is refused with `ValueError`.
- A finding whose target (its `observation_id` for `unreadable`, its `claim_id` for `not_photographed`) has an open request of that kind shows `<p data-request="<request_id>">` with "A new photo has been requested from the patient."
- The region figure of a superseded observation adds "Replaced by a newer photo." Coverage counts it like any other observation.
- When the review has a request that isn't withdrawn, coverage ends with "Photos requested {n}, received {m}." (`n` the requests that aren't withdrawn, `m` the answered ones).
- All of this text lives in `templates.py` and passes `assert_no_advice`.
