"""Shared provider errors, traces, retries, and documented prices."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from anamnesis.providers.spend import SpendGuard


class ProviderError(Exception):
    def __init__(
        self,
        provider: str,
        message: str,
        retryable: bool = False,
        *,
        billable_uncertain: bool = False,
        estimated_reason: str | None = None,
        attempt_trace: ProviderTrace | None = None,
        charged_call_ids: list[str] | None = None,
        charged_usd: Decimal = Decimal(0),
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable
        self.billable_uncertain = billable_uncertain
        self.estimated_reason = estimated_reason
        self.attempt_trace = attempt_trace
        self.charged_call_ids = list(charged_call_ids or [])
        self.charged_usd = charged_usd


class ProviderTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    call_id: Annotated[str, Field(min_length=1)]
    model_id: Annotated[str, Field(min_length=1)]
    latency_ms: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: Decimal = Field(ge=0, allow_inf_nan=False)
    prior_call_ids: list[str] = Field(default_factory=list)
    prior_cost_usd: Decimal = Field(default=Decimal(0), ge=0, allow_inf_nan=False)

    @field_validator("model_id")
    @classmethod
    def reject_contributor(cls, value: str) -> str:
        if "-contributor" in value.strip().casefold():
            raise ValueError("contributor models are not permitted")
        return value


def _charged_attempt(
    exc: ProviderError, guard: SpendGuard, model_id: str, estimate: Decimal
) -> tuple[list[str], Decimal]:
    """Call ids and cost that one failed attempt charged: a real trace, an estimate, or nothing."""
    if exc.attempt_trace is not None:
        return [exc.attempt_trace.call_id], exc.attempt_trace.cost_usd
    if exc.billable_uncertain:
        call_id = guard.charge_estimate(model_id, estimate, exc.estimated_reason or "billing uncertain")
        return [call_id], estimate
    return [], Decimal(0)


def with_one_retry[T](
    fn: Callable[[], T], *, guard: SpendGuard | None = None, model_id: str | None = None,
    estimate: Decimal | None = None,
) -> T:
    if guard is None:
        try:
            return fn()
        except ProviderError as exc:
            if not exc.retryable:
                raise
        return fn()
    if model_id is None or estimate is None:
        raise ValueError("model_id and estimate are required for traced retries")
    prior_call_ids: list[str] = []
    prior_cost_usd = Decimal(0)
    for attempt in range(2):
        try:
            result, trace = cast(tuple[T, ProviderTrace], fn())
        except Exception as exc:
            if isinstance(exc, ProviderError):
                call_id, cost = _charged_attempt(exc, guard, model_id, estimate)
                prior_call_ids.extend(call_id)
                prior_cost_usd += cost
            if attempt == 0 and isinstance(exc, ProviderError) and exc.retryable:
                continue
            # Anything escaping after charged attempts (a retryable error, or the cap refusing attempt 2)
            # carries them, so the caller's spend matches the ledger.
            exc.charged_call_ids = list(prior_call_ids)  # type: ignore[attr-defined]
            exc.charged_usd = prior_cost_usd  # type: ignore[attr-defined]
            raise
        else:
            return cast(T, (result, trace.model_copy(update={
                "prior_call_ids": prior_call_ids,
                "prior_cost_usd": prior_cost_usd,
            })))
    raise AssertionError("retry loop must return or raise")


_PRICES = {
    "muse-spark-1.3": {"input_tokens": Decimal("1.25") / 1_000_000,
                       "output_tokens": Decimal("4.25") / 1_000_000},
    "muse-spark-open@fireworks": {"input_tokens": Decimal("1.25") / 1_000_000,
                                  "output_tokens": Decimal("4.25") / 1_000_000},
    "muse-spark-open@baseten": {"input_tokens": Decimal("1.25") / 1_000_000,
                                "output_tokens": Decimal("4.25") / 1_000_000},
    "sam-3.1": {"images": Decimal("2.50") / 1_000},
    "muse-voice-transcribe-1.0": {"audio_seconds": Decimal("0.18") / 3_600},
    "muse-glimmer-30b+lora-r1@modal": {"gpu_seconds": Decimal("0.00127284")},
}


def cost_usd(
    model_id: str, *, input_tokens: int = 0, output_tokens: int = 0,
    audio_ms: int | None = None, images: int | None = None,
    gpu_ms: int | None = None,
) -> Decimal:
    rates = _PRICES[model_id]
    if any(value < 0 for value in (input_tokens, output_tokens, audio_ms or 0, images or 0,
                                   gpu_ms or 0)):
        raise ValueError("usage cannot be negative")
    return (
        rates.get("input_tokens", Decimal(0)) * input_tokens
        + rates.get("output_tokens", Decimal(0)) * output_tokens
        + rates.get("images", Decimal(0)) * (images or 0)
        + rates.get("audio_seconds", Decimal(0)) * (((audio_ms or 0) + 999) // 1000)
        + rates.get("gpu_seconds", Decimal(0)) * (((gpu_ms or 0) + 999) // 1000)
    )
