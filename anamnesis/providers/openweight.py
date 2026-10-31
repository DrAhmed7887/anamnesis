"""Open-weight label reader for the zero-shot comparison with Spark 1.3 (SPEC §4, batch 22)."""

import json
from typing import Any

import httpx

from anamnesis.providers.base import ProviderError, ProviderTrace, cost_usd, with_one_retry
from anamnesis.providers.meta import _SYSTEM_PROMPT, LABEL_SCHEMA, MetaClient, _data_url, spark_call_estimate
from anamnesis.providers.spark import LabelReading, parse_label_json
from anamnesis.providers.spend import SpendGuard
from anamnesis.schema import ImageRegion

PRESETS: dict[str, dict[str, Any]] = {
    "fireworks": {
        "base_url": "https://api.fireworks.ai/inference/v1",
        "model": "accounts/fireworks/models/muse-spark-open",
        "json_mode": True,
    },
    "baseten": {
        "base_url": "https://inference.baseten.co/v1",
        "model": "meta-models/muse-spark-open",
        "json_mode": False,
    },
}


def _strip_fence(content: Any) -> Any:
    """Remove one surrounding ``` or ```json fence before parsing."""
    if not isinstance(content, str):
        return content
    text = content.strip()
    if not (text.startswith("```") and text.endswith("```") and len(text) >= 6):
        return content
    if text.startswith("```json"):
        inner = text[len("```json"):]
    else:
        inner = text[len("```"):]
    return inner[: -len("```")].strip()


class OpenWeightClient(MetaClient):
    def __init__(self, api_key: str, base_url: str, provider: str,
                 transport: httpx.BaseTransport | None = None, timeout: float = 60.0) -> None:
        super().__init__(api_key, base_url=base_url, transport=transport, timeout=timeout)
        self.provider = provider

    def __repr__(self) -> str:
        return "OpenWeightClient()"

    def post(self, path: str, **kwargs: Any) -> tuple[dict[str, Any], int]:
        try:
            return super().post(path, **kwargs)
        except ProviderError as exc:
            exc.provider = self.provider
            raise


class OpenWeightLabelReader:
    def __init__(self, client: OpenWeightClient, guard: SpendGuard, *, model: str,
                 price_key: str, json_mode: bool,
                 reasoning_effort: str | None = None) -> None:
        if "-contributor" in model.strip().casefold():
            raise ValueError("contributor models are not permitted")
        if reasoning_effort is not None and reasoning_effort not in ("low", "medium", "high", "xhigh"):
            raise ValueError("reasoning_effort must be None or one of low, medium, high, xhigh")
        self.client = client
        self.guard = guard
        self.model = model
        self.price_key = price_key
        self.json_mode = json_mode
        self.reasoning_effort = reasoning_effort

    def read(self, image: bytes, region: ImageRegion, *, mime: str,
             cropped: bool = False) -> tuple[LabelReading, ProviderTrace]:
        if cropped:
            user_text = "Read the pack in this image, which is a cropped photo of one pack."
        else:
            user_text = (
                f"Read the pack in box x1={region.x1}, y1={region.y1}, "
                f"x2={region.x2}, y2={region.y2} on a {region.frame_w}×{region.frame_h} image."
            )
        if not self.json_mode:
            user_text += (
                " Reply with only one JSON object that matches this JSON schema: "
                + json.dumps(LABEL_SCHEMA, sort_keys=True)
            )
        body: dict[str, Any] = {
            "model": self.model, "max_tokens": 4000,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": _data_url(image, mime)}},
                ]},
            ],
        }
        if self.json_mode:
            body["response_format"] = {"type": "json_schema", "json_schema": {
                "name": "label_reading", "strict": True, "schema": LABEL_SCHEMA,
            }}
        if self.reasoning_effort is not None:
            body["reasoning_effort"] = self.reasoning_effort

        estimate = spark_call_estimate({**body, "model": self.price_key})

        def attempt() -> tuple[LabelReading, ProviderTrace]:
            self.guard.check(estimate)
            payload, latency_ms = self.client.post("/chat/completions", json=body)
            try:
                usage = payload["usage"]
                input_tokens = int(usage["prompt_tokens"])
                output_tokens = int(usage["completion_tokens"])
                content = payload["choices"][0]["message"]["content"]
                call_id = payload["id"]
                if not isinstance(call_id, str) or not call_id:
                    raise ValueError("missing id")
                cost = cost_usd(self.price_key, input_tokens=input_tokens, output_tokens=output_tokens)
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise ProviderError(
                    self.client.provider, "malformed Spark response", retryable=True,
                    billable_uncertain=True, estimated_reason="malformed Spark response",
                ) from exc
            trace = ProviderTrace(
                call_id=call_id, model_id=self.price_key, latency_ms=latency_ms,
                input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost,
            )
            self.guard.charge_prechecked(trace)
            if payload["choices"][0].get("finish_reason") == "length":
                raise ProviderError(
                    self.client.provider, "Spark reply stopped at the length limit",
                    retryable=False, attempt_trace=trace,
                )
            if not self.json_mode:
                content = _strip_fence(content)
            try:
                reading = parse_label_json(content, region.region_id)
            except ProviderError as exc:
                raise ProviderError(
                    self.client.provider, self.client._safe(str(exc)), retryable=True,
                    attempt_trace=trace,
                ) from None
            return reading, trace

        return with_one_retry(attempt, guard=self.guard, model_id=self.price_key, estimate=estimate)


__all__ = ["PRESETS", "OpenWeightClient", "OpenWeightLabelReader"]
