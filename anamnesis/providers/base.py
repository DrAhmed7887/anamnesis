"""Shared provider errors, traces, retries, and documented prices."""

from collections.abc import Callable
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProviderError(Exception):
    def __init__(self, provider: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class ProviderTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    call_id: Annotated[str, Field(min_length=1)]
    model_id: Annotated[str, Field(min_length=1)]
    latency_ms: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: Decimal = Field(ge=0, allow_inf_nan=False)

    @field_validator("model_id")
    @classmethod
    def reject_contributor(cls, value: str) -> str:
        if value.endswith("-contributor"):
            raise ValueError("contributor models are not permitted")
        return value


def with_one_retry[T](fn: Callable[[], T]) -> T:
    try:
        return fn()
    except ProviderError as exc:
        if not exc.retryable:
            raise
    return fn()


_PRICES = {
    "muse-spark-1.3": {"input_tokens": Decimal("1.25") / 1_000_000,
                       "output_tokens": Decimal("4.25") / 1_000_000},
    "sam-3.1": {"images": Decimal("2.50") / 1_000},
    "muse-voice-transcribe-1.0": {"audio_seconds": Decimal("0.18") / 3_600},
}


def cost_usd(
    model_id: str, *, input_tokens: int = 0, output_tokens: int = 0,
    audio_ms: int | None = None, images: int | None = None,
) -> Decimal:
    rates = _PRICES[model_id]
    if any(value < 0 for value in (input_tokens, output_tokens, audio_ms or 0, images or 0)):
        raise ValueError("usage cannot be negative")
    return (
        rates.get("input_tokens", Decimal(0)) * input_tokens
        + rates.get("output_tokens", Decimal(0)) * output_tokens
        + rates.get("images", Decimal(0)) * (images or 0)
        + rates.get("audio_seconds", Decimal(0)) * (((audio_ms or 0) + 999) // 1000)
    )
