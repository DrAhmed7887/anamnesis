# Batch 22: zero-shot label reading on 39 public photos, 28 Oct

**What was compared:**
- **The readers:** Meta's hosted **Muse Spark 1.3**, and Meta's open-weight **Muse Spark Open** on two hosts:
  - **Baseten**, without JSON mode: the schema goes in the prompt;
  - **Fireworks**, with strict JSON mode.
- **The same input for each:** the same SAM 3.1 crops, system prompt, schema and parser (`anamnesis/providers/openweight.py`, batch 22).
- **Zero-shot:** no model was trained.
- **Pre-registered:** the expected readings and scoring rules were committed before any call (c1b5b6e: `preregistration.json`, `preregistration-gemini.json`, `preregistration-notes.md`).
- **Run:** `scripts/reader_eval.py`, one pass. The photos are 30 Cairo University phone photos (CC BY 4.0, two per pack) and 9 Wikimedia Commons photos.

**This is a comparison, not a benchmark.** n is small and every miss is listed.

## Coverage first: SAM found a pack in 20 of the 39 photos
- **Found:** all 9 Commons photos, and 11 of the 30 Cairo photos.
- **Not found:** the other 19 are "no pack found" for every reader, as in the loop. SAM ran with "medicine box", then "label".
- **The no-pack photos:** `pk101_b`, `pk084_a/b`, `pk136_a/b`, `pk013_a/b`, `pk002_a`, `pk035_b`, `pk025_b`, `pk068_a`, `pk034_a/b`, `pk063_a/b`, `pk042_a/b`, `pk097_a/b`.

## Results on the 20 photos with a crop

| Reader | Correct | Harmful | Missed | Abstained | Error | Cost per read | Median time |
|---|---|---|---|---|---|---|---|
| Spark 1.3 (Meta API) | **14** | 2 | 0 | 4 | 0 | $0.0094 | 7.4 s |
| Spark Open on Baseten | **14** | 1 | 0 | 3 | 2 | $0.0136 | 15.4 s |
| Spark Open on Fireworks (JSON mode) | 1 | 1 | 10 | 8 | 0 | $0.0100 | 23.4 s |

- **Spark 1.3 and Spark Open on Baseten agree closely.** Both are right on the same 12 photos.
  - Only Spark 1.3 is right on `bloxazoc_50mg_krka_box` and `paracetamol_650mg_blister`.
  - Only Baseten is right on `pk092_a` and `pk092_b`, the two Janumet photos.
- **Fireworks' JSON mode returned no strength on any of the 20 crops**, even though its `label_text` held the amounts. So this column measures the host's strict JSON mode, not the open weights (diagnostic 1 below).

### Every photo with a crop

| Photo | Printed | Spark 1.3 | Spark Open, Baseten | Spark Open, Fireworks |
|---|---|---|---|---|
| pk014_a | amoxicillin 875 mg + clavulanic acid 125 mg | correct | correct | miss: INNs, no strength |
| pk014_b | amoxicillin 875 mg + clavulanic acid 125 mg | correct | correct | abstained (partial) |
| pk101_a | amoxicillin + clavulanic acid, no strength printed | correct | correct | correct |
| pk092_a | sitagliptin 50 mg + metformin 1000 mg | abstained (partial) | correct | abstained (partial) |
| pk092_b | sitagliptin 50 mg + metformin 1000 mg | **harmful: metformin 100 mg** | correct | **harmful: INN "not_printed_in_visible_crop"** |
| pk002_b | paracetamol 500 mg | correct | correct | miss: no strength |
| pk035_a | paracetamol 250 mg/5 ml (syrup) | **harmful: 250 mg per dose** | **harmful: 250 mg per ml** | abstained (partial) |
| pk028_a | candesartan 16 mg + hydrochlorothiazide 12.5 mg | correct | correct | miss: no strength |
| pk028_b | candesartan 16 mg + hydrochlorothiazide 12.5 mg | correct | correct | miss: no strength |
| pk025_a | ibuprofen 400 mg | abstained (partial) | abstained (partial) | abstained (partial) |
| pk068_b | metronidazole 500 mg | correct | correct | miss: no strength |
| concor_5mg_china_retail | bisoprolol 5 mg | correct | correct | miss: no strength |
| bisoprolol_2_5mg_sandoz_es (Orion, FI/SE) | bisoprolol 2.5 mg | correct | correct | miss: no strength |
| augmentin_1g_gsk_box | amoxicillin 875 mg + clavulanic acid 125 mg | abstained (partial) | error: length stop | abstained (partial) |
| augmentin_875_125_blister_nl | amoxicillin 875 mg + clavulanic acid 125 mg | correct | correct | abstained (partial) |
| bloxazoc_50mg_krka_box | metoprolol 50 mg | correct | error: length stop | miss: no strength |
| metoprolol_50mg_ratiopharm_de (Baltic) | metoprolol 50 mg | abstained (partial, read 50 mg) | abstained (partial, read 50 mg) | abstained (partial) |
| siofor_500mg_metformin_box | metformin 500 mg | correct | correct | miss: no strength |
| metformin_500mg_generics_uk | metformin 500 mg | correct | correct | miss: no strength |
| paracetamol_650mg_blister | paracetamol 650 mg | correct | abstained (partial, read 650 mg) | abstained (partial) |

### The harmful verdicts, one by one
- **Janumet, `pk092_b`:** Spark 1.3 read the metformin as **100 mg** where the pack prints 1000 mg. That is a dropped digit, shown as fact.
- **CETAL syrup, `pk035_a`, printed 250 mg/5 ml:**
  - Spark Open on Baseten wrote **250 mg per ml**, a fivefold error.
  - Spark 1.3 wrote 250 mg "per dose".
  - The schema can't say "per 5 ml", and the pre-registration made strength null the only right answer here, so both count as harmful.
  - The loop now drops such a strength (batch 23, part 4).
- **Janumet, `pk092_b`, Fireworks:** it put "not_printed_in_visible_crop" in the INN field of a readable reading. By the pre-registered rule that is an INN shown as fact. In the loop it would fail to resolve, so it fails safe there.

**The errors:** Baseten stopped at the 4,000-token limit on two crops. That gave no reading, was charged, and failed safe. Diagnostic 4 below read both crops again.

## A scorer fix after the run
The scorer splits the `inn` field into a set at "+", "/", "&", "and" and "with". Readers also wrote combinations with a comma ("sitagliptin, metformin"), so the comma was added after the run. It changed four verdicts, all from harmful:
- `pk101_a`, Fireworks: now correct;
- `pk092_b`, Baseten: now correct;
- `pk028_a`, Spark 1.3: now correct;
- `pk028_b`, Fireworks: now a miss.

The one other comma entry, Fireworks' "not printed, Janumet brand name only", was already abstained.

**As scored at run time** (correct / harmful / missed / abstained / error):

| Reader | As run | After the fix |
|---|---|---|
| Spark 1.3 | 13 / 3 / 0 / 4 / 0 | 14 / 2 / 0 / 4 / 0 |
| Baseten | 13 / 2 / 0 / 3 / 2 | 14 / 1 / 0 / 3 / 2 |
| Fireworks | 0 / 3 / 9 / 8 / 0 | 1 / 1 / 10 / 8 / 0 |

## Diagnostics decided after seeing the results (not pre-registered)
1. **Fireworks with JSON mode off.** On 5 crops where Spark 1.3 and Baseten were right, the same model on Fireworks read **5 of 5** correctly, strengths included. It cost $0.068, at 15.7–52.2 s a read (`reader_eval_fireworks_textmode.jsonl`).
2. **Other SAM concepts on the 19 no-pack photos.** "package" found exactly one region in **all 19**, at confidence 0.76–0.95, for $0.048 (`sam_concepts_diagnostic.jsonl`).
3. **Spark 1.3 on those 19 "package" crops** (`reader_eval_package.jsonl`), for $0.17:
   - **15 correct;**
   - 2 abstained (Atoreza `pk013_a`, LAMISIL `pk097_a`);
   - 1 missed: a readable Clarinase with no INN;
   - 1 harmful: the CETAL syrup again, `pk035_b`, read as 250 mg per ml.

   With "package" as a third concept, Spark 1.3 would have read **22 of the 30** Cairo phone photos correctly, not 7. Batch 23 makes it the loop's third concept, tried only when the first two find nothing.
4. **Baseten's two length stops, read again** the same evening (`evidence/batches/22/diagnostics.py baseten-cap`), with max_tokens 8,000 instead of 4,000 and nothing else changed. Both came back correct: `augmentin_1g_gsk_box` as amoxicillin 875 mg + clavulanic acid 125 mg, and `bloxazoc_50mg_krka_box` as metoprolol 50 mg. It cost $0.038, at 16.4 and 17.4 s a read (`reader_eval_baseten_cap8k.jsonl`).
   - **The higher cap didn't fix them.** Both replies ended under the old cap, at 2,556 and 3,675 tokens, so this was a second draw.
   - **The table keeps both as errors.** Only Baseten got a second draw, and only on these two crops. The reader keeps its 4,000-token cap.

## Cost
- **The pass:** $0.85.
  - Meta $0.36: SAM $0.17 (68 calls) and Spark 1.3 $0.19.
  - Fireworks $0.20.
  - Baseten $0.29, including $0.045 for the two length stops, which were charged.
  - Corrected on 28 Oct evening from the ledger: this list first said SAM $0.22, Meta $0.40 and Baseten $0.25, which added up to the same total.
- **Pilots and diagnostics:** another $0.40, $0.28 of it on Meta (SAM and Spark 1.3). The rest was Fireworks and Baseten, including diagnostic 4's $0.04 on Baseten.
- **The Meta total** stays far under the 50% pause line (`scripts/spend_check.py`). The Fireworks and Baseten lines are billed by those providers, not Meta.

## Limits
- **Small n.** 39 photos, 20 with a crop. The 30 Cairo photos are 15 packs, photographed twice.
- **One pass and one prompt.**
- **Judgement calls** are listed above: the CETAL "per dose", and Fireworks' placeholder INN.
- **Costs** are our ledger's estimates. Each provider's dashboard is the final word.
- **Glimmer** was not run: no vision endpoint was ready.
