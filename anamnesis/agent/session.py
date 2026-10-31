"""Call budget, spend and step log for one intake. The only mutable state in the loop."""

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from anamnesis.providers.base import ProviderError, ProviderTrace
from anamnesis.providers.spend import SpendCapExceeded
from anamnesis.schema.report import AgentAction, AgentStep


def _error_outcome(exc: Exception) -> str:
    """Describe an error without any provider or model prose."""
    if isinstance(exc, ProviderError):
        return f"error: {exc.provider} {type(exc).__name__}"
    return f"error: {type(exc).__name__}"


def _attempt_fields(attempt: ProviderTrace | None) -> dict[str, Any]:
    if attempt is None:
        return {}
    return {"model_id": attempt.model_id, "input_tokens": attempt.input_tokens,
            "output_tokens": attempt.output_tokens, "latency_ms": attempt.latency_ms}


class IntakeSession:
    """Counts provider calls against a budget and records one step per action."""

    def __init__(self, max_provider_calls: int) -> None:
        self.max_provider_calls = max_provider_calls
        self.calls = 0
        self.spend_usd = Decimal(0)
        self.exhausted = False
        self.steps: list[AgentStep] = []

    def note(self, action: AgentAction, target: str, outcome: str, call_ids: list[str] | None = None,
             model_id: str | None = None, input_tokens: int = 0, output_tokens: int = 0,
             latency_ms: int = 0, cost_usd: Decimal = Decimal(0)) -> None:
        self.steps.append(AgentStep(n=len(self.steps), action=action, target=target, outcome=outcome,
                                    call_ids=call_ids or [], model_id=model_id, input_tokens=input_tokens,
                                    output_tokens=output_tokens, latency_ms=latency_ms, cost_usd=cost_usd))

    def call(self, action: AgentAction, target: str, fn: Callable[[], tuple[Any, ProviderTrace | None]],
             describe: Callable[[Any], str]) -> Any | None:
        """Run one provider call within budget. Returns its value, or None if skipped or failed."""
        if self.exhausted or self.calls >= self.max_provider_calls:
            if not self.exhausted:
                self.exhausted = True
                self.note(AgentAction.BUDGET_EXHAUSTED, action.value,
                          f"max_provider_calls={self.max_provider_calls}")
            return None
        self.calls += 1
        try:
            value, trace = fn()
        except SpendCapExceeded as exc:  # a money cap ends the session, like the call budget
            self.exhausted = True
            self.spend_usd += exc.charged_usd  # attempts charged before the cap refused the next one
            attempt = getattr(exc, "attempt_trace", None)
            self.note(AgentAction.BUDGET_EXHAUSTED, target, _error_outcome(exc), exc.charged_call_ids,
                      **_attempt_fields(attempt), cost_usd=exc.charged_usd)
            return None
        except ProviderError as exc:  # charged attempts of a failed call still count as spend
            self.spend_usd += exc.charged_usd
            self.note(action, target, _error_outcome(exc), exc.charged_call_ids,
                      **_attempt_fields(exc.attempt_trace), cost_usd=exc.charged_usd)
            return None
        except ValueError as exc:  # a non-provider error may still follow charged attempts
            charged = getattr(exc, "charged_usd", Decimal(0))
            self.spend_usd += charged
            self.note(action, target, _error_outcome(exc), getattr(exc, "charged_call_ids", []),
                      **_attempt_fields(getattr(exc, "attempt_trace", None)), cost_usd=charged)
            return None
        ids = self._charge(trace)
        if trace is None:
            self.note(action, target, describe(value), ids)
        else:
            self.note(action, target, describe(value), ids, model_id=trace.model_id,
                      input_tokens=trace.input_tokens, output_tokens=trace.output_tokens,
                      latency_ms=trace.latency_ms, cost_usd=trace.cost_usd + trace.prior_cost_usd)
        return value

    def _charge(self, trace: ProviderTrace | None) -> list[str]:
        if trace is None:
            return []
        self.spend_usd += trace.cost_usd + trace.prior_cost_usd
        return [trace.call_id, *trace.prior_call_ids]
