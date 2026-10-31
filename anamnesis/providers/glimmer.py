"""Tuned Glimmer claim extractor on Modal (SPEC §4, batch 26)."""

from typing import Any

from anamnesis.providers.base import ProviderError, ProviderTrace, cost_usd, with_one_retry
from anamnesis.providers.claims import _SYSTEM_PROMPT as _SPARK_SYSTEM_PROMPT
from anamnesis.providers.claims import CLAIMS_SCHEMA, parse_claims_json
from anamnesis.providers.spend import SpendGuard
from anamnesis.schema import AudioTurn, PatientClaim

GLIMMER_MODEL_ID = "muse-glimmer-30b+lora-r1@modal"
GLIMMER_TIMEOUT_S = 120.0
_SYSTEM_PROMPT = f"{_SPARK_SYSTEM_PROMPT}\nReasoning strength: low"


class GlimmerClaimExtractor:
    def __init__(self, client: Any, guard: SpendGuard) -> None:
        self.client = client
        self.guard = guard

    def extract(
        self, turns: list[AudioTurn],
    ) -> tuple[list[PatientClaim], ProviderTrace | None]:
        if not turns:
            return [], None

        transcript = "\n".join(
            f"[{turn.turn_id} {turn.start_ms}–{turn.end_ms} ms, speaker {turn.speaker or 'unknown'}] "
            f"{turn.transcript}"
            for turn in turns
        )
        body = {
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": transcript},
            ],
            "schema": CLAIMS_SCHEMA,
            "max_tokens": 16000,
        }

        estimate = cost_usd(GLIMMER_MODEL_ID, gpu_ms=int(GLIMMER_TIMEOUT_S * 1000))

        def attempt() -> tuple[list[PatientClaim], ProviderTrace]:
            self.guard.check(estimate)
            payload, latency_ms = self.client.post("/extract", json=body)
            try:
                if not isinstance(payload, dict):
                    raise ValueError("reply is not an object")
                call_id = payload["id"]
                reply = payload["reply"]
                opened_answer = payload["opened_answer"]
                first_finish = payload["first_finish"]
                answer_finish = payload["answer_finish"]
                prompt_tokens = payload["prompt_tokens"]
                completion_tokens = payload["completion_tokens"]
                if not isinstance(call_id, str) or not call_id:
                    raise ValueError("bad id")
                if not (reply is None or isinstance(reply, str)):
                    raise ValueError("bad reply")
                if type(opened_answer) is not bool:
                    raise ValueError("bad opened_answer")
                if not (first_finish is None or isinstance(first_finish, str)):
                    raise ValueError("bad first_finish")
                if not (answer_finish is None or isinstance(answer_finish, str)):
                    raise ValueError("bad answer_finish")
                if type(prompt_tokens) is not int or prompt_tokens < 0:
                    raise ValueError("bad prompt_tokens")
                if type(completion_tokens) is not int or completion_tokens < 0:
                    raise ValueError("bad completion_tokens")
            except (KeyError, TypeError, ValueError) as exc:
                raise ProviderError(
                    "modal", "malformed Modal response", retryable=True,
                    billable_uncertain=True, estimated_reason="malformed Modal response",
                ) from exc
            trace = ProviderTrace(
                call_id=call_id,
                model_id=GLIMMER_MODEL_ID,
                latency_ms=latency_ms,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                cost_usd=cost_usd(GLIMMER_MODEL_ID, gpu_ms=latency_ms),
            )
            self.guard.charge_prechecked(trace)
            if first_finish == "length" or answer_finish == "length":
                raise ProviderError(
                    "modal", "Glimmer reply stopped at the length limit", retryable=False,
                    attempt_trace=trace,
                )
            if first_finish != "stop":
                raise ProviderError(
                    "modal", "Glimmer reply ended without a stop", retryable=False,
                    attempt_trace=trace,
                )
            if reply is None:
                if answer_finish is not None:
                    raise ProviderError(
                        "modal", "Glimmer reply ended without a stop", retryable=False,
                        attempt_trace=trace,
                    )
                raise ProviderError(
                    "modal", "Glimmer reply has no answer", retryable=True,
                    attempt_trace=trace,
                )
            if answer_finish != "stop":
                raise ProviderError(
                    "modal", "Glimmer reply ended without a stop", retryable=False,
                    attempt_trace=trace,
                )
            try:
                claims = parse_claims_json(reply, turns)
            except ProviderError as exc:
                raise ProviderError(
                    "modal", self.client._safe(str(exc)), retryable=True,
                    attempt_trace=trace,
                ) from None
            return claims, trace

        return with_one_retry(attempt, guard=self.guard, model_id=GLIMMER_MODEL_ID, estimate=estimate)


__all__ = ["GLIMMER_MODEL_ID", "GLIMMER_TIMEOUT_S", "GlimmerClaimExtractor"]
