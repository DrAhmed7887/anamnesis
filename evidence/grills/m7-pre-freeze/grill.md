| # | severity | surface | file:function | exact input | SPEC says | code does |
|---|---|---|---|---|---|---|
| 1 | critical | 1 | `anamnesis/providers/spark.py:parse_label_json` | `text = '{"label_text": "Amoxicillin 250 mg / 5 ملي", "inn": "amoxicillin", "country": "EG", "readability": "readable", "strength": {"ingredients": [{"inn": "amoxicillin", "amount": "250", "unit": "mg"}], "per": "ml", "release": "unknown"}}'`, `region_id = "r1"` | SPEC §2: "`ملي` alone counts, as Egyptian labels write it." A 250 mg / 5 ملي syrup read as 250 mg per ml must drop its strength to `None`. | `_VOLUME_RE` and `_ML` only match `مل` (without `ي`), so `5 ملي` is not recognised as a volume (`_find_dose_volumes` returns `[]`) and the 5× wrong strength `250 mg per ml` is kept as fact. |
| 2 | critical | 1 | `anamnesis/providers/spark.py:parse_label_json` | `text = '{"label_text": "Each 5 ml contains 250 mg. Also 250 mg/ml drops", "inn": "paracetamol", "country": null, "readability": "readable", "strength": {"ingredients": [{"inn": "paracetamol", "amount": "250", "unit": "mg"}], "per": "tablet", "release": "unknown"}}'`, `region_id = "r1"` | SPEC §2: "A volume or spoon right after an amount always counts... For a reading per `tablet`, `capsule` or `dose`, such a volume nulls the strength outright." (Here `5 ml` is not after an amount, and `250` is not printed per tablet, so strength must be `None` anyway; even if `"250 mg tablets"` is added, `250` is printed after `5 ml` in its sentence). Take `label_text = "Each 5 ml contains 250 mg. 250 mg tablets"` with `per = "tablet"`: SPEC §2 says `250` is printed later in the sentence of `5 ml`, so strength becomes `None`. | In `_printed_beside_a_volume`, `_SENTENCE_END_RE` stops at `. 2`? No: for `label_text = "Each 5 ml contains 250 mg/ml. 250 mg tablets"` with `per = "tablet"`, `_starts_own_print` is only skipped for `per in ("ml", "dose")`, wait—for `per = "dose"` and `label_text = "Each 5 ml contains 250 mg/ml"`, `_starts_own_print(text, pos, 250, "dose")` returns `True` on `250 mg/ml`, AND `_printed_per_1ml` returns `True`, so `"Each 5 ml contains 250 mg/ml"` (or `"Each 5 ml contains 250 mg per dose"`) keeps `250 mg per dose`! |
| 3 | high | 1 | `anamnesis/providers/spark.py:parse_label_json` | `text = '{"label_text": "Paracetamol twenty-five mg/5 ml. 25 mg/ml drops", "inn": "paracetamol", "country": null, "readability": "readable", "strength": {"ingredients": [{"inn": "paracetamol", "amount": "25", "unit": "mg"}], "per": "ml", "release": "unknown"}}'`, `region_id = "r1"` | SPEC §2: "Each 5 ml contains 125 mg" / "no amount of the reading is also printed beside a volume or spoon" — when the label prints `"Each 5 ml contains twenty-five mg. Also 25 mg/ml drops"` (or `"five ml contains 250 mg. 250 mg/ml"`), `five ml` is a volume of 5 ml and `twenty-five` is the reading's amount 25. | `_VOLUME_RE` and `_NUMBER_RE` only match digits (`[0-9]+`), never number words, whereas `parse_amount_text` and `stated_amounts` accept number words. Thus `"Each five ml contains 250 mg. 250 mg/ml"` misses the volume `five ml` and keeps `250 mg/ml`. |
| 4 | high | 2 | `anamnesis/core/reconcile.py:reconcile_pair` | `claim` with `name_text="metoprolol"`, `strength=Strength(ingredients=[IngredientAmount(inn="metoprolol", amount=Decimal(100), unit=Unit.MG)], per=StrengthPer.TABLET, release=Release.IMMEDIATE)` and `observation` with `label_text="Metoprolol 100 mg"`, `readability="readable"`, `strength=Strength(ingredients=[IngredientAmount(inn="metoprolol", amount=Decimal(100), unit=Unit.MG)], per=StrengthPer.TABLET, release=Release.IMMEDIATE)` | SPEC §3 (C8, batch 17): "Claim-side release is trusted only when the claim says so: a claim's explicit `strength.release` counts only if `name_text` contains a curated release word ... or matches a catalogue brand. An unsaid explicit release still counts when it **disagrees** with the pack, so it can raise `formulation_mismatch`, but never when it agrees: then the claim's release is the brand-implied one (usually `unknown`), so a guessed release can't make a `match`." | When the pack is `MODIFIED` and the claim has an unsaid `MODIFIED` release on an INN-only `name_text="metoprolol"`, `_claim_release` returns `Release.UNKNOWN`, and rule 10 returns `insufficient_information`. However, in `_pair_score`, `reconcile_all` pairs a claim having `strength=100mg (release=MODIFIED)` and `intake_amount=None` at score 3 via `_claim_strength_type` (which ignores release), beating a pack that actually matches release! Even worse, if `claim` has `strength=None`, `intake_amount=50mg`, and `name_text="Beloc-Zok"` (brand-implied `MODIFIED`, splittable) vs two packs of `metoprolol 50 mg` (one `IMMEDIATE`, one `MODIFIED`), wait: what if `claim` has `name_text="metoprolol"`, `strength=None`, `intake_amount=100mg`, and `regimen=DoseRegimen(units_per_intake=Decimal(1))` vs `pack` with `label_text="Beloc-Zok 95 mg"` (metoprolol succinate 95 mg = 100 mg nominal, release=`UNKNOWN` on strength)? `_release` on pack uses `catalogue.implied_release("Beloc-Zok 95 mg")` -> `MODIFIED`, while claim is `UNKNOWN` -> `insufficient_information`. What if `pack.label_text="Metoprolol succinate 95 mg"` (no brand, `strength.release=UNKNOWN`) and `claim.name_text="metoprolol 100 mg"` (`strength.release=UNKNOWN`)? Both releases are `UNKNOWN`, and nominal equivalence converts 95 mg succinate to 100 mg even though succinate is modified-release! That returns `match` on an unknown-release pack. |
| 5 | high | 5 | `anamnesis/providers/openweight.py:OpenWeightLabelReader.__init__` | `OpenWeightLabelReader(client, guard, model="meta-models/muse-spark-open", price_key="muse-spark-open-contributor@baseten", json_mode=False)` | SPEC §5: "`MetaLabelReader`, `MetaClaimExtractor`, the open-weight reader, `ProviderTrace`, `AgentStep` and `SpendGuard.charge_estimate` (so `SessionGuard.charge_estimate` too) all refuse a model id with `-contributor` anywhere in it, in any case, surrounding whitespace ignored". | `OpenWeightLabelReader.__init__` checks `self.model` for `"-contributor"`, but does NOT check `self.price_key`, which is what it passes as `model_id` to `ProviderTrace`, `with_one_retry`, and `guard.charge_estimate`. It accepts a `-contributor` `price_key` at construction time and sends the HTTP request before `ProviderTrace` rejects it after the call has already been made. |
| 6 | high | 6 | `scripts/reader_eval.py:main` | Run `scripts/reader_eval.py --key key.json --readers spark` (or `fireworks`) where `key.json` has `[{"photo": "public/../../real/secret.jpg", ...}]` or a symlink inside `evidence/raw/media/public/link.jpg` pointing to `evidence/raw/media/real/secret.jpg`; OR in `scripts/intake_live.py`, pass `--reader spark --case R1 --voice v.wav --photo /etc/passwd` (or in `reader_eval.py`, `regions_for` caches segments by sha256 without checking `PUBLIC` when `regions_for` is called directly). Even simpler: in `scripts/reader_eval.py`, `PUBLIC = (MEDIA / "public", MEDIA / "real-public")` allows ANY file under `evidence/raw/media/public/`, whereas `docs/DATA_HANDLING.md` and `scripts/intake_live.py` (`OPEN_WEIGHT_PHOTOS`) restrict public photos to `public/commons`, `public/gemini-commons`, and `real-public`! | SPEC §4 & `docs/DATA_HANDLING.md`: "Public test photos only, for the open-weight comparison (batch 22)... the Wikimedia Commons and Cairo University CC BY photos may also go to Fireworks or Baseten." `intake_live.py` enforces `OPEN_WEIGHT_PHOTOS = (MEDIA / "public/commons", MEDIA / "public/gemini-commons", MEDIA / "real-public")`. | `scripts/reader_eval.py` sets `PUBLIC = (MEDIA / "public", MEDIA / "real-public")`, allowing any photo placed in `evidence/raw/media/public/` outside `commons` and `gemini-commons` (e.g., `evidence/raw/media/public/ staged_private.jpg`) to be sent to Fireworks or Baseten. |
| 7 | high | 7 | `anamnesis/review.py:request_message` | `report` with `PatientClaim(claim_id="c1", name_text="   \n  ", status=MedicationStatus.ACTIVE, audio_evidence=["t1"])` and `request = PhotoRequest(request_id="r1", kind=RequestKind.NOT_PHOTOGRAPHED, target_id="c1", status=RequestStatus.OPEN)` | SPEC §8: "`not_photographed`: 'Please send one photo of the pack of the medicine you mentioned as “{name}”.', where `{name}` is the first non-blank line of the claim's `name_text`, verbatim." And SPEC §3: "`assert_no_advice` runs over `name_text`... The messages to the patient are fixed text and give no advice." | If `claim.name_text` has a line that contains a formatting brace or if `name_text` is `"Panadol\nTake two daily"`—wait: `assert_no_advice` is NOT run on `PatientClaim` construction! A `PatientClaim` constructed in a report (or loaded from JSON) with `name_text="Take two tablets"` is interpolated verbatim by `request_message` into the patient message without running `assert_no_advice`, leaking advice directly to the patient. |
| 8 | medium | 4 | `anamnesis/agent/loop.py:run_intake` | Two photos (or two concepts/regions) where a custom/fixture segmenter returns two `ImageRegion` objects with the same `region_id` on the same photo, or `add_photo` where a new photo produces a `region_id` already in `report.regions` (e.g., two photos sharing the same 12-char sha256 prefix and `object_id=0`). | SPEC §4 & §7: Every region's crop and bounding box in the brief must come from the photo that region belongs to (`region.image_sha256`). | `ImageRegion.region_id` is `f"{image_sha256[:12]}-{object_id}"`, and `run_intake` / `add_photo` deduplicate regions by `region_id` (`regions.update({region.region_id: region for region in kept})`), overwriting the earlier region while keeping both observations pointing to the same `region_id`. |
| 9 | medium | 5 | `anamnesis/providers/spend.py:SessionGuard.charge_prechecked` | Call `MetaLabelReader.read` wrapped in `SessionGuard(ledger, max_usd=Decimal("0.006"), max_calls=10)` where attempt 1 returns a 200 OK with `finish_reason="length"` (or malformed JSON) whose actual `trace.cost_usd` exceeds `max_usd` (e.g. `prompt_tokens=5000, completion_tokens=4000` -> `cost_usd = $0.02325 > estimate`). | SPEC §4 & §5: `SessionGuard` caps per-session spend at `max_usd`. | `charge_prechecked` does not check `self._usd + trace.cost_usd <= self.max_usd` or `self.parent.cap_usd`; it unconditionally appends `trace.cost_usd` to the ledger and session total, allowing actual spend to exceed both `SessionGuard.max_usd` and `SpendGuard.cap_usd` when `prompt_tokens` exceeds the `chars // 2 + 5000` heuristic. |
| 10 | medium | 2 | `anamnesis/core/catalogue.py:Catalogue.resolve` | `catalogue.resolve("أملوديبين 5 مجم")` or `catalogue.resolve("باراسيتامول")` | SPEC §2 & §3: Arabic ingredient names or Spanish/French/German/Latin ingredient aliases (`INN_ALIASES`) on a multi-INN product, or an INN with an Arabic clitic: "Arabic names ... accept the attached clitics `ال`, `وال`, `بال`, `فال`, `لل`, `و`, `ف`, `ب` and `ل`." | In `Catalogue._matches`, INN and `INN_ALIASES` names are only matched when `len(entry.inns) == 1` (`if len(entry.inns) == 1:`), so `"amoxicillin and clavulanic acid"` (or `"amoxicilline / acide clavulanique"`) in `label_text` without a `strength` or `inn` field resolves to `amoxicillin` alone (single-INN entry) instead of the combination or ambiguity! Specifically, `catalogue.resolve("amoxicillin clavulanic acid")` returns the single-ingredient `Amoxil` (`inns={"amoxicillin"}`), completely dropping `clavulanic acid`! |
| 11 | low | 7 | `anamnesis/providers/numbers.py:parse_amount_text` | `parse_amount_text("00.125")` or `parse_amount_text("١.٠٠٠")` | SPEC §2: "A dot followed by exactly three digits with a non-zero whole part (`"1.000"`, `"2.500"`) is ambiguous the same way (a European thousands mark) and does not parse; `"0.125"` does... Both Arabic-Indic digit sets and the Arabic decimal sign `٫` are read as ASCII first." | `parse_amount_text("١,٥")` (Arabic-Indic digits with a comma) fails with `None` because `Decimal("١.٥")` raises `InvalidOperation` in Python when a comma is replaced by a dot, OR wait: `Decimal("١.٥")` works in Python, but `parse_amount_text(1.5)` (a `float`) converts `1.5` to `"1.5"`, whereas `parse_amount_text(1e-5)` converts to `"1e-05"`, which fails `_AMOUNT_RE` and returns `None` even though it is a positive float. |

### Reproducer tests (Critical and High findings)

```python
# Finding 1 (Critical, Surface 1): Egyptian "ملي" volume unit is not matched by _VOLUME_RE
def test_finding_1_egyptian_milli_volume_drops_strength():
    import json
    from anamnesis.providers.spark import parse_label_json

    raw = json.dumps({
        "label_text": "Amoxicillin 250 mg / 5 ملي",
        "inn": "amoxicillin",
        "country": "EG",
        "readability": "readable",
        "strength": {
            "ingredients": [{"inn": "amoxicillin", "amount": "250", "unit": "mg"}],
            "per": "ml",
            "release": "unknown",
        },
    })
    assert parse_label_json(raw, "r1").strength is None
```

```python
# Finding 2 (Critical, Surface 1): "Each 5 ml contains 250 mg per dose" keeps 250 mg/dose
def test_finding_2_syrup_with_per_dose_after_volume_drops_strength():
    import json
    from anamnesis.providers.spark import parse_label_json

    raw = json.dumps({
        "label_text": "Each 5 ml contains 250 mg per dose",
        "inn": "paracetamol",
        "country": None,
        "readability": "readable",
        "strength": {
            "ingredients": [{"inn": "paracetamol", "amount": "250", "unit": "mg"}],
            "per": "dose",
            "release": "unknown",
        },
    })
    assert parse_label_json(raw, "r1").strength is None
```

```python
# Finding 3 (High, Surface 1): Volume written as a number word ("five ml") is ignored
def test_finding_3_word_volume_drops_per_ml_strength():
    import json
    from anamnesis.providers.spark import parse_label_json

    raw = json.dumps({
        "label_text": "Each five ml contains 250 mg",
        "inn": "amoxicillin",
        "country": None,
        "readability": "readable",
        "strength": {
            "ingredients": [{"inn": "amoxicillin", "amount": "250", "unit": "mg"}],
            "per": "ml",
            "release": "unknown",
        },
    })
    assert parse_label_json(raw, "r1").strength is None
```

```python
# Finding 4 (High, Surface 2): Combination INN text resolves to single-ingredient Amoxil
def test_finding_4_combination_inns_in_text_do_not_false_match_single_inn():
    from decimal import Decimal
    from anamnesis.core.catalogue import load_catalogue
    from anamnesis.core.reconcile import reconcile_pair
    from anamnesis.schema import (
        DiscrepancyType, IngredientAmount, MedicationStatus,
        PackObservation, PatientClaim, Readability, Strength, StrengthPer, Unit,
    )

    cat = load_catalogue()
    claim = PatientClaim(
        claim_id="c1", name_text="amoxicillin clavulanic acid",
        intake_amount=IngredientAmount(inn="amoxicillin", amount=Decimal(500), unit=Unit.MG),
        status=MedicationStatus.ACTIVE, audio_evidence=["t1"],
    )
    pack = PackObservation(
        observation_id="o1", label_text="Amoxil 500 mg", readability=Readability.READABLE,
        strength=Strength(ingredients=[IngredientAmount(inn="amoxicillin", amount=Decimal(500), unit=Unit.MG)],
                          per=StrengthPer.TABLET),
        visual_evidence=["r1"],
    )
    assert reconcile_pair(claim, pack, cat).type is not DiscrepancyType.MATCH
```

```python
# Finding 5 (High, Surface 5): OpenWeightLabelReader accepts -contributor in price_key
def test_finding_5_openweight_reader_rejects_contributor_price_key(tmp_path):
    from decimal import Decimal
    import pytest
    from anamnesis.providers.openweight import OpenWeightClient, OpenWeightLabelReader
    from anamnesis.providers.spend import SpendGuard

    client = OpenWeightClient("key", "https://inference.baseten.co/v1", "baseten")
    guard = SpendGuard(tmp_path / "ledger.jsonl", Decimal("1.00"))
    with pytest.raises(ValueError, match="contributor"):
        OpenWeightLabelReader(
            client, guard, model="meta-models/muse-spark-open",
            price_key="muse-spark-open-contributor@baseten", json_mode=False,
        )
```

```python
# Finding 6 (High, Surface 6): reader_eval.py allows photos outside public/commons & gemini-commons
def test_finding_6_reader_eval_rejects_non_commons_photo_under_public():
    import pytest
    from scripts.reader_eval import public_photo

    with pytest.raises(SystemExit):
        public_photo("public/unapproved_folder/photo.jpg")
```

```python
# Finding 7 (High, Surface 3/7): request_message leaks unchecked advice in claim.name_text
def test_finding_7_request_message_rejects_advice_in_name_text():
    from anamnesis.core.guardrails import assert_no_advice
    from anamnesis.review import new_review, request_message, request_photo
    from anamnesis.schema import (
        AudioTurn, DiscrepancyType, Finding, MedicationStatus, PatientClaim, ReconciliationReport,
    )
    from anamnesis.schema.templates import QUESTION_FOR, TEMPLATES

    claim = PatientClaim(claim_id="c1", name_text="Panadol - take two tablets daily",
                         status=MedicationStatus.ACTIVE, audio_evidence=["t1"])
    finding = Finding(finding_id="c1:-", type=DiscrepancyType.MISSING_MODALITY, claim_id="c1",
                      observation_id=None, audio_evidence=["t1"], visual_evidence=[],
                      needs_clinician_review=True, clinician_note=TEMPLATES[DiscrepancyType.MISSING_MODALITY],
                      patient_question_id=QUESTION_FOR[DiscrepancyType.MISSING_MODALITY])
    report = ReconciliationReport(intake_id="a" * 64, turns=[AudioTurn(turn_id="t1", start_ms=0, end_ms=1000, transcript="x")],
                                  claims=[claim], regions=[], observations=[], findings=[finding], steps=[], calls=0, spend_usd=0)
    review = request_photo(new_review(report), report, "c1")
    assert_no_advice(request_message(report, review.requests[0]))
```

GRILL: 11 findings (2 critical, 5 high)
