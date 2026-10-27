"""Batch 1 contract: domain models (SPEC.md §1-3). Written by the reviewer; the builder must not edit it."""

import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from anamnesis.schema import (
    AudioTurn,
    DiscrepancyType,
    DoseRegimen,
    Finding,
    ImageRegion,
    IngredientAmount,
    MedicationStatus,
    PackObservation,
    PatientClaim,
    Readability,
    Strength,
)

SHA = "a" * 64


def strength(*pairs, per="tablet"):
    return Strength(
        ingredients=[IngredientAmount(inn=inn, amount=Decimal(str(a)), unit="mg") for inn, a in pairs],
        per=per,
    )


def finding(type_, audio=("t1",), visual=("r1",), review=True, **kw):
    return Finding(
        finding_id="f1",
        type=type_,
        claim_id=kw.pop("claim_id", "c1"),
        observation_id=kw.pop("observation_id", "o1"),
        audio_evidence=list(audio),
        visual_evidence=list(visual),
        needs_clinician_review=review,
        clinician_note="Sources disagree; review with the patient.",
        **kw,
    )


# --- evidence ---------------------------------------------------------------

def test_audio_turn_valid():
    t = AudioTurn(turn_id="t1", start_ms=0, end_ms=4200, transcript="Concor 5", speaker="A")
    assert t.end_ms == 4200 and t.lang_hint is None


@pytest.mark.parametrize("start,end", [(100, 100), (500, 100), (-1, 10)])
def test_audio_turn_rejects_bad_times(start, end):
    with pytest.raises(ValidationError):
        AudioTurn(turn_id="t1", start_ms=start, end_ms=end, transcript="x")


def test_image_region_valid():
    r = ImageRegion(region_id="r1", image_sha256=SHA, object_id=0,
                    x1=353, y1=382, x2=453, y2=427, frame_w=537, frame_h=561, confidence=0.9)
    assert r.x2 == 453


@pytest.mark.parametrize("box", [
    dict(x1=10, y1=10, x2=5, y2=20),      # x2 < x1
    dict(x1=0, y1=0, x2=537, y2=20),      # x2 == frame_w (inclusive corners must be < w)
    dict(x1=0, y1=0, x2=20, y2=561),      # y2 == frame_h
    dict(x1=-1, y1=0, x2=20, y2=20),      # negative
])
def test_image_region_rejects_box_outside_frame(box):
    with pytest.raises(ValidationError):
        ImageRegion(region_id="r1", image_sha256=SHA, object_id=0, frame_w=537, frame_h=561, **box)


@pytest.mark.parametrize("sha", ["abc", "A" * 64, "g" * 64])
def test_image_region_rejects_bad_hash(sha):
    with pytest.raises(ValidationError):
        ImageRegion(region_id="r1", image_sha256=sha, object_id=0,
                    x1=0, y1=0, x2=1, y2=1, frame_w=10, frame_h=10)


@pytest.mark.parametrize("c", [-0.1, 1.1])
def test_image_region_rejects_confidence_out_of_range(c):
    with pytest.raises(ValidationError):
        ImageRegion(region_id="r1", image_sha256=SHA, object_id=0,
                    x1=0, y1=0, x2=1, y2=1, frame_w=10, frame_h=10, confidence=c)


# --- medication facts -------------------------------------------------------

def test_ingredient_amount_rules():
    assert IngredientAmount(inn="bisoprolol", amount=Decimal("2.5"), unit="mg").amount == Decimal("2.5")
    for bad in [dict(amount=Decimal("0"), unit="mg"), dict(amount=Decimal("5"), unit="mgs")]:
        with pytest.raises(ValidationError):
            IngredientAmount(inn="bisoprolol", **bad)


def test_strength_supports_combinations_and_requires_one_ingredient():
    aug = strength(("amoxicillin", 875), ("clavulanic acid", 125))
    assert len(aug.ingredients) == 2
    with pytest.raises(ValidationError):
        Strength(ingredients=[], per="tablet")
    with pytest.raises(ValidationError):
        strength(("paracetamol", 500), per="sachet-ish")


def test_dose_regimen_allows_half_tablets_and_rejects_zero():
    assert DoseRegimen(units_per_intake=Decimal("0.5"), intakes_per_day=Decimal("2")).as_needed is False
    with pytest.raises(ValidationError):
        DoseRegimen(units_per_intake=Decimal("0"))


def test_patient_claim_keeps_intake_separate_from_strength():
    c = PatientClaim(
        claim_id="c1", name_text="metoprolol", inn="metoprolol",
        intake_amount=IngredientAmount(inn="metoprolol", amount=Decimal("50"), unit="mg"),
        regimen=DoseRegimen(intakes_per_day=Decimal("2")),
        status="active", audio_evidence=["t1"],
    )
    assert c.strength is None and c.intake_amount.amount == Decimal("50")
    assert c.status is MedicationStatus.ACTIVE


def test_patient_claim_requires_audio_evidence():
    with pytest.raises(ValidationError):
        PatientClaim(claim_id="c1", name_text="concor", status="unknown", audio_evidence=[])


def test_pack_observation_rules():
    o = PackObservation(observation_id="o1", label_text="Concor 5 mg", inn="bisoprolol",
                        strength=strength(("bisoprolol", 5)), readability="readable",
                        country="DE", visual_evidence=["r1"])
    assert o.readability is Readability.READABLE
    unreadable = PackObservation(observation_id="o2", readability="unreadable", visual_evidence=["r2"])
    assert unreadable.label_text is None and unreadable.strength is None
    with pytest.raises(ValidationError):  # readable needs label text
        PackObservation(observation_id="o3", readability="readable", visual_evidence=["r3"])
    with pytest.raises(ValidationError):  # needs visual evidence
        PackObservation(observation_id="o4", readability="unreadable", visual_evidence=[])


# --- findings ---------------------------------------------------------------

def test_discrepancy_enum_is_closed_and_lowercase():
    assert {t.value for t in DiscrepancyType} == {
        "match", "strength_mismatch", "intake_differs_from_unit_strength", "ingredient_mismatch",
        "ratio_mismatch", "discontinued_but_present", "unreadable_source", "unresolved_name",
        "missing_modality",
    }


def test_match_may_skip_review_but_others_may_not():
    assert finding("match", review=False).needs_clinician_review is False
    for t in DiscrepancyType:
        if t is DiscrepancyType.MATCH:
            continue
        kw = {}
        if t is DiscrepancyType.MISSING_MODALITY:
            kw = dict(visual=())
        with pytest.raises(ValidationError):
            finding(t, review=False, **kw)


@pytest.mark.parametrize("t", ["match", "strength_mismatch", "intake_differs_from_unit_strength",
                               "ingredient_mismatch", "ratio_mismatch", "discontinued_but_present"])
def test_two_sided_types_need_both_evidence_lists(t):
    finding(t)
    with pytest.raises(ValidationError):
        finding(t, visual=())
    with pytest.raises(ValidationError):
        finding(t, audio=())


def test_unreadable_source_needs_visual_evidence():
    finding("unreadable_source", audio=())
    with pytest.raises(ValidationError):
        finding("unreadable_source", visual=())


def test_unresolved_name_needs_at_least_one_side():
    finding("unresolved_name", visual=())
    finding("unresolved_name", audio=())
    with pytest.raises(ValidationError):
        finding("unresolved_name", audio=(), visual=())


def test_missing_modality_needs_exactly_one_side():
    finding("missing_modality", visual=())
    finding("missing_modality", audio=())
    with pytest.raises(ValidationError):
        finding("missing_modality")
    with pytest.raises(ValidationError):
        finding("missing_modality", audio=(), visual=())


# --- whole-model rules ------------------------------------------------------

@pytest.mark.parametrize("model,kwargs", [
    (AudioTurn, dict(turn_id="t1", start_ms=0, end_ms=1, transcript="x")),
    (IngredientAmount, dict(inn="x", amount=Decimal("1"), unit="mg")),
    (PackObservation, dict(observation_id="o1", readability="unreadable", visual_evidence=["r1"])),
])
def test_extra_fields_forbidden(model, kwargs):
    with pytest.raises(ValidationError):
        model(**kwargs, surprise=True)


def test_json_round_trip():
    f = finding("strength_mismatch", patient_question_id="q_strength")
    assert Finding.model_validate_json(f.model_dump_json()) == f
    c = PatientClaim(claim_id="c1", name_text="augmentin",
                     strength=strength(("amoxicillin", 875), ("clavulanic acid", 125)),
                     status="active", audio_evidence=["t1", "t2"])
    assert PatientClaim.model_validate_json(c.model_dump_json()) == c


def test_json_schemas_are_not_recursive():
    for model in (Finding, PatientClaim, PackObservation):
        schema = json.dumps(model.model_json_schema())
        assert f'"#/$defs/{model.__name__}"' not in schema
