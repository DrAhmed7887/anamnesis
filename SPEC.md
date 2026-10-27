# Anamnesis contract (v1, 27 Oct 2026)

A pre-visit intake agent. It takes the patient's voice note (any of 25 languages) and photos of their medicine packs, and gives the clinician a one-page brief. Every fact in the brief links to the audio turn and the image region it came from. **It reports where sources disagree. It never gives medical advice.** All data is synthetic.

## 1. Evidence (independent IDs, no forced chain)
| Model | Fields | Rules |
|---|---|---|
| `AudioTurn` | `turn_id`, `start_ms`, `end_ms`, `transcript`, `speaker?`, `lang_hint?` | `end_ms > start_ms ≥ 0`. Turn-level timing only (Voice Transcribe has no word timestamps) |
| `ImageRegion` | `region_id`, `image_sha256`, `object_id`, `x1,y1,x2,y2`, `frame_w`, `frame_h`, `confidence?` | Source pixels, inclusive corners (SAM 3.1 format). `0 ≤ x1 ≤ x2 < frame_w`, same for y. `confidence` in [0,1]. Hash is 64 lowercase hex chars |

## 2. Medication facts
| Model | Fields | Rules |
|---|---|---|
| `IngredientAmount` | `inn`, `amount`, `unit` | `amount > 0` (Decimal). `unit` ∈ `mg, mcg, g, ml, iu` |
| `Strength` | `ingredients: list[IngredientAmount]`, `per` | ≥1 ingredient (combinations: Augmentin 875/125). `per` ∈ `tablet, capsule, ml, dose` |
| `DoseRegimen` | `units_per_intake?`, `intakes_per_day?`, `as_needed` | Decimals > 0 when present (0.5 means half a tablet) |
| `PatientClaim` (from audio) | `claim_id`, `name_text`, `inn?`, `strength?`, `intake_amount?`, `regimen?`, `status`, `audio_evidence` | `audio_evidence` has ≥1 turn_id. `status` ∈ `active, discontinued, unknown`. `intake_amount` (what they take per intake) is kept separate from `strength` (what the tablet contains) |
| `PackObservation` (from image) | `observation_id`, `label_text?`, `inn?`, `strength?`, `readability`, `country?`, `visual_evidence` | `visual_evidence` has ≥1 region_id. `readability` ∈ `readable, partial, unreadable`. `readable` requires `label_text` |

## 3. Findings (closed enum, lowercase)
| `DiscrepancyType` | Needs both sides | Meaning |
|---|---|---|
| `match` | yes | Same INN set and the same strength (or intake equals unit strength) |
| `strength_mismatch` | yes | Stated strength ≠ pack strength, and not a whole-tablet multiple or half |
| `intake_differs_from_unit_strength` | yes | Intake is 0.5×, 2×, 3× or 4× the pack strength. Possibly fine (split or several tablets): ask |
| `ingredient_mismatch` | yes | Different INN sets (for example Panadol vs Panadol Extra with caffeine) |
| `ratio_mismatch` | yes | Same combination, different ratio (Augmentin 875/125 vs 500/125) |
| `discontinued_but_present` | yes | Patient says they stopped; the pack is in the photo |
| `unreadable_source` | visual required | Label is unreadable or partial: abstain, never guess from shape or colour |
| `unresolved_name` | at least one side | Name not found in the catalogue |
| `missing_modality` | exactly one side | Only audio or only image evidence exists |

`Finding`: `finding_id`, `type`, `claim_id?`, `observation_id?`, `audio_evidence`, `visual_evidence`, `needs_clinician_review`, `clinician_note`, `patient_question_id?`.
- Every type except `match` requires `needs_clinician_review = true`.
- All text comes from fixed templates. There is no free-text dosing advice.

### Decision order for one claim and one pack (`reconcile_pair`)
The first rule that applies wins.
1. Pack `partial` or `unreadable` → `unreadable_source`.
2. Claim INNs (`inn`, otherwise the catalogue resolves `name_text`) or pack INNs (`inn`, otherwise the catalogue resolves `label_text`) cannot be found → `unresolved_name`.
3. The INN sets differ → `ingredient_mismatch`.
4. The claim's status is `discontinued` → `discontinued_but_present`.
5. Both sides have a strength. Amounts are converted to mg (g ×1000, mcg ×0.001); if `ml` or `iu` units differ, the result is `strength_mismatch`.
   - Equal → `match`.
   - Combinations with the same ratio but different amounts → `strength_mismatch`. A different ratio → `ratio_mismatch`.
   - Single ingredient, unequal → `strength_mismatch`.
6. The claim gives only an `intake_amount` and the pack has a single-ingredient strength. Compute r = intake / strength:
   - r = 1 → `match`
   - r ∈ {0.5, 2, 3, 4} → `intake_differs_from_unit_strength`
   - otherwise → `strength_mismatch`
7. Nothing to compare → `match`.

`reconcile_all` pairs each claim, in order, with the first unpaired pack whose INN set overlaps. Anything left over becomes a one-sided finding:
- An unreadable pack → `unreadable_source`.
- A name that can't be resolved → `unresolved_name`.
- Otherwise → `missing_modality`.

## 4. Agent loop bounds (Batch 4)
- One tool: `submit_reconciliation`. `tool_choice="auto"`.
- `max_grounding_iters = 2`, then abstain.
- Top-3 SAM regions per photo.
- Full JSON is collected, then validated with Pydantic. A provider call gets 1 retry and a 30 s timeout.

## 5. Every model call logs
`model_id`, `latency_ms`, `input_tokens`, `output_tokens`, `cost_usd` → `evidence/`. Hosted Meta models are the default. Open weights (Glimmer on Modal, Spark Open on Baseten) are for comparison only.

## 6. Build rules
- All models use `extra="forbid"`. No recursive JSON schemas.
- Tests pass offline, with no keys and no network.
- `tests/contract/` is written by the reviewer before each batch. A batch that edits it is rejected.
