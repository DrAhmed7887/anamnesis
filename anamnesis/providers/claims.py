"""Muse Spark extraction of patient-reported medication claims."""

import json
from typing import Any

from pydantic import ValidationError

from anamnesis.providers.base import ProviderError, ProviderTrace, cost_usd, with_one_retry
from anamnesis.providers.meta import SPARK_CALL_ESTIMATE_USD, MetaClient
from anamnesis.providers.spend import SpendGuard
from anamnesis.schema import (
    AudioTurn,
    MedicationStatus,
    PatientClaim,
    Release,
    StrengthPer,
    Unit,
)

_SYSTEM_PROMPT = (
    "Extract every medicine the patient mentions, with one claim per medicine. "
    "Copy name_text exactly as spoken. Fill inn only if the patient said the ingredient name; "
    "never infer it from a brand. An amount spoken with a frequency, such as '50 mg twice a day', "
    "is an intake_amount with regimen.intakes_per_day. Use strength only when the patient explicitly "
    "describes the tablet or pack, such as 'the 5 mg tablets'. 'I stopped' or 'no longer take' means "
    "discontinued. If unclear, use unknown. Leave anything not said as null. Cite the turn_ids each "
    "claim comes from. Give no medical advice. Only report what the patient said."
)

_AMOUNT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["inn", "amount", "unit"],
    "properties": {
        "inn": {"type": "string"},
        "amount": {"type": "string"},
        "unit": {"type": "string", "enum": [item.value for item in Unit]},
    },
}

_STRENGTH_SCHEMA: dict[str, Any] = {
    "type": ["object", "null"],
    "additionalProperties": False,
    "required": ["ingredients", "per", "release"],
    "properties": {
        "ingredients": {"type": "array", "items": _AMOUNT_SCHEMA},
        "per": {"type": "string", "enum": [item.value for item in StrengthPer]},
        "release": {"type": "string", "enum": [item.value for item in Release]},
    },
}

_REGIMEN_SCHEMA: dict[str, Any] = {
    "type": ["object", "null"],
    "additionalProperties": False,
    "required": ["units_per_intake", "intakes_per_day", "as_needed"],
    "properties": {
        "units_per_intake": {"type": ["string", "null"]},
        "intakes_per_day": {"type": ["string", "null"]},
        "as_needed": {"type": ["boolean", "null"]},
    },
}

CLAIMS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["claims"],
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name_text", "inn", "strength", "intake_amount", "regimen", "status", "turn_ids",
                ],
                "properties": {
                    "name_text": {"type": "string"},
                    "inn": {"type": ["string", "null"]},
                    "strength": _STRENGTH_SCHEMA,
                    "intake_amount": _AMOUNT_SCHEMA | {"type": ["object", "null"]},
                    "regimen": _REGIMEN_SCHEMA,
                    "status": {"type": "string", "enum": [item.value for item in MedicationStatus]},
                    "turn_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}


def _expect_keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} has an invalid shape")


def _validate_raw_shape(data: Any) -> list[dict[str, Any]]:
    _expect_keys(data, {"claims"}, "claims response")
    claims = data["claims"]
    if not isinstance(claims, list):
        raise ValueError("claims must be an array")
    claim_keys = {
        "name_text", "inn", "strength", "intake_amount", "regimen", "status", "turn_ids",
    }
    amount_keys = {"inn", "amount", "unit"}
    for claim in claims:
        _expect_keys(claim, claim_keys, "claim")
        strength = claim["strength"]
        if strength is not None:
            _expect_keys(strength, {"ingredients", "per", "release"}, "strength")
            if not isinstance(strength["ingredients"], list):
                raise ValueError("strength ingredients must be an array")
            for amount in strength["ingredients"]:
                _expect_keys(amount, amount_keys, "strength ingredient")
        intake_amount = claim["intake_amount"]
        if intake_amount is not None:
            _expect_keys(intake_amount, amount_keys, "intake amount")
        regimen = claim["regimen"]
        if regimen is not None:
            _expect_keys(regimen, {"units_per_intake", "intakes_per_day", "as_needed"}, "regimen")
    return claims


def parse_claims_json(text: str, turns: list[AudioTurn]) -> list[PatientClaim]:
    """Validate Spark JSON and attach only cited transcript turns as evidence."""
    try:
        raw_claims = _validate_raw_shape(json.loads(text))
        known_turn_ids = {turn.turn_id for turn in turns}
        claims = []
        for index, raw in enumerate(raw_claims, start=1):
            turn_ids = raw["turn_ids"]
            invalid_turn_ids = any(
                not isinstance(turn_id, str) or turn_id not in known_turn_ids for turn_id in turn_ids
            ) if isinstance(turn_ids, list) else True
            if not isinstance(turn_ids, list) or not turn_ids or invalid_turn_ids:
                raise ValueError("claim turn_ids must cite existing turns")
            values = {
                **{key: value for key, value in raw.items() if key != "turn_ids"},
                "claim_id": f"c{index}",
                "audio_evidence": turn_ids,
            }
            claims.append(PatientClaim.model_validate(values))
        return claims
    except (TypeError, ValueError, ValidationError) as exc:
        raise ProviderError("spark", f"malformed patient claims: {exc}", retryable=True) from exc


class MetaClaimExtractor:
    def __init__(
        self, client: MetaClient, guard: SpendGuard, model: str = "muse-spark-1.3",
    ) -> None:
        if model.endswith("-contributor"):
            raise ValueError("contributor models are not permitted")
        self.client = client
        self.guard = guard
        self.model = model

    def extract(self, turns: list[AudioTurn]) -> tuple[list[PatientClaim], ProviderTrace | None]:
        if not turns:
            return [], None

        transcript = "\n".join(
            f"[{turn.turn_id} {turn.start_ms}–{turn.end_ms} ms, speaker {turn.speaker or 'unknown'}] "
            f"{turn.transcript}"
            for turn in turns
        )
        body = {
            "model": self.model,
            "reasoning_effort": "low",
            "max_tokens": 4000,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": transcript},
            ],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "patient_claims", "strict": True, "schema": CLAIMS_SCHEMA,
            }},
        }

        def attempt() -> tuple[list[PatientClaim], ProviderTrace]:
            self.guard.check(SPARK_CALL_ESTIMATE_USD)
            payload, latency_ms = self.client.post("/chat/completions", json=body)
            try:
                usage = payload["usage"]
                input_tokens = int(usage["prompt_tokens"])
                output_tokens = int(usage["completion_tokens"])
                content = payload["choices"][0]["message"]["content"]
                call_id = str(payload["id"])
                cost = cost_usd(self.model, input_tokens=input_tokens, output_tokens=output_tokens)
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise ProviderError(
                    "spark", "malformed Spark response", retryable=True,
                    billable_uncertain=True, estimated_reason="malformed Spark response",
                ) from exc
            trace = ProviderTrace(
                call_id=call_id,
                model_id=self.model,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
            )
            self.guard.charge_prechecked(trace)
            try:
                claims = parse_claims_json(content, turns)
            except ProviderError as exc:
                raise ProviderError(
                    exc.provider, self.client._safe(str(exc)), retryable=True,
                    attempt_trace=trace,
                ) from None
            return claims, trace

        return with_one_retry(
            attempt, guard=self.guard, model_id=self.model, estimate=SPARK_CALL_ESTIMATE_USD,
        )
