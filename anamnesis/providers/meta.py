"""Live Meta Model API adapters, with local spend checks before each call."""

import base64
import hashlib
import io
import json
import re
import time
import uuid
import wave
from decimal import Decimal
from typing import Any

import httpx

from anamnesis.providers.base import ProviderError, ProviderTrace, cost_usd, with_one_retry
from anamnesis.providers.sam import parse_sam_output
from anamnesis.providers.spark import LabelReading, parse_label_json
from anamnesis.providers.spend import SpendGuard
from anamnesis.providers.voice import parse_transcribe_response
from anamnesis.schema import AudioTurn, ImageRegion, Readability, Release, StrengthPer, Unit

SPARK_CALL_ESTIMATE_USD = Decimal("0.03")
_VOICE_MODEL = "muse-voice-transcribe-1.0"
_SAM_MODEL = "sam-3.1"
_SYSTEM_PROMPT = (
    "Read only what is printed on the pack inside the given box. "
    "Give no advice. Use unreadable or partial rather than guessing."
)

# Keep every nested property inline: Meta's strict structured output rejects recursive schemas.
LABEL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["label_text", "inn", "country", "readability", "strength"],
    "properties": {
        "label_text": {"type": ["string", "null"]},
        "inn": {"type": ["string", "null"]},
        "country": {"type": ["string", "null"]},
        "readability": {"type": "string", "enum": [item.value for item in Readability]},
        "strength": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "required": ["ingredients", "per", "release"],
            "properties": {
                "ingredients": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["inn", "amount", "unit"],
                        "properties": {
                            "inn": {"type": "string"},
                            "amount": {"type": "string"},
                            "unit": {"type": "string", "enum": [item.value for item in Unit]},
                        },
                    },
                },
                "per": {"type": "string", "enum": [item.value for item in StrengthPer]},
                "release": {"type": "string", "enum": [item.value for item in Release]},
            },
        },
    },
}


def _data_url(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _trace(call_id: str, model: str, latency_ms: int, *, cost: Decimal,
           input_tokens: int = 0, output_tokens: int = 0) -> ProviderTrace:
    return ProviderTrace(
        call_id=call_id, model_id=model, latency_ms=latency_ms,
        input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost,
    )


class MetaClient:
    def __init__(self, api_key: str, base_url: str = "https://api.meta.ai/v1",
                 transport: httpx.BaseTransport | None = None, timeout: float = 30.0) -> None:
        self._api_key = api_key
        self._http = httpx.Client(
            base_url=base_url.rstrip("/") + "/", transport=transport, timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        )

    def __repr__(self) -> str:
        return "MetaClient()"

    def close(self) -> None:
        self._http.close()

    def _safe(self, message: str) -> str:
        return message.replace(self._api_key, "[redacted]") if self._api_key else message

    def post(self, path: str, **kwargs: Any) -> tuple[dict[str, Any], int]:
        start = time.monotonic()
        try:
            response = self._http.post(path.lstrip("/"), **kwargs)
        except httpx.TimeoutException as exc:
            message = self._safe(f"Meta request timed out: {exc}")
            raise ProviderError(
                "meta", message, retryable=True, billable_uncertain=True,
                estimated_reason="timeout",
            ) from None
        except httpx.RequestError as exc:
            raise ProviderError(
                "meta", self._safe(f"Meta request failed: {exc}"), retryable=True,
                billable_uncertain=True, estimated_reason="transport error",
            ) from None
        latency_ms = max(0, int((time.monotonic() - start) * 1000))
        if response.is_error:
            try:
                error = response.json().get("error", {})
                message = error.get("message", response.text) if isinstance(error, dict) else response.text
            except (ValueError, TypeError, AttributeError):
                message = response.text
            raise ProviderError(
                "meta", self._safe(f"Meta HTTP {response.status_code}: {message}"),
                retryable=response.status_code == 429 or response.status_code >= 500,
                billable_uncertain=response.status_code >= 500,
                estimated_reason=f"http {response.status_code}",
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError(
                "meta", "malformed Meta response JSON", retryable=True,
                billable_uncertain=True, estimated_reason="malformed response JSON",
            ) from exc
        if not isinstance(payload, dict):
            raise ProviderError(
                "meta", "malformed Meta response object", retryable=True,
                billable_uncertain=True, estimated_reason="malformed response object",
            )
        return payload, latency_ms


def wav_duration_ms(data: bytes) -> int:
    try:
        with wave.open(io.BytesIO(data), "rb") as audio:
            return audio.getnframes() * 1000 // audio.getframerate()
    except (EOFError, ValueError, wave.Error, ZeroDivisionError) as exc:
        raise ProviderError("voice", "invalid WAV audio") from exc


class MetaTranscriber:
    def __init__(self, client: MetaClient, guard: SpendGuard) -> None:
        self.client = client
        self.guard = guard

    def transcribe(self, wav: bytes, *, language_bias: list[str] | None = None,
                   keywords: list[str] | None = None,
                   lang_hint: str | None = None) -> tuple[list[AudioTurn], ProviderTrace]:
        try:
            if wav[:4] != b"RIFF" or wav[8:12] != b"WAVE":
                raise ValueError("expected RIFF/WAVE")
            with wave.open(io.BytesIO(wav), "rb") as audio:
                if (audio.getnchannels() != 1 or audio.getsampwidth() != 2
                        or audio.getframerate() not in (16000, 24000)
                        or audio.getcomptype() != "NONE"):
                    raise ValueError("expected mono 16-bit PCM at 16 or 24 kHz")
                frames = audio.getnframes()
                rate = audio.getframerate()
                duration = frames * 1000 // rate
            if frames > rate * 600 or len(wav) > 32_000_000:
                raise ValueError("audio exceeds file endpoint limits")
        except (EOFError, ValueError, wave.Error, ZeroDivisionError) as exc:
            raise ProviderError("voice", f"unsupported WAV audio: {exc}") from exc

        estimate = cost_usd(_VOICE_MODEL, audio_ms=duration)
        request: dict[str, Any] = {
            "model": _VOICE_MODEL, "audioEncoding": "WAV", "mode": "ENDPOINTING",
        }
        if language_bias is not None:
            request["languageBias"] = language_bias
        if keywords is not None:
            request["keywords"] = keywords
        def attempt() -> tuple[list[AudioTurn], ProviderTrace]:
            self.guard.check(estimate)
            payload, latency_ms = self.client.post("/asr/transcribe", files={
                "request": (None, json.dumps(request), "application/json"),
                "audio": ("recording.wav", wav, "audio/wav"),
            })
            try:
                turns = parse_transcribe_response(payload, lang_hint)
                call_id = str(payload.get("id") or uuid.uuid4())
                cost = cost_usd(_VOICE_MODEL, audio_ms=int(payload["audioDurationMs"]))
            except (ProviderError, KeyError, TypeError, ValueError) as exc:
                raise ProviderError(
                    "voice", "malformed transcription response", retryable=True,
                    billable_uncertain=True, estimated_reason="malformed Voice response",
                ) from exc
            trace = _trace(call_id, _VOICE_MODEL, latency_ms, cost=cost)
            self.guard.charge_prechecked(trace)
            return turns, trace

        return with_one_retry(
            attempt, guard=self.guard, model_id=_VOICE_MODEL, estimate=estimate,
        )


class MetaSegmenter:
    def __init__(self, client: MetaClient, guard: SpendGuard) -> None:
        self.client = client
        self.guard = guard

    def segment(self, image: bytes, concept: str, *, mime: str) -> tuple[list[ImageRegion], ProviderTrace]:
        words = concept.strip().split()
        if (not 1 <= len(words) <= 4 or "," in concept
                or re.search(r"\b(?:and|or)\b", concept, re.IGNORECASE)):
            raise ProviderError("sam", "concept must be one short noun phrase")
        estimate = cost_usd(_SAM_MODEL, images=1)
        body = {
            "model": _SAM_MODEL,
            "input": [{"type": "message", "role": "user", "content": [
                {"type": "input_text", "text": concept},
                {"type": "input_image", "image_url": _data_url(image, mime)},
            ]}],
            "metadata": {"include_confidence": "true"},
        }

        def attempt() -> tuple[list[ImageRegion], ProviderTrace]:
            self.guard.check(estimate)
            payload, latency_ms = self.client.post("/responses", json=body)
            try:
                output = payload["output"]
                text = "".join(
                    part["text"] for item in output for part in item.get("content", [])
                    if part.get("type") == "output_text"
                )
                call_id = payload["id"]
                if not isinstance(call_id, str) or not call_id:
                    raise ValueError("missing id")
            except (KeyError, TypeError, AttributeError, ValueError) as exc:
                raise ProviderError(
                    "sam", "malformed SAM response", retryable=True,
                    billable_uncertain=True, estimated_reason="malformed SAM response",
                ) from exc
            try:
                regions = parse_sam_output(text, hashlib.sha256(image).hexdigest())
            except ProviderError as exc:
                raise ProviderError(
                    exc.provider, self.client._safe(str(exc)), retryable=True,
                    billable_uncertain=True, estimated_reason="malformed SAM output",
                ) from None
            trace = _trace(call_id, _SAM_MODEL, latency_ms, cost=estimate)
            self.guard.charge_prechecked(trace)
            return regions, trace

        return with_one_retry(attempt, guard=self.guard, model_id=_SAM_MODEL, estimate=estimate)


class MetaLabelReader:
    def __init__(self, client: MetaClient, guard: SpendGuard, model: str = "muse-spark-1.3") -> None:
        if model.endswith("-contributor"):
            raise ValueError("contributor models are not permitted")
        self.client = client
        self.guard = guard
        self.model = model

    def read(self, image: bytes, region: ImageRegion, *, mime: str) -> tuple[LabelReading, ProviderTrace]:
        user_text = (
            f"Read the pack in box x1={region.x1}, y1={region.y1}, "
            f"x2={region.x2}, y2={region.y2} on a {region.frame_w}×{region.frame_h} image."
        )
        body = {
            "model": self.model, "reasoning_effort": "low", "max_tokens": 4000,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": _data_url(image, mime)}},
                ]},
            ],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "label_reading", "strict": True, "schema": LABEL_SCHEMA,
            }},
        }

        def attempt() -> tuple[LabelReading, ProviderTrace]:
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
            trace = _trace(call_id, self.model, latency_ms, cost=cost,
                           input_tokens=input_tokens, output_tokens=output_tokens)
            self.guard.charge_prechecked(trace)
            try:
                reading = parse_label_json(content, region.region_id)
            except ProviderError as exc:
                raise ProviderError(
                    exc.provider, self.client._safe(str(exc)), retryable=True,
                    attempt_trace=trace,
                ) from None
            return reading, trace

        return with_one_retry(
            attempt, guard=self.guard, model_id=self.model, estimate=SPARK_CALL_ESTIMATE_USD,
        )


__all__ = [
    "LABEL_SCHEMA", "SPARK_CALL_ESTIMATE_USD", "MetaClient", "MetaLabelReader",
    "MetaSegmenter", "MetaTranscriber", "wav_duration_ms",
]
