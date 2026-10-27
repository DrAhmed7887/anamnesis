"""Focused offline checks for the live Meta transport boundary."""

import io
import json
import wave
from decimal import Decimal

import httpx
import pytest

from anamnesis.providers import ProviderError, SpendGuard
from anamnesis.providers.meta import LABEL_SCHEMA, MetaClient, MetaTranscriber, wav_duration_ms


def _wav(seconds: int = 1) -> bytes:
    data = io.BytesIO()
    with wave.open(data, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\0" * 32000 * seconds)
    return data.getvalue()


def test_http_error_redacts_key_and_keeps_provider_message(tmp_path):
    key = "LLM_secret_for_test"

    def respond(_request):
        return httpx.Response(403, json={"error": {"message": f"bad key {key}"}})

    client = MetaClient(key, transport=httpx.MockTransport(respond))
    guard = SpendGuard(tmp_path / "ledger", Decimal("1"))
    with pytest.raises(ProviderError) as raised:
        MetaTranscriber(client, guard).transcribe(_wav())
    assert raised.value.retryable is False
    assert "bad key [redacted]" in str(raised.value)
    assert key not in str(raised.value)


def test_timeout_is_retried_and_recorded_as_estimated(tmp_path):
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)

    client = MetaClient("test", transport=httpx.MockTransport(timeout))
    guard = SpendGuard(tmp_path / "ledger", Decimal("1"))
    with pytest.raises(ProviderError) as raised:
        MetaTranscriber(client, guard).transcribe(_wav())
    assert raised.value.retryable is True
    lines = [json.loads(line) for line in guard.ledger_path.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    assert all(line["estimated"] and line["reason"] == "timeout" for line in lines)


def test_wav_duration_and_invalid_header():
    assert wav_duration_ms(_wav(3)) == 3000
    with pytest.raises(ProviderError):
        wav_duration_ms(b"not WAV")


def test_label_schema_is_inline_and_requires_all_fields():
    encoded = json.dumps(LABEL_SCHEMA)
    assert "$ref" not in encoded and "$defs" not in encoded
    assert set(LABEL_SCHEMA["required"]) == {
        "label_text", "inn", "country", "readability", "strength",
    }
    assert LABEL_SCHEMA["properties"]["strength"]["properties"]["ingredients"]["items"][
        "properties"
    ]["amount"]["type"] == "string"
