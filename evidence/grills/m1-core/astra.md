### 1. Critical — Missing comparison data becomes an affirmative `match`

**Location:** SPEC §3, decision rule 7; `reconcile_pair` final `else`.

**Failure case:** The claim says Concor 5 mg; the readable pack says “Concor 10 mg,” but the label adapter omits `strength`. Both names resolve, so the result is `match`, with no clinician review. An intake-only claim against a combination pack also falls through to `match`.

**Exact fix:** Amend the closed enum and SPEC to introduce `insufficient_information`, requiring review. Replace rule 7 with that outcome. Permit `match` only after an explicit, complete comparison of the relevant identity, formulation and amounts. Do not silently derive a strength from label text inside reconciliation; request grounded extraction or abstain.

### 2. Critical — Salts and release forms disappear from medication identity

**Location:** SPEC §2 medication identity and §3 rules 2–5; `CatalogueEntry`, `catalogue.yaml`, `_claim_inns`, `_pack_inns`.

**Failure case:** “Glucophage 500 mg” and “Glucophage XR 500 mg,” both extracted as metformin 500 mg/tablet, return `match`. Release characteristics are neither represented nor compared. Conversely, explicit `inn="bisoprolol fumarate"` versus catalogue `bisoprolol` produces an ingredient mismatch even when the label amounts use the same active-moiety basis.

**Exact fix:** Represent canonical active moiety, salt, release form, dosage form, and strength-expression basis separately in claims, observations and catalogue products. Compare known formulation differences before amount equality; add a review-required `formulation_mismatch`. Use curated salt aliases and explicit labelled equivalence mappings—not generic salt stripping or molecular-weight guesses. Unknown material formulation or strength basis must prevent a confirmed match.

### 3. Critical — Conflicting ingredient representations and duplicate ingredients can produce `match`

**Location:** Schema rules for `PatientClaim.inn`, `PackObservation.inn`, `Strength.ingredients`; `_strength_type` dictionary construction.

**Failure case:** A Concor claim contains bisoprolol amounts `[10 mg, 5 mg]`; the pack contains `[5 mg]`. Both models validate. Dictionary construction discards the first claim amount and returns `match`.

Separately, both records can say `inn="bisoprolol"` while both strengths contain only amlodipine 5 mg; reconciliation again returns `match`. For combinations, the scalar `inn` cannot represent the ingredient set: an adapter supplying only “amoxicillin” overrides the Augmentin identity and can create false alarms or hide an omitted component.

**Exact fix:** Replace scalar identity with a structured canonical ingredient list. Reject duplicate canonical ingredient IDs in every strength. Validate consistency between resolved product identity and strength ingredients; contradictions must become extraction conflicts requiring review, not silent precedence. Explicit adapter-supplied names must undergo canonical resolution rather than automatically count as “found.” Reject or abstain on incomplete combination composition.

### 4. High — Equal strengths suppress contradictory intake and regimen information

**Location:** SPEC §3 rules 5–6; `reconcile_pair` strength branch; `DoseRegimen`.

**Failure case:** Claim: tablet strength 5 mg, intake 10 mg, regimen one tablet per intake. Pack: 5 mg/tablet. Rule 5 returns `match`; the intake and regimen are never examined. Even without the regimen contradiction, this reports “details agree” where the intake-only version would produce `intake_differs_from_unit_strength`.

**Exact fix:** Evaluate unit-strength agreement, intake-versus-unit amount, and stated regimen consistency independently. Return multiple findings, or define a deterministic aggregation in which any conflict or unresolved comparison prevents an overall `match`. Use `units_per_intake × pack unit strength` only when the intake unit and formulation are known. Keep questions descriptive; do not interpret arithmetic as permission to split or change intake.

### 5. High — Intake comparison ignores denominators and treats liquids or capsules as tablet multiples

**Location:** SPEC §3 rule 6; `_intake_type`; schema rules for `Strength.per` and `DoseRegimen.units_per_intake`.

**Failure case:** A claim gives metformin intake 5 mg; a pack strength is 5 mg/ml. `_intake_type` returns `match`, although an amount and a concentration are not equivalent. Intake 10 mg returns the same classification used for two tablets.

The schema also cannot directly preserve “125 mg per 5 ml”; an adapter must silently normalize it or misrepresent it as 125 mg/ml.

**Exact fix:** Model strength denominators as quantity plus unit, and give reported intake quantities explicit units. Preserve the labelled concentration as evidence alongside any normalized value. Perform dimensional checks before arithmetic. Require a reported volume to compare a mass intake against a concentration. Restrict tablet-multiple classification to applicable dosage forms, without asserting that the product is splittable. In SPEC, remove “whole-tablet multiple or half” from the definition of **stated-strength** mismatch; that exception belongs only to intake comparisons.

### 6. High — Substring resolution silently accepts unknown products and conflicting names

**Location:** Catalogue resolution rule: `Catalogue._best` and `Catalogue.resolve`.

**Failure case:** “Panadol Night” resolves to the simpler Panadol entry because `Panadol` is a bounded substring. If extraction supplies only paracetamol 500 mg, it can match ordinary Panadol despite the unrecognized product qualifier. Text containing multiple medicine names selects whichever matching name is longest rather than reporting ambiguity.

Country handling can also select a shorter local alias before considering a more specific nonlocal product.

**Exact fix:** Resolve against curated product aliases, allowing only recognized surrounding strength, packaging and dosage-form tokens. Treat unrecognized identity-bearing suffixes and multiple distinct product candidates as unresolved or ambiguous. Use country as an explicit resolution constraint, with separately recorded fallback policy—not a silent preference that changes specificity. Preserve all candidates and abstain when identity is not unique.

### 7. High — Greedy overlap pairing manufactures disagreements and depends on photo order

**Location:** SPEC §3 `reconcile_all` pairing rule.

**Failure case:** Claims are Concor 5 mg and Concor 10 mg; packs arrive in the reverse order. The first-overlap algorithm pairs 5 with 10 and 10 with 5, producing two false strength alarms. Likewise, a Panadol claim can consume Panadol Extra before an exact Panadol pack, generating avoidable ingredient mismatches.

An unreadable pack carrying a guessed `inn` can consume a claim before a readable matching pack.

**Exact fix:** Build candidate associations across the entire intake. Exclude unreadable identity guesses from pairing. Prefer grounded product/formulation identity and exact ingredient sets over partial overlap; use strength as an association signal only where it does not conceal genuine discrepancies. Require a unique supported assignment. Otherwise emit a review-required `ambiguous_pairing` with candidate links rather than selecting by input order.

### 8. High — “Fixed templates only” is not enforced at the schema or output boundary

**Location:** SPEC §3 text rule; `Finding.clinician_note`, `Finding.patient_question_id`; `assert_no_advice`.

**Failure case:** A valid `Finding` can contain `clinician_note="Continue your current dose."` and an arbitrary question ID. The advice regex does not catch that sentence, and reconciliation does not invoke the regex anyway. A future provider-generated finding can therefore pass Pydantic validation while violating the central safety contract.

**Exact fix:** Do not accept rendered clinical text from providers. Accept only validated structured results and derive note/question text server-side from immutable, reviewed template IDs. Validate the question-to-finding mapping and reject unknown IDs. If rendered text remains in serialized findings, require exact equality with the canonical rendering. Treat regex scanning as supplementary testing, not as the safety boundary; reviewed translations need the same allowlist discipline.

### 9. High — Evidence links can be nonexistent, contradictory or ambiguous

**Location:** SPEC opening provenance contract; `Finding.validate_evidence_sides`; evidence-reference schema rules.

**Failure case:** A two-sided match validates with `claim_id=None`, `observation_id=None`, and invented evidence IDs. A one-sided finding can retain both object IDs. Claims can reference turns that do not exist, and regions can reference an unregistered image hash. Nothing checks that finding evidence actually belongs to its linked claim and observation.

**Exact fix:** Add a validated intake envelope containing source manifests, evidence, claims, observations and findings. Enforce unique IDs, reference existence, finding-side ID/evidence equivalence, and evidence membership against the linked records. Link turns to an audio source recording; bind image hashes to actual source dimensions. Validate the complete envelope before reconciliation and before brief rendering.

### 10. High — Batch 3 has no typed boundary for coordinate, timing and extraction provenance

**Location:** SPEC §1, §5 and batch-3 adapter contract; `AudioTurn`, `ImageRegion`, `PackObservation`.

**Failure case:** SAM coordinates measured on a resized image can still satisfy every `ImageRegion` bound when mistakenly labelled as source pixels. A Voice Transcribe adapter can similarly pass plausible integer times expressed in the wrong unit. A Muse observation can cite a whole region without identifying which grounded reading supports its extracted strength. Bounds and nonempty IDs do not establish correct conversion or extraction.

**Exact fix:** Define separate provider-result and normalized-domain envelopes before implementing adapters. Require source/request IDs, timing units, coordinate convention, source and inference dimensions, crop/resize transforms, and provider call IDs. Keep turn-level timing—do not manufacture word timestamps. Record field-level evidence references for extracted identity, strength and status, plus extraction uncertainty. Add a typed call record for the §5 model, latency, token and cost fields, linked to each result. Test normalization using recorded offline fixtures.

### 11. Medium — Missing regimen information is represented as a negative fact

**Location:** `DoseRegimen.as_needed` default and medication extraction rules.

**Failure case:** “Concor, half a tablet” becomes `DoseRegimen(units_per_intake=0.5)` with `as_needed=False`, despite no statement about scheduled versus as-needed use. Batch 3 can then promote an adapter default into a purported patient fact.

**Exact fix:** Make `as_needed` nullable or use an explicit `scheduled/as_needed/unknown` enum. Default to unknown. Require evidence for non-unknown values and apply the same absent-versus-negative distinction to other extracted categorical facts. Brief rendering must omit unknown facts or identify them as unknown.

### 12. Medium — Several tests verify implementation agreement, not the promised safety properties

**Location:** `tests/contract/test_b1_schemas.py` and `test_b2_reconcile.py`.

**Failure cases:**
- The template test checks text against the same limited blacklist; it does not prove advice exclusion.
- `test_every_type_has_a_safe_template_and_non_match_types_have_a_question` never checks its promised question coverage directly.
- `test_json_schemas_are_not_recursive` searches only for a root-model reference; cycles entirely within `$defs` can escape it.
- The determinism test repeats one call with identical arguments; it says nothing about order-induced false pairing.
- Finding round-trip tests accept unrestricted notes and an unknown `"q_strength"` ID, entrenching the output-boundary gap.
- Reconciliation fixtures never supply contradictory `strength`, `intake_amount` and regimen together.

**Exact fix:** Have the reviewer revise and freeze the next contract before implementation; do not have the builder edit the protected tests. Add explicit expected-result regressions for findings 1–11, permutation tests for uniquely identifiable pack assignments, malformed-reference and contradictory-extraction tests, and complete template/question mapping assertions. Traverse JSON Schema references to detect cycles. Use independent reviewed output expectations and mutation tests—for example, deleting the fallback abstention or ingredient-uniqueness check must fail the suite.
