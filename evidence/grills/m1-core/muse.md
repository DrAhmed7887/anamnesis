muse: workspace root: <repo>/.muse/worktrees/20261027-9154 (cwd default)
muse: Agent delegation: auto unavailable: workspace is untrusted.
Core verdict: the reconcile path can report "agree" when nothing was compared, and it cannot tell an immediate-release tablet from a modified-release one. Ranked findings below. All verified by code trace; I could not execute probes (sandbox blocks the package cache and the system Python is 3.9 vs the project's 3.12+ syntax), so each failure case is traced, not run.

## Critical

**1. `reconcile.py:110-111` (SPEC §3 rule 7) — absence of evidence reported as `match`.**
Failure: claim `Concor` with no strength/intake vs readable pack `Concor 5 mg` with `strength=None` (Spark failed to parse the dose) → falls through to `else: kind = D.MATCH`, `needs_clinician_review=False`, note "details agree". Same when only one side has a strength. A missed dose extraction becomes false reassurance.
Fix: change rule 7 so resolved-but-incomparable pairs never return `match`. Minimal: `else: kind = D.STRENGTH_MISMATCH` in [reconcile.py](anamnesis/core/reconcile.py:110), amend SPEC §3 rule 7 to "names resolve but no strength/intake comparison possible → `strength_mismatch`", and add a contract test for both sub-cases.

**2. No salt / formulation / modified-release model — [catalogue.yaml](anamnesis/core/catalogue.yaml:1), [medication.py](anamnesis/schema/medication.py:49) `Strength`, [reconcile.py](anamnesis/core/reconcile.py:43) `_strength_type`.**
Failure: patient says metoprolol tartrate IR 100 mg, pack is Beloc-Zok (metoprolol succinate ER) 100 mg → INN sets both `{metoprolol}`, amounts equal → `match`. These are not interchangeable. Same for Glucophage vs Glucophage XR, amlodipine besilate vs mesilate. `StrengthPer` (`tablet/capsule/ml/dose`) cannot express release profile.
Fix: add `salt: str | None` and `form: Literal["immediate","prolonged","enteric","other"] | None` (or equivalent enum) to `Strength`/`IngredientAmount`, extend catalogue entries with salt/form, and in `_strength_type` return `STRENGTH_MISMATCH` (or a new `formulation_mismatch`) when they differ or when one side is unknown and the other is prolonged/enteric.

**3. Half-tablet logic ignores dosage form; `regimen` never read — [reconcile.py](anamnesis/core/reconcile.py:61) `_intake_type`, [reconcile.py](anamnesis/core/reconcile.py:103) intake branch.**
Failure: intake 50 mg vs pack capsule 100 mg → `r=0.5` → `intake_differs_from_unit_strength` ("possibly fine, ask"). Capsules, ER and enteric tablets must not be split. Separately, `DoseRegimen.units_per_intake=0.5` is never consulted, so "half a tablet twice daily" expressed via regimen with no `intake_amount` falls to rule 7 → `match`.
Fix: pass `pack.per`/`form` into `_intake_type`; if `per != "tablet"` or form is prolonged/enteric/coated, return `STRENGTH_MISMATCH` for `r=0.5` instead of `intake_differs`. Add a branch that derives the ratio from `regimen.units_per_intake` when `intake_amount` is absent, under the same splittability gate. Add a catalogue `splittable` flag for the 8 entries.

## High

**4. Advice guardrail unenforced and regex-weak — [guardrails.py](anamnesis/core/guardrails.py:47), [findings.py](anamnesis/schema/findings.py:34), [reconcile.py](anamnesis/core/reconcile.py:74).**
Failure: `Finding(clinician_note="Split the tablet and continue half daily")` validates — `clinician_note` is free `str`, `patient_question_id` is free `str|None`, and `assert_no_advice` is never called outside tests. The regex misses `split, halve, half, continue, keep taking, safe, fine, maintain, stay on`, and covers ~5 words for the promised 25 transcribe languages.
Fix: call `assert_no_advice` in a `Finding` `mode="after"` validator and in `_finding`; constrain `clinician_note` to the `TEMPLATES` values and `patient_question_id` to `PATIENT_QUESTIONS` keys (Literal types); expand the blocklist (`split, halve, half, continue, keep, safe, fine, ok to, maintain, stay on, carry on`, …) plus per-language dosing verbs, with adversarial tests per language family.

**5. Greedy first-overlap pairing mis-pairs combinations — [reconcile.py](anamnesis/core/reconcile.py:121).**
Failure: claims `[Panadol, Panadol Extra]`, packs `[Panadol Extra, Panadol]` (photo order) → `c1` grabs `o1` on `{paracetamol}` overlap → two `ingredient_mismatch` findings instead of two matches. Order-dependent false alarms; same for Augmentin vs amoxicillin-only.
Fix: two-pass pairing — exact INN-set matches first, then overlap, breaking ties by strength equality; or score candidates (exact > subset > overlap) and take the best. Add a swapped-order contract test.

**6. INN sets ignore strength contents; explicit `inn` unnormalised; key-difference mistyped — [reconcile.py](anamnesis/core/reconcile.py:19), [reconcile.py](anamnesis/core/reconcile.py:50).**
Failure A: pack with explicit `inn="paracetamol"` but strength paracetamol+caffeine vs paracetamol-only claim → singleton sets match → `_strength_type` sees different keys → `strength_mismatch`, understating a missing active ingredient (should be `ingredient_mismatch`). Failure B: `inn=" bisoprolol"` (whitespace), `"metoprolol succinate"`, or `acetaminophen` vs `paracetamol` → false `ingredient_mismatch` (no strip/salt-strip/synonym map).
Fix: derive comparison INN sets from `strength.ingredients` when present (unioned with `inn`/catalogue); normalise `inn` (strip, casefold, salt-suffix strip, synonym table incl. paracetamol=acetaminophen); in `_strength_type`, return `INGREDIENT_MISMATCH` when ingredient key sets differ.

**7. Catalogue substring/longest-wins drops drugs; hyphen mismatch; country fallback — [catalogue.py](anamnesis/core/catalogue.py:36).**
Failure A: `name_text="I take Concor and Panadol Extra daily"` (raw transcribe sentence) → longest match wins → Panadol Extra only; Concor silently dropped. Failure B: transcribed `"Beloc Zok"` (space) vs brand `"Beloc-Zok"` (hyphen preserved by `_normalise`) → `None` → false `unresolved_name`. Failure C: same brand, different INNs per country → "preference never filter" returns the wrong country's entry as a confident resolve.
Fix: normalise `-`/`/` to spaces on both sides; make `resolve` return all matches or `None` on multi-brand text and require batch 3 to segment one claim per drug before resolving; make country a filter when the brand exists under the requested country (else resolve globally but flag review). Add tests for sentence input, space/hyphen variants, and a country-collision entry.

**8. Liquids/concentrations unrepresentable; `_intake_type` ignores `per` — [medication.py](anamnesis/schema/medication.py:12) `Unit`/`StrengthPer`, [reconcile.py](anamnesis/core/reconcile.py:61).**
Failure: syrup "amoxicillin 250 mg/5 ml" has no faithful encoding (`per="ml"` with 250 mg — per 1 ml? per 5 ml?). Intake 250 mg vs that pack → ratio 1 → false `match` ignoring volume; intake 5 ml (`unit="ml"`) vs 250 mg strength → `strength_mismatch` false alarm. `%`, drops, patches (mcg/h), inhaler doses are outside the closed `Unit` enum, forcing batch 3 to mis-encode or crash.
Fix: add a concentration denominator (e.g. `volume_ml: Decimal` on `Strength` when `per="ml"`, or `amount_per: IngredientAmount + per_volume`), gate `_intake_type` on compatible `per`/`unit` (ml packs need volume-aware comparison, else `strength_mismatch`), and extend `Unit`/`StrengthPer` (or add `other` + raw-text field) before batch 3.

## Medium

**9. Duplicate INNs in one `Strength` collapse silently — [medication.py](anamnesis/schema/medication.py:57), [reconcile.py](anamnesis/core/reconcile.py:46).**
Failure: claim strength `[paracetamol 500, paracetamol 500]` vs pack `[paracetamol 500]` → dict comprehension keeps the last duplicate → dicts equal → `match`, hiding a 2× discrepancy.
Fix: `model_validator` on `Strength` rejecting duplicate casefolded INNs (or an explicit sum rule), plus a test.

**10. Schema gaps that will hurt batch 3 — [evidence.py](anamnesis/schema/evidence.py:10), [medication.py](anamnesis/schema/medication.py:82), SPEC §5.**
Failure: nowhere to put the §5 call log (`model_id, latency_ms, input/output_tokens, cost_usd`); `transcript` allows `""`, `speaker` allows `""`, `lang_hint` is free text (no 25-language/BCP47 validation, though `languageBias` needs language names); `ImageRegion` rejects float boxes a segmenter may emit and has no rank field for "top-3 regions per photo"; no per-field grounding (which region supports which strength); `audio_evidence`/`visual_evidence` ID lists have no referential check, so dangling `t_foo`/`r_foo` validate.
Fix: add a `ProviderCall` log model; tighten `AudioTurn` (`transcript min_length=1` or explicit empty-flag, `speaker` NonEmpty, `lang_hint` 25-language enum/pattern); accept and round float boxes or coerce explicitly; add per-field provenance + confidence slots on claim/pack; validate evidence IDs against supplied turn/region ID sets in `reconcile_all` (or a dedicated linker).

**11. Guardrail tests are circular — [test_b2_reconcile.py](tests/contract/test_b2_reconcile.py:166).**
Failure: `test_every_type_has_a_safe_template` runs the templates past the same regex they were written to avoid, and `test_advice_is_caught` feeds the regex its own keywords. Both pass while "Continue your tablets" and "Split the tablet" sail through, and nothing tests that `Finding`/`reconcile` enforce anything at runtime.
Fix: add miss-case phrases (`continue, split, halve, safe, keep taking`, one per supported language family) that must raise, and a test that `Finding` with advice text and `_finding` output are validated, not just the static dicts.

**12. Pairing/units/strictness tests don't pin the behavior — [test_b2_reconcile.py](tests/contract/test_b2_reconcile.py:121), [test_b1_schemas.py](tests/contract/test_b1_schemas.py:200).**
Failure: `test_reconcile_all_pairs_by_ingredient` uses disjoint INNs (never exercises overlap/greedy order); `intake_half` bundles a `regimen` the code ignores, so the "dose vs frequency" title proves nothing; `test_units_are_normalized` covers only g→mg (not mcg/iu/ml/per); `test_extra_fields_forbidden` covers 3 of 8 models; `test_json_schemas_are_not_recursive` is a substring check.
Fix: add swapped-order overlap pairing test, a regimen-ignored regression test (or implement regimen use), mcg/iu/ml/per unit matrix, parametrize extra-forbid over all models, and validate tool-call schemas against the Spark limits (depth/properties) instead of the substring check.

No files were modified.
