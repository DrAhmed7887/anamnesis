"""Typed Muse Spark label reading boundary."""

import json
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from anamnesis.providers.base import ProviderError
from anamnesis.schema import Readability, Strength


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


def parse_label_json(text: str, region_id: str) -> LabelReading:
    try:
        data = json.loads(text)
        if not isinstance(data, dict) or "region_id" in data:
            raise ValueError("expected a label object without region_id")
        return LabelReading.model_validate({**data, "region_id": region_id})
    except (TypeError, ValueError, ValidationError) as exc:
        raise ProviderError("spark", f"malformed label reading: {exc}", retryable=True) from exc
