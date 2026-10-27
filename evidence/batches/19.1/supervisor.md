# Batch 19.1 supervisor (Claude Opus 5.5, high effort, read-only)

Prompt: `evidence/grills/BATCH_SUPERVISOR_PROMPT.md`. The builder was Muse Code (`muse-spark-1.3`). The supervisor is a different model family and was not told the CEO's opinion. It probed offline, in scratch copies of the code from before and after the batch.

## Round 1: SUPERVISOR: CHANGES
1. **blocker** `anamnesis/brief_html.py` (salts rendered), `anamnesis/providers/spark.py`, `anamnesis/core/guardrails.py`. A model-written `salt` now reaches the brief with no advice check.
   - Why it gets through: `IngredientAmount.salt` is a declared field, so `parse_label_json` accepts a `"salt"` key. The label parser has no exact-key check like the claim parser's, and the advice check covers only `inn`.
   - Ran: a label whose ingredient salt is "double the dose if dizzy" gives `match`. The pack row reads "metoprolol double the dose if dizzy 100 mg per tablet (modified)"; before the batch the text never reached the page.
   - Live requests use the strict `LABEL_SCHEMA`, which has no salt key, but the parser is the trust boundary.
2. **major** `anamnesis/core/overlap.py`. Skipping every conflicted claim hides a real duplicate. Ran: "Panadol" with a paracetamol + caffeine strength, plus Gelocatil, gives `same_ingredient paracetamol` before the batch and nothing after, though both readings hold paracetamol. A fix tried in a copy (count by what the identity shares with the name's entry) keeps all 696 tests passing.
3. **major** `anamnesis/brief_html.py`. A salt named only in the scalar `inn` field (rule 6 uses `salt_of(inn)`) is shown on neither side. Ran: claim inn "metoprolol tartrate" against pack inn "metoprolol succinate" is a `formulation_mismatch`, but both sides read "metoprolol 100 mg per tablet".
4. **minor** Nothing pins the Arabic advice word boundaries: removing either boundary passes the suite. Without them, "يتناول", "المتناول", "أخذ" and "تناولت" would be rejected.
5. **minor** These gaps are out of the SPEC's scope:
   - missed: suffixed and negated advice forms ("خذي", "تناوله", "لا تتناول") and Arabic presentation-form letters (no NFKC);
   - false positive: a bare "فخذ" (thigh).
6. **minor** The clitic list is written out three times (guardrails, reconcile, catalogue).

Checked clean:
- **Arabic decimal sign:** 402,233 fuzzed strings; it only turns a `None` into the dot form's value.
- **Catalogue names:** no brand, alias or INN alias trips the advice check.
- **Feminine release words:** near-misses ("كممتدة", "ممتدهم") don't count.

Mutations: 10 of 12 caught; the two advice-boundary mutants survived.

**CEO triage:**
- **#1–#4 accepted, with new contract cases for round 2 in `test_b19_1_qm_fixes.py`:**
  - #1: a label strength with any key beyond `LABEL_SCHEMA`'s is malformed (SPEC §2), so salts reach a pack only through the curated split.
  - #2: the supervisor's rule is adopted (SPEC §7). A conflicted claim counts by what its identity shares with the catalogue entry its name resolves to.
  - #3: the scalar `inn` is shown on both sides (SPEC §7).
  - #4: whole-word cases that must pass.
- **#5 deferred to a later SPEC follow-up.** A missed form is still behind the fixed templates. The "فخذ" false positive makes a reply malformed, so it is retried, never shown wrongly.
- **#6 accepted** in the round brief: one shared clitic constant.
- **Rule adjusted while proving the contract:** the first draft of #1 required every schema key, and that broke `test_b4_providers.py::test_label_json_parses_into_reading`, whose strength has no `release`. The rule is "no key beyond the schema's"; a missing `release` still defaults to `unknown`. A reference build then passes the whole suite (707).

## Round 2: SUPERVISOR: APPROVE
Every accepted round-1 finding is fixed; the supervisor reran its own failing inputs on the round-2 tree:
- **#1:** the "double the dose if dizzy" salt label is now a retryable malformed reply and never reaches the brief.
- **#2:** Panadol (paracetamol + caffeine) and Gelocatil give `same_ingredient paracetamol` again.
- **#3:** the scalar-`inn` salts show as "Ingredient metoprolol tartrate" against "Ingredient metoprolol succinate".
- **#4:** `يتناول`, `المتناول`, `تناولت` and `أخذ` pass, the clitic and mark forms are still caught, and both boundary mutants are now caught.

Regression checks:
- Both live label replies in `tests/fixtures/spark_labels_live_2026-10-27.json` still parse, and the b4, b7, b8, b9, b11 and b16 contracts pass.
- The shared `ARABIC_CLITICS` is the same string as the three old copies.
- Removing the six Arabic words from the raw-text check: 990 fuzzed strings, nothing newly rejected. The only strings no longer caught are not whole words ("مَتناول", "within reach"), so they were false positives under SPEC §2.

1. **minor** `anamnesis/brief_html.py`: the new Ingredient rows are escaped, but nothing tests it (the unescaped mutant passes all 707).
2. **minor** Nothing tests `dir="auto"` on the Ingredient rows (that mutant passes too).

Mutations: 11 of 13 caught; the two above survived.

**CEO triage:** both accepted, none blocking. The code is right today, so both go into the next batch's contract, with the batch 19 follow-ups.
