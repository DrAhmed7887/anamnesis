"""Batch 5 contract: live Meta adapters behind SpendGuard, tested offline with a fake HTTP transport.

Written by the reviewer; do not edit. No test here may touch the network.
"""

import io
import json
import wave
from decimal import Decimal

import httpx
import pytest

from anamnesis.providers import ProviderError, SpendCapExceeded, SpendGuard
from anamnesis.providers.meta import (
    MetaClient,
    MetaLabelReader,
    MetaSegmenter,
    MetaTranscriber,
    wav_duration_ms,
)
from anamnesis.schema import ImageRegion, Readability

KEY = "LLM_test_secret"


def wav(seconds=2.0, rate=16000, channels=1, width=2):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(b"\x00" * int(seconds * rate) * channels * width)
    return buf.getvalue()


class Recorder:
    """Fake Meta API: records requests, replies from a queue."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        status, body = self.responses.pop(0)
        return httpx.Response(status, json=body)


def client(rec):
    return MetaClient(api_key=KEY, transport=httpx.MockTransport(rec))


@pytest.fixture
def guard(tmp_path):
    return SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal("5.00"))


# --- client basics ----------------------------------------------------------------

def test_client_sends_bearer_key_to_meta_base_url(guard):
    rec = Recorder((200, {"audioDurationMs": 2000, "turns": [
        {"turnId": 0, "startMs": 0, "endMs": 1900, "transcript": "Concor five", "speaker": "A"}]}))
    MetaTranscriber(client(rec), guard).transcribe(wav())
    req = rec.requests[0]
    assert str(req.url) == "https://api.meta.ai/v1/asr/transcribe"
    assert req.headers["authorization"] == f"Bearer {KEY}"


def test_key_never_appears_in_errors_or_repr(guard):
    rec = Recorder((401, {"error": {"message": "bad key"}}))
    c = client(rec)
    assert KEY not in repr(c)
    with pytest.raises(ProviderError) as e:
        MetaTranscriber(c, guard).transcribe(wav())
    assert KEY not in str(e.value)


@pytest.mark.parametrize("status,retryable", [(400, False), (401, False), (402, False), (404, False),
                                              (429, True), (500, True), (503, True)])
def test_http_errors_map_to_provider_errors(status, retryable, guard):
    rec = Recorder((status, {"error": {"message": "x"}}), (status, {"error": {"message": "x"}}))
    with pytest.raises(ProviderError) as e:
        MetaTranscriber(client(rec), guard).transcribe(wav())
    assert e.value.retryable is retryable


# --- Voice Transcribe -----------------------------------------------------------------

VOICE_OK = {"audioDurationMs": 2000, "turns": [
    {"turnId": 0, "startMs": 0, "endMs": 1900, "transcript": "I use Concor five", "speaker": "A"}]}


def test_transcribe_posts_wav_multipart_in_endpointing_mode(guard):
    rec = Recorder((200, VOICE_OK))
    turns, trace = MetaTranscriber(client(rec), guard).transcribe(
        wav(), language_bias=["Arabic", "English"], keywords=["Concor", "Beloc-Zok"], lang_hint="ar")
    body = rec.requests[0].content
    assert b'"model": "muse-voice-transcribe-1.0"' in body or b'"model":"muse-voice-transcribe-1.0"' in body
    assert b"ENDPOINTING" in body and b"Beloc-Zok" in body and b"RIFF" in body
    assert [t.turn_id for t in turns] == ["turn-0"] and turns[0].lang_hint == "ar"
    assert trace.model_id == "muse-voice-transcribe-1.0" and trace.cost_usd == Decimal("0.0001")
    assert guard.total_usd == Decimal("0.0001")  # 2 s at $0.18/h, charged to the ledger


@pytest.mark.parametrize("bad", [wav(rate=44100), wav(channels=2), wav(width=1), b"not a wav", wav(seconds=601)])
def test_transcribe_rejects_unsupported_audio_before_any_call(bad, guard):
    rec = Recorder()
    with pytest.raises(ProviderError) as e:
        MetaTranscriber(client(rec), guard).transcribe(bad)
    assert e.value.retryable is False and rec.requests == []


def test_wav_duration():
    assert wav_duration_ms(wav(seconds=2.5)) == 2500


# --- SAM 3.1 --------------------------------------------------------------------------

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
SAM_TEXT = "<0f>0<|box;x1=10;y1=20;x2=200;y2=300;w=640;h=480;c=0.9|><|mask;x=0;y=0;data=2,2,!ab|>"


def responses_body(text):
    return {"id": "resp_1", "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}


def test_segment_posts_one_concept_and_one_image_to_responses(guard):
    rec = Recorder((200, responses_body(SAM_TEXT)))
    regions, trace = MetaSegmenter(client(rec), guard).segment(PNG, "medicine box", mime="image/png")
    req = rec.requests[0]
    sent = json.loads(req.content)
    assert str(req.url) == "https://api.meta.ai/v1/responses" and sent["model"] == "sam-3.1"
    parts = sent["input"][0]["content"]
    assert {"type": "input_text", "text": "medicine box"} in parts
    assert any(p["type"] == "input_image" and p["image_url"].startswith("data:image/png;base64,") for p in parts)
    assert sent["metadata"]["include_confidence"] == "true"  # strings, not booleans (docs)
    assert len(regions) == 1 and isinstance(regions[0], ImageRegion)
    assert trace.call_id == "resp_1" and trace.cost_usd == Decimal("0.0025")
    assert guard.total_usd == Decimal("0.0025")


def test_segment_empty_output_is_zero_regions(guard):
    rec = Recorder((200, responses_body("")))
    regions, _ = MetaSegmenter(client(rec), guard).segment(PNG, "medicine box", mime="image/png")
    assert regions == []


@pytest.mark.parametrize("concept", ["", "box and bottle", "the box on the left, please"])
def test_segment_rejects_non_single_concepts_before_any_call(concept, guard):
    rec = Recorder()
    with pytest.raises(ProviderError):
        MetaSegmenter(client(rec), guard).segment(PNG, concept, mime="image/png")
    assert rec.requests == []


# --- Muse Spark label reading -----------------------------------------------------------

REGION = ImageRegion(region_id="abc-0", image_sha256="a" * 64, object_id=0,
                     x1=10, y1=20, x2=200, y2=300, frame_w=640, frame_h=480)


def chat_body(content, usage=(1000, 200)):
    return {"id": "chat_1", "choices": [{"message": {"role": "assistant", "content": content},
                                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": usage[0], "completion_tokens": usage[1]}}


LABEL = json.dumps({"label_text": "Concor 5 mg", "inn": "bisoprolol", "readability": "readable",
                    "country": None, "strength": {"ingredients": [{"inn": "bisoprolol", "amount": "5",
                                                                   "unit": "mg"}],
                                                  "per": "tablet", "release": "immediate"}})


def test_label_reader_uses_standard_spark_with_strict_json_schema(guard):
    rec = Recorder((200, chat_body(LABEL)))
    reading, trace = MetaLabelReader(client(rec), guard).read(PNG, REGION, mime="image/png")
    sent = json.loads(rec.requests[0].content)
    assert str(rec.requests[0].url) == "https://api.meta.ai/v1/chat/completions"
    assert sent["model"] == "muse-spark-1.3"
    assert sent["response_format"]["type"] == "json_schema"
    assert "$ref" not in json.dumps(sent["response_format"])  # flat schema, no recursion
    assert "x1=10" in json.dumps(sent["messages"]) or "10, 20, 200, 300" in json.dumps(sent["messages"])
    assert reading.region_id == "abc-0" and reading.readability is Readability.READABLE
    assert trace.cost_usd == Decimal("0.00125") + Decimal("0.00085")
    assert guard.total_usd == trace.cost_usd


def test_label_reader_retries_once_on_invalid_json_then_succeeds(guard):
    rec = Recorder((200, chat_body("not json")), (200, chat_body(LABEL)))
    reading, _ = MetaLabelReader(client(rec), guard).read(PNG, REGION, mime="image/png")
    assert reading.label_text == "Concor 5 mg" and len(rec.requests) == 2
    assert len(guard.ledger_path.read_text(encoding="utf-8").splitlines()) == 2  # both calls were paid


def test_label_reader_gives_up_after_one_retry(guard):
    rec = Recorder((200, chat_body("nope")), (200, chat_body("still nope")))
    with pytest.raises(ProviderError):
        MetaLabelReader(client(rec), guard).read(PNG, REGION, mime="image/png")
    assert len(rec.requests) == 2


def test_contributor_models_are_refused_at_construction(guard):
    with pytest.raises(ValueError):
        MetaLabelReader(client(Recorder()), guard, model="muse-spark-1.3-contributor")


# --- the spend cap guards every live call ---------------------------------------------------

def test_spend_cap_blocks_the_call_before_it_is_sent(tmp_path):
    g = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal("0.001"))
    rec = Recorder()
    with pytest.raises(SpendCapExceeded):
        MetaSegmenter(client(rec), g).segment(PNG, "medicine box", mime="image/png")  # $0.0025 > cap
    with pytest.raises(SpendCapExceeded):
        MetaLabelReader(client(rec), g).read(PNG, REGION, mime="image/png")
    assert rec.requests == []
