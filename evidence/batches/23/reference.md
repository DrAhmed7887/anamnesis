# Batch 23: the CEO's reference build, 28 Oct

- **Contract:** `test_b23_timeline.py` (part 1), `test_b23_m5_fixes.py` (part 2) and `test_b23_coverage.py` (parts 3–4): 56 tests.
- **On the code before the batch:**
  - part 1 fails at import, because the templates don't exist yet;
  - part 2: 9 of 13 fail; the 4 that pass are the #5 pin and the standard models;
  - parts 3–4: 17 of 23 fail; the 6 that pass are the earlier-concept cases and the strengths that must be kept.
- **Reference build** (a scratch copy with all nine items done by the CEO): **1178 passed**, ruff clean.
- **Older tests that counted two SAM concepts:** `test_b15_m3_blockers.py::test_the_report_counts_spend_of_a_failed_call` (contract) now counts three, updated by the CEO in this lock commit. `tests/unit/test_agent_extra.py::test_provider_error_becomes_a_step_without_prose` (unit) is listed in the brief for Muse to update.
- **One mutant per part**, each applied alone to the reference, is caught by the contract:
  - a failed call's cost recorded as 0: 1 failure;
  - `package` dropped from the concepts: 2 failures;
  - the volume rule weakened to volumes over 5 ml: 15 failures;
  - `ProviderTrace` back to the exact `-contributor` suffix: 4 failures.
- **The #5 pin:** an unstated units count of "two", "2" or «اتنين» gives `intake_differs_from_unit_strength` on today's code, never `match`, as SPEC §2 Known limits says. My first version of that test failed only because its regimen lacked the `as_needed` key.

## Round 2 (28 Oct): the supervisor's #1–#6 and the Gemini check's #3, #4, #6, pinned in `tests/contract/test_b23_round2.py`
- **On Muse's round 1:** 46 of the 57 new tests fail. Each one reproduces a finding: 42 syrup wordings, the Arabic `ملجم` combination tablet, the four-photo budget case, and the two `add_photo` concept tests. The 11 that pass are kept behaviour: the English decimal, six labels that keep their strength, an explicit budget, and the step sum after `add_photo`. Muse's round 1 already keeps those step fields; the test pins them.
- **Reference build** (round 1 plus: the full volume rule, `SAM_CONCEPTS`, and the budget that covers every call): **1248 passed**. No older test depended on the old defaults of 12 and 8.
- **Mutants,** each applied alone to the reference, all caught:
  - the budget back to 12: 1 failure;
  - the volume-first form removed: 6;
  - the `ملجم` guard removed: 1;
  - `add_photo` back to two concepts: 2;
  - `٫` not translated: 9.

## Round 3 (28 Oct): the supervisor's round 2 #2–#3 and the Gemini check's round 2 #4–#6, pinned in `tests/contract/test_b23_round3.py`
- **On Muse's round 2:** 41 of the 53 new tests fail: 33 syrup wordings, all 7 packs that aren't syrups, and the timeline's `colspan`. The 12 that pass are wordings round 2 already drops.
- **The CEO's own fixes (scripts, not the build):** `intake_live.py` uses the loop's budget formula for `run_intake` and for its `SessionGuard` (f5a9326, ccebce0; supervisor round 2 #1). SPEC §4 Budget now says every caller that spends wraps the providers in a `SessionGuard` (#4).
- **Reference build** (round 2 plus the round 3 volume forms and the `colspan`): all 153 batch 23 contract tests pass, and the full suite gives **1322 passed**. Muse's round 2 unit case "Every 5 cc has ibuprofen 100 mg" led the CEO to add `has` to the contains words, which only drops more.
- **Mutants,** each alone, all caught: the water skip removed (3 failures); the container check removed (1); the contains-word requirement removed (4); `cada`/`chaque` removed (6); the `colspan` removed (1).

## Round 4 (28 Oct): one clause rule, pinned in `tests/contract/test_b23_round4.py`
- **On Muse's round 3:** 85 of the 87 new tests fail: every wording the supervisor's round 3 found, the containers read per ml, and 5 of the 7 kept lines. The 2 that pass are per-ml strengths printed per 1 ml.
- **Reference build** (round 3 plus the clause rule in `spark.py`): all **1100** contract tests pass, 253 of them batch 23's. Every round 1–3 case still holds under the new rule.
  - 14 of Muse's own round 2–3 unit tests fail. They call the old helper, or pin pattern behaviour the clause rule changes on purpose: the container exemption, "peach", "within", and kept lines with a dose volume in another clause and no tablet word.
- **Mutants,** each alone against all four batch 23 volume contracts, all caught:
  - the water exemption removed: 7 failures;
  - the per-1-ml exemption removed: 6;
  - the tablet-word rule removed: 2;
  - the not-dissolving exclusion removed: 6;
  - the clause split removed: 4.

## Round 5 (28 Oct): a strength printed in its own unit, pinned in `tests/contract/test_b23_round5.py`
- **The design change:** rounds 1–4 asked where a volume doesn't count, and each answer was a place to hide one. Round 5 asks whether each amount is printed in the reading's own unit (`250 mg/ml`, `100 mcg per dose`, `5 mg tablets`) and not also beside a volume. A missing wording now loses a strength instead of keeping a wrong one. The clauses are gone.
- **On Muse's round 4:** 75 of the 104 first-draft tests fail: every supervisor round 4 input, in both directions.
- **Reference build** (round 4 plus the round 5 rule in `spark.py`): all **1220** contract tests pass.
  - **Two earlier keeps now fail closed, on purpose,** and moved to the drops with a note: "Vitamin C 1000 mg per 200 ml of water" (round 4), and "Panadol 500 mg\n24 tablets, 100 ml bottle" (round 1).
  - **9 of Muse's round 3–4 unit cases fail.** They pin behaviour round 5 changes on purpose. Six are "Syrup 250 mg in 5 ml of water" read per ml, now dropped; three are tablet and capsule lines. The brief lists them.
- **Mutants,** each applied alone to the reference and run against every contract test. All 16 were caught:
  - the water exemption also for per ml;
  - no always-counts after `/` or `per`;
  - no spoons;
  - no refusal, the refusal only before the volume, the refusal across sentences;
  - the tablet print across a line break, or across a sentence. The sentence mutant first survived once the refusal also looked later in the sentence. One drop now pins it ("Paracetamol syrup 250 mg. Tablets also available. Dose: 5 ml"), added in a second lock while Muse was building. The brief already gave Muse the rule.
  - brackets not skipped;
  - no `ال` on water. This mutant first survived, because the Arabic keeps also printed «قرص». Two keeps without a tablet print were added.
  - no `U`, no `unidades`;
  - no per-dose print;
  - no water before brackets;
  - no Arabic tablet words;
  - a four-word window instead of the lead-in words.
