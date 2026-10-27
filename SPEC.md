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
| `IngredientAmount` | `inn`, `amount`, `unit` | `amount > 0` (Decimal). `unit` ∈ `mg, mcg, g, ml, iu`. INNs are compared in canonical form (trimmed, casefolded, synonyms such as acetaminophen → paracetamol) |
| `Strength` | `ingredients: list[IngredientAmount]`, `per`, `release` | ≥1 ingredient (combinations: Augmentin 875/125) and **no duplicate canonical INNs**. `per` ∈ `tablet, capsule, ml, dose`. `release` ∈ `immediate, modified, unknown` (default `unknown`) |
| `DoseRegimen` | `units_per_intake?`, `intakes_per_day?`, `as_needed?` | Decimals > 0 when present (0.5 means half a tablet). `as_needed` defaults to `None`: unknown, not "no" |
| `PatientClaim` (from audio) | `claim_id`, `name_text`, `inn?`, `strength?`, `intake_amount?`, `regimen?`, `status`, `audio_evidence` | `audio_evidence` has ≥1 turn_id. `status` ∈ `active, discontinued, unknown`. `intake_amount` (what they take per intake) is kept separate from `strength` (what the tablet contains) |
| `PackObservation` (from image) | `observation_id`, `label_text?`, `inn?`, `strength?`, `readability`, `country?`, `visual_evidence` | `visual_evidence` has ≥1 region_id. `readability` ∈ `readable, partial, unreadable`. `readable` requires `label_text` |

`AudioTurn.transcript` and `speaker` are non-empty when present.

## 3. Findings (closed enum, lowercase)
| `DiscrepancyType` | Needs both sides | Meaning |
|---|---|---|
| `match` | yes | Same identity, and every comparison that could be made agreed |
| `strength_mismatch` | yes | Stated strength ≠ pack strength, or an intake that the pack can't give |
| `intake_differs_from_unit_strength` | yes | Intake is 0.5× (only for a tablet the catalogue marks splittable), 2×, 3× or 4× the unit strength. Possibly fine: ask |
| `ingredient_mismatch` | yes | Different canonical INN sets (Panadol vs Panadol Extra with caffeine) |
| `ratio_mismatch` | yes | Same combination, different ratio (Augmentin 875/125 vs 500/125) |
| `formulation_mismatch` | yes | Both release forms are known and differ (immediate vs modified) |
| `insufficient_information` | yes | Names agree, but the evidence can't confirm a match: no comparable amounts, release unknown against modified, unknown splittability, liquids, or contradictory extraction |
| `discontinued_but_present` | yes | Patient says they stopped; the pack is in the photo |
| `unreadable_source` | visual required | Label is unreadable or partial: abstain, never guess from shape or colour |
| `unresolved_name` | at least one side | Name not found in the catalogue, or the text names 2+ products |
| `missing_modality` | exactly one side | Only audio or only image evidence exists |

`Finding`: `finding_id`, `type`, `claim_id?`, `observation_id?`, `audio_evidence`, `visual_evidence`, `needs_clinician_review`, `clinician_note`, `patient_question_id?`.
- Every type except `match` requires `needs_clinician_review = true`.
- `claim_id` is set exactly when `audio_evidence` is non-empty, and `observation_id` exactly when `visual_evidence` is non-empty.
- **Text is enforced, not just advised:** `clinician_note` must equal `TEMPLATES[type]`, and `patient_question_id` must equal `QUESTION_FOR[type]`. Both tables live in `anamnesis/schema/templates.py`. The blocklist (`assert_no_advice`) is a regression check, not the safety boundary.

### Identity of one side
- **Identity set:** the canonical INNs of `strength.ingredients` if a strength exists. Otherwise `{inn}`, otherwise the INNs of the catalogue entry that `name_text` (or `label_text`) resolves to.
- If a side has both a strength and a resolvable name, and their INN sets differ, that is an extraction conflict and the result is `insufficient_information`.
- **Brand-implied facts** (`release`, `splittable`) come from the catalogue only when the text matched a **brand** name, never an INN. "Beloc-Zok" implies modified release; "metoprolol" implies nothing.

### Decision order for one claim and one pack (`reconcile_pair`)
The first rule that applies wins.
1. Pack `partial` or `unreadable` → `unreadable_source`.
2. Either identity set can't be built → `unresolved_name`.
3. Extraction conflict on either side → `insufficient_information`.
4. The identity sets differ → `ingredient_mismatch`.
5. The claim's status is `discontinued` → `discontinued_but_present`.
6. Both sides have a strength: compare amounts in mg (g ×1000, mcg ×0.001; `ml` and `iu` only against the same unit). Unequal → `strength_mismatch` or `ratio_mismatch`, as in v1.
7. The claim has an `intake_amount` (also when 6 found equal strengths): compare it with a single-ingredient pack strength.
   - `per` ∉ {tablet, capsule} → `insufficient_information`.
   - Compute r = intake / unit strength. r = 1 → continue.
   - r ∈ {2, 3, 4} → `intake_differs_from_unit_strength`.
   - r = 0.5 on a tablet. Splittability is per product, because some scored ER tablets such as Beloc-Zok may be halved: `splittable: true` → `intake_differs_from_unit_strength`; `false`, or a capsule → `strength_mismatch`; unknown → `insufficient_information`.
   - Otherwise → `strength_mismatch`.
8. No amount comparison was possible on either rule 6 or rule 7 → `insufficient_information`.
9. **Formulation gate before `match`.** Release forms (explicit, otherwise implied by the brand):
   - both known and different → `formulation_mismatch`
   - one `modified`, the other `unknown` → `insufficient_information`
10. Otherwise → `match`.

### Pairing (`reconcile_all`)
- Only readable packs can pair. Candidate pairs have overlapping identity sets.
- Score each candidate: 3 = same identity and equal strength, 2 = same identity, 1 = overlap.
- Take candidates greedily by score, then claim index, then pack index. The **set** of findings must not depend on the order of claims or packs.
- Leftovers:
  - an unreadable pack → `unreadable_source`
  - an unresolvable name → `unresolved_name`
  - otherwise → `missing_modality`

### Catalogue resolution
- `-` and `/` count as spaces, matching is on whole words, and the longest match wins only over names contained inside it. Text that names 2+ different products → `None`.
- The country is a preference, never a filter.
- Entries carry `release` and `splittable` (`true`, `false` or `null`). All entries are synthetic.

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
