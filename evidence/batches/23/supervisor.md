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
