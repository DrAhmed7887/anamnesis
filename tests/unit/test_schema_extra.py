"""Additional boundary cases for domain schemas."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from anamnesis.schema import (
    AudioTurn,
    DoseRegimen,
    Finding,
    ImageRegion,
    IngredientAmount,
    Strength,
)


def test_ids_must_be_non_empty():
    with pytest.raises(ValidationError):
        AudioTurn(turn_id="", start_ms=0, end_ms=1, transcript="x")


def test_decimal_dose_fields_preserve_fractional_values():
    regimen = DoseRegimen(units_per_intake=Decimal("0.5"), intakes_per_day=Decimal("1.5"))
    assert regimen.units_per_intake == Decimal("0.5")
    assert regimen.intakes_per_day == Decimal("1.5")


def test_image_region_allows_box_touching_last_pixel():
    region = ImageRegion(
        region_id="r1",
        image_sha256="a" * 64,
        object_id=0,
        x1=0,
        y1=0,
        x2=9,
        y2=9,
        frame_w=10,
        frame_h=10,
    )
    assert (region.x2, region.y2) == (9, 9)


def test_non_match_finding_requires_review_even_with_both_sides():
    with pytest.raises(ValidationError, match="requires clinician review"):
        Finding(
            finding_id="f1",
            type="strength_mismatch",
            claim_id="c1",
            observation_id="o1",
            audio_evidence=["t1"],
            visual_evidence=["r1"],
            needs_clinician_review=False,
            clinician_note="Review needed.",
        )


def test_amount_is_kept_as_decimal():
    amount = IngredientAmount(inn="amoxicillin", amount=Decimal("875"), unit="mg")
    assert isinstance(amount.amount, Decimal)


def test_duplicate_ingredient_alias_is_rejected():
    with pytest.raises(ValidationError, match="duplicate canonical INNs"):
        Strength(
            ingredients=[
                IngredientAmount(inn="Acetaminophen", amount=Decimal(500), unit="mg"),
                IngredientAmount(inn="paracetamol", amount=Decimal(500), unit="mg"),
            ],
            per="tablet",
        )
