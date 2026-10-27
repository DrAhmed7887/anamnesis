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


class IntakeSession:
    """Counts provider calls against a budget and records one step per action."""

    def __init__(self, max_provider_calls: int) -> None:
        self.max_provider_calls = max_provider_calls
        self.calls = 0
        self.spend_usd = Decimal(0)
        self.exhausted = False
        self.steps: list[AgentStep] = []

    def note(self, action: AgentAction, target: str, outcome: str, call_ids: list[str] | None = None) -> None:
        self.steps.append(AgentStep(n=len(self.steps), action=action, target=target, outcome=outcome,
                                    call_ids=call_ids or []))

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
            self.note(AgentAction.BUDGET_EXHAUSTED, target, _error_outcome(exc), exc.charged_call_ids)
            return None
        except ProviderError as exc:  # charged attempts of a failed call still count as spend
            self.spend_usd += exc.charged_usd
            self.note(action, target, _error_outcome(exc), exc.charged_call_ids)
            return None
        except ValueError as exc:  # a non-provider error may still follow charged attempts
            self.spend_usd += getattr(exc, "charged_usd", Decimal(0))
            self.note(action, target, _error_outcome(exc), getattr(exc, "charged_call_ids", []))
            return None
        ids = self._charge(trace)
        self.note(action, target, describe(value), ids)
        return value

    def _charge(self, trace: ProviderTrace | None) -> list[str]:
        if trace is None:
            return []
        self.spend_usd += trace.cost_usd + trace.prior_cost_usd
        return [trace.call_id, *trace.prior_call_ids]
