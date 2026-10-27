# Anamnesis contract (v3.3, 27 Oct 2026)

A pre-visit intake agent. It takes the patient's voice note (Voice Transcribe supports 25 languages; **tested live so far only on synthetic text-to-speech notes: English, and Egyptian Arabic text with brand names in Latin or Arabic script, spoken by a macOS voice; no human speech yet**) and photos of their medicine packs, and gives the clinician a one-page brief. Every fact in the brief links to the audio turn and the image region it came from. **It reports where sources disagree. It never gives medical advice.** All data is synthetic.

## 1. Evidence (independent IDs, no forced chain)
| Model | Fields | Rules |
|---|---|---|
| `AudioTurn` | `turn_id`, `start_ms`, `end_ms`, `transcript`, `speaker?`, `lang_hint?` | `end_ms > start_ms ≥ 0`. Turn-level timing only (Voice Transcribe has no word timestamps) |
| `ImageRegion` | `region_id`, `image_sha256`, `object_id`, `x1,y1,x2,y2`, `frame_w`, `frame_h`, `confidence?` | Source pixels, inclusive corners (SAM 3.1 format). `0 ≤ x1 ≤ x2 < frame_w`, same for y. `confidence` in [0,1]. Hash is 64 lowercase hex chars |

## 2. Medication facts
| Model | Fields | Rules |
|---|---|---|
| `IngredientAmount` | `inn`, `salt?`, `amount`, `unit` | `amount > 0` (Decimal). `unit` ∈ `mg, mcg, g, ml, iu`. `inn` holds the **active moiety**: a curated alias table splits salt names (`"Metoprolol succinate"` → `inn="metoprolol"`, `salt="succinate"`). Synonyms are handled the same way (acetaminophen → paracetamol). An unknown suffix is never stripped |
| `Strength` | `ingredients: list[IngredientAmount]`, `per`, `release` | ≥1 ingredient (combinations: Augmentin 875/125) and **no duplicate canonical INNs**. `per` ∈ `tablet, capsule, ml, dose`. `release` ∈ `immediate, modified, unknown` (default `unknown`) |
| `DoseRegimen` | `units_per_intake?`, `intakes_per_day?`, `as_needed?` | Decimals > 0 when present (0.5 means half a tablet). `as_needed` defaults to `None`: unknown, not "no" |
| `PatientClaim` (from audio) | `claim_id`, `name_text`, `inn?`, `strength?`, `intake_amount?`, `regimen?`, `status`, `audio_evidence` | `audio_evidence` has ≥1 turn_id. `status` ∈ `active, discontinued, unknown`. `intake_amount` (what they take per intake) is kept separate from `strength` (what the tablet contains) |
| `PackObservation` (from image) | `observation_id`, `label_text?`, `inn?`, `strength?`, `readability`, `country?`, `visual_evidence` | `visual_evidence` has ≥1 region_id. `readability` ∈ `readable, partial, unreadable`. `readable` requires `label_text` |

`AudioTurn.transcript` and `speaker` are non-empty when present.

### Model replies (batch 16)
Every string a model writes is checked at the parser, before it can reach a report:
- **Numbers** arrive as strings. `"2.5"` and the decimal comma `"2,5"` both parse; a comma is a decimal mark only when 1–2 digits follow it (`"1,000"` is ambiguous and does not parse). A dot followed by exactly three digits with a non-zero whole part (`"1.000"`, `"2.500"`) is ambiguous the same way (a European thousands mark) and does not parse; `"0.125"` does. Ranges (`"1-2"`), words, zero and negatives don't parse.
- **An optional field that doesn't parse becomes null; it never fails the whole reply.** Optional fields: `regimen.units_per_intake`, `regimen.intakes_per_day`, `intake_amount` (null if its amount doesn't parse or it fails validation, e.g. an empty `inn`), `strength` (null if any of its ingredient amounts doesn't parse, or if it fails validation, e.g. an equivalence line read as two salts of one INN), and the label's `country`.
- **A dropped claim amount takes the other one with it.** When a claim's reply sent a `strength` or an `intake_amount` and either one is dropped, both become null, so the claim can't reach `match` on what is left (supervisor 16 #1: a combination whose caffeine amount didn't parse, or an intake range, would otherwise have matched). From batch 17, rule 8 also uses `regimen.units_per_intake`, so a sent `units_per_intake` that is dropped (`"1-2"`, `"half or one"`) nulls `strength` and `intake_amount` the same way.
- **`name_text`** must occur in the text of a turn the claim cites (both sides through `catalogue.normalise`, substring match, so `الPanadol` contains `Panadol`). Otherwise the reply is malformed (retryable), like an uncited turn.
- **`country`** is kept only as an ISO 3166-1 alpha-2 code (two letters, stored upper-case); anything else becomes null.
- **`assert_no_advice`** runs over `name_text`, the claim's `inn`, the label's `inn` and every ingredient `inn` (strength and intake). A hit makes the reply malformed (retryable). `label_text` is exempt: it is quoted source text, and real packs print directions ("Take one tablet daily").

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
- The `match` template is narrowed to what was actually compared: **"The compared identity and strength details agree."** (QM M3 r2 #5; batch 17)

### Identity of one side
- Every ingredient field uses one resolver: a known catalogue moiety is canonicalised with `canonical_inn`; otherwise a name resolving to a single-INN catalogue entry resolves to that INN; otherwise the canonicalised input stays unchanged (unknown names remain unknown).
- **Identity set:** the resolved INNs of `strength.ingredients` if a strength exists. Otherwise the resolved scalar `{inn}`, otherwise the INNs of the catalogue entry that `name_text` (or `label_text`) resolves to.
- If a side has a strength and a resolvable name, or (when strength is absent) a scalar `inn` and a resolvable name, and their INN sets differ, that is an extraction conflict and the result is `insufficient_information`.
- When a side has both a strength and a scalar `inn`, the `inn`'s resolved moiety must be in the strength's ingredient set, otherwise it is an extraction conflict. A salt form of the same moiety is not.
- **Brand-implied facts** (`release`, `splittable`) come from the catalogue only when the text matched a **brand** name, never an INN. "Beloc-Zok" implies modified release; "metoprolol" implies nothing.
- **A text that names 2+ different catalogue products** (`name_text` or `label_text`, e.g. a label read as "Beloc-Zok 100 mg Concor 5 mg") is an extraction conflict on that side, even when the side's identity comes from its strength. (C4; batch 17)
- **Claim-side release is trusted only when the claim says so** (C8; batch 17): a claim's explicit `strength.release` counts only if `name_text` contains a curated release word (whole word after `normalise`: `retard`, `depot`, `xr`, `xl`, `sr`, `er`, `cr`, `mr`, `prolonged`, `extended`, `modified`, `sustained`, `controlled`, `slow`, `immediate`, `ممتد`, `بطيء`; the Arabic words also with the attached clitics `ال`, `وال`, `بال`, `فال`, `لل`, `و`, `ف`, `ب`, `ل`) or matches a catalogue brand. An unsaid explicit release still counts when it **disagrees** with the pack, so it can raise `formulation_mismatch`, but never when it agrees: then the claim's release is the brand-implied one (usually `unknown`), so a guessed release can't make a `match`. (Batch 17: the older contracts, b3 `release_ir_vs_er` and b10 `f01b`, keep a bare-name `immediate` claim against a modified pack as `formulation_mismatch`.) Pack-side release is read from the label and trusted as before.

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
- Score each candidate: 3 = same identity and equal strength, 2 = same identity, 1 = overlap.
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
3. Per image, `segment` with each concept in order (`medicine box`, `label`), stopping at the first that returns a region.
4. **Read the crop first (Z8, batch 18).** For each of the `top_regions(k=3)` of each image: only regions whose `image_sha256` and frame size match the prepared photo are kept, ranked and published in the report; each other region gets one `read` step `error: region does not match the photo` and is dropped. Each kept region is cut with `crop_region` (padded by 5% of the box size on each side, i.e. 10% in total, rounded down and clamped to the frame; refused unless the sha256 and frame size match the region) and the reader is called on the **crop only**, as PNG, with `cropped=True`. The reader never sees the full photo, so a reading can only describe the pixels of its own region (provenance by construction; live, 27 Oct: 8/8 crop reads correct at 465–1,001 input tokens against about 4,300 for the full photo). A crop that fails logs one `read` step `error: crop failed` (no provider call) and the region gets no reading. Once the session is exhausted, no crop is cut and nothing is logged.
5. Each `unreadable` or `partial` reading gets **one** `zoom_read`: the same crop, upscaled 2× (Lanczos; the factor is lowered so the longest side is at most 2,048 px; if that factor is ≤ 1 there is no zoom and no step), read with `cropped=True`. The new reading keeps the **source** `region_id`, so provenance stays in source pixels. SAM never runs on a crop. At most 2 reads per region (`max_grounding_iters = 2`). Both the read and the zoom cut their crop through the name `crop_region` in `anamnesis/agent/loop.py`.
6. `reconcile` with `reconcile_all`.
- **Budget:** every provider call, including failed ones, counts 1 against `max_provider_calls` (default 12). The call that would exceed it is skipped, a `budget_exhausted` step is logged (it is then the last step, whatever fails afterwards, including a crop), and every remaining provider call is skipped. Reconciliation still runs on what exists.
- **Errors:** a provider error becomes a step whose `outcome` is `error: <provider> <ExceptionName>` (no message text); the loop continues with the next item.
- **Report:** one `ReconciliationReport` (`anamnesis/schema/report.py`): turns, claims, regions, observations (`o0, o1, ...` in reading order, `visual_evidence=[region_id]`), findings, steps, `calls`, `spend_usd` (sum of `cost_usd + prior_cost_usd` over every returned trace) and a sha256 `intake_id` of the inputs. A validator rejects any evidence, claim or observation id that points nowhere.
- **Session caps:** `SessionGuard(parent, max_usd, max_calls)` wraps the ledger guard with a per-session dollar and call cap and still writes every charge to the parent.
- Voice, SAM, and Spark calls retry once on retryable errors and use a 30 s timeout.

## 5. Every model call logs
- **Ledger** (`evidence/spend/ledger.jsonl`): `call_id`, `model_id`, `cost_usd`, `time_utc`, `estimated` (+ `reason`). Lines from before batch 12 have no `estimated` field; all of them are real charges.
- **Trace** (saved with each live result in `evidence/live/<date>/*.json`): latency and tokens as listed below.
- Muse Code grill runs (the `muse` CLI) are billed by Meta **outside** our adapters, so they are not on the ledger (see `evidence/decisions.md`).

`model_id`, `latency_ms`, `input_tokens`, `output_tokens`, `cost_usd` → `evidence/`. Hosted Meta models are the default. Open weights (Glimmer on Modal, Spark Open on Baseten) are for comparison only.
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
- the two sides **side by side**: `data-side="patient"` (name, strength, intake amount, regimen and status, verbatim) and `data-side="pack"` (label text, strength, readability, country). Amounts print as plain decimals with their unit and never with a trailing zero ("100 mg", never "100.0 mg"; "0.5", never ".5"), the safe-notation rule for doses. A missing side says "Not mentioned." or "Not photographed.";
- A3 wording: a `missing_modality` finding is labelled "Mentioned, not photographed" or "Photographed, not mentioned", and one in `stopped` "Reported as stopped, not photographed";
- a link to every piece of its evidence: `href="#turn:<turn_id>"` for each audio turn, `href="#region:<region_id>"` for each region.

**Evidence on the page.**
- Each photo that opens is `<figure id="photo:<i>">` (input order, from 1), with one `<img>` of the **prepared** bytes (§4 step 0) under an `<svg viewBox="0 0 <frame_w> <frame_h>">`. The svg has one `<rect>` per report region of that photo, at `x1, y1`, `x2 − x1 + 1` wide and `y2 − y1 + 1` high, inside `<a href="#region:<region_id>">`. A box is an outline with a transparent fill, so the pack under it stays visible and the whole box is clickable. No image makes the page wider than the screen.
- Each report region is `<figure id="region:<region_id>">` showing `crop_region(prepared photo, region)`. For a region that was read, these are exactly the pixels the reader saw; this is the click-to-zoom view.
- The voice note is one `<audio src="data:…">`. Each turn is `<li id="turn:<turn_id>" data-start-ms="…" data-end-ms="…">` with its time range and transcript. Clicking it plays that turn only, from its start to its end, and starting another turn ends the first.
- Every `#` link on the page points to an element on the page.

**Cross-medication observations** (`cross_medication(claims, catalogue)` in `anamnesis/core/overlap.py`; supervisor #2, J2). Pairwise reconciliation can't see two medicines that overlap each other: the showcase patient reports Concor and Beloc-Zok, two beta-blockers. Only **claims** count, never the photos, because a pack can't show use and repeated photos never imply duplicate use.
- A claim counts unless its status is `discontinued`, and only if its identity set (§3) can be built. Its *product* is the catalogue brand when `name_text` matches a brand or alias name, otherwise `normalise(name_text)`. A brand said twice, in either script, is one product.
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

**Scope lines**, in the header, always (supervisor #3, #4):
- "Anamnesis reports where the patient's account and the pack photos disagree. It gives no medical advice."
- "Prescribed directions, timing, adherence and supply were not assessed."
- "Over-the-counter, herbal and non-tablet products may be missing from this brief: ask about them."

**Catalogue:** one synthetic entry for the hero case (J2): Gelocatil (ES; paracetamol; immediate release; splittability unknown; Arabic aliases جيلوكاتيل and جلوكاتيل).
