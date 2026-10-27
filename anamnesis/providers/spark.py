"""Typed Muse Spark label reading boundary."""

import json
import re
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from anamnesis.core.guardrails import AdviceLeak, assert_no_advice, assert_no_advice_in_ingredients
from anamnesis.providers.base import ProviderError
from anamnesis.providers.numbers import coerce_strength
from anamnesis.schema import Readability, Strength

_COUNTRY_RE = re.compile(r"[A-Za-z]{2}")


class LabelReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_id: Annotated[str, Field(min_length=1)]
    label_text: str | None = None
    inn: Annotated[str, Field(min_length=1)] | None = None
    strength: Strength | None = None
    readability: Readability
    country: str | None = None

    @model_validator(mode="after")
    def require_readable_label(self) -> "LabelReading":
        if self.readability is Readability.READABLE and not self.label_text:
            raise ValueError("label_text is required when readability is readable")
        return self


def _check_no_advice(data: dict[str, Any]) -> None:
    """Run the advice check over raw model-written inn strings (SPEC §2)."""
    text = data.get("inn")
    if isinstance(text, str) and text:
        try:
            assert_no_advice(text)
        except AdviceLeak as exc:
            raise ValueError("label string failed the advice check") from exc
    assert_no_advice_in_ingredients(data)


_STRENGTH_KEYS = frozenset({"ingredients", "per", "release"})
_INGREDIENT_KEYS = frozenset({"inn", "amount", "unit"})


def _check_strength_shape(strength: Any) -> None:
    """Refuse strength keys beyond LABEL_SCHEMA's, so no model-written salt passes (SPEC §2)."""
    if not isinstance(strength, dict):
        return
    if set(strength) - _STRENGTH_KEYS:
        raise ValueError("label strength has keys beyond the schema")
    ingredients = strength.get("ingredients")
    if not isinstance(ingredients, list):
        return
    for part in ingredients:
        if isinstance(part, dict) and set(part) - _INGREDIENT_KEYS:
            raise ValueError("label strength ingredient has keys beyond the schema")


def _coerce_country(value: Any) -> str | None:
    """Keep only an ISO 3166-1 alpha-2 code, stored upper-case."""
    if isinstance(value, str) and _COUNTRY_RE.fullmatch(value):
        return value.upper()
    return None


def parse_label_json(text: str, region_id: str) -> LabelReading:
    try:
        data = json.loads(text)
        if not isinstance(data, dict) or "region_id" in data:
            raise ValueError("expected a label object without region_id")
        _check_no_advice(data)
        _check_strength_shape(data.get("strength"))
        validated = {
            **data,
            "region_id": region_id,
            "country": _coerce_country(data.get("country")),
            "strength": (
                coerce_strength(data["strength"]) if data.get("strength") is not None else None
            ),
        }
        return LabelReading.model_validate(validated)
    except (TypeError, ValueError, ValidationError) as exc:
        raise ProviderError("spark", f"malformed label reading: {exc}", retryable=True) from exc
