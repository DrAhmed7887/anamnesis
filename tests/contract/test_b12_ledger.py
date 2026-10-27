"""Batch 12 (B12a) contract: ledger integrity and retries (QM M2 #8 blocker, #4; M2 F-07). Written by the reviewer.

Do not edit. Rule: a call that may have been billed is always on the ledger. Timeouts, transport errors after
sending, 5xx and malformed 200 bodies charge the pre-call estimate (marked "estimated"); 4xx and 429 are rejected
before any work and charge nothing. Voice, SAM and Spark each retry once; the returned trace keeps every attempt.
"""

import io
import json
import wave
from decimal import Decimal

import httpx
import pytest

from anamnesis.providers import ProviderError, SpendCapExceeded, SpendGuard
from anamnesis.providers.claims import MetaClaimExtractor
from anamnesis.providers.meta import (
    MetaClient,
    MetaLabelReader,
    MetaSegmenter,
    MetaTranscriber,
    spark_call_estimate,
)
from anamnesis.schema import AudioTurn, ImageRegion


def wav(seconds=2.0):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00" * int(seconds * 16000) * 2)
    return buf.getvalue()


class Script:
    """Fake Meta API: each step is (status, json) or an exception instance to raise."""

    def __init__(self, *steps):
        self.steps, self.requests = list(steps), []

    def __call__(self, request):
        self.requests.append(request)
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        status, body = step
        return httpx.Response(status, json=body)


def client(script):
    return MetaClient(api_key="LLM_t_s", transport=httpx.MockTransport(script))


@pytest.fixture
def guard(tmp_path):
    return SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal("5.00"))


def lines(g):
    p = g.ledger_path
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


VOICE_OK = {"audioDurationMs": 2000, "turns": [
    {"turnId": 0, "startMs": 0, "endMs": 1900, "transcript": "Concor five", "speaker": "A"}]}
SAM_OK = {"id": "resp_2", "output": [{"type": "message", "content": [{"type": "output_text", "text":
          "<0f>0<|box;x1=1;y1=1;x2=5;y2=5;w=10;h=10;c=0.9|><|mask;x=0;y=0;c=0.9;data=2,2,!ab|>\n"}]}]}
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
REGION = ImageRegion(region_id="r-0", image_sha256="a" * 64, object_id=0, x1=1, y1=1, x2=5, y2=5,
                     frame_w=10, frame_h=10)
LABEL = json.dumps({"label_text": "Concor 5 mg", "inn": "bisoprolol", "readability": "readable", "country": None,
                    "strength": None})


def chat(content, cid="chat_x", usage=(1000, 200)):
    return {"id": cid, "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": usage[0], "completion_tokens": usage[1]}}


# --- Voice and SAM retry once on billable-uncertain failures -------------------------------------

def test_voice_retries_after_a_5xx_and_the_5xx_is_on_the_ledger(guard):
    s = Script((503, {"error": {"message": "busy"}}), (200, VOICE_OK))
    turns, trace = MetaTranscriber(client(s), guard).transcribe(wav())
    assert len(turns) == 1 and len(s.requests) == 2
    first, second = lines(guard)
    assert first["estimated"] is True and "503" in first["reason"] and Decimal(first["cost_usd"]) == Decimal("0.0001")
    assert second.get("estimated", False) is False
    assert len(trace.prior_call_ids) == 1 and trace.prior_cost_usd == Decimal("0.0001")


def test_sam_retries_after_a_timeout_and_the_timeout_is_on_the_ledger(guard):
    s = Script(httpx.ReadTimeout("slow"), (200, SAM_OK))
    regions, trace = MetaSegmenter(client(s), guard).segment(PNG, "label", mime="image/png")
    assert len(regions) == 1 and len(s.requests) == 2
    first, _ = lines(guard)
    assert first["estimated"] is True and "timeout" in first["reason"].lower()
    assert Decimal(first["cost_usd"]) == Decimal("0.0025")
    assert trace.prior_cost_usd == Decimal("0.0025") and trace.cost_usd == Decimal("0.0025")


def test_two_timeouts_raise_and_both_are_charged(guard):
    s = Script(httpx.ReadTimeout("slow"), httpx.ReadTimeout("slow"))
    with pytest.raises(ProviderError) as e:
        MetaSegmenter(client(s), guard).segment(PNG, "label", mime="image/png")
    assert e.value.retryable is True
    assert [x["estimated"] for x in lines(guard)] == [True, True]


@pytest.mark.parametrize("status", [400, 401, 402, 404])
def test_rejected_requests_are_not_retried_or_charged(status, guard):
    s = Script((status, {"error": {"message": "no"}}))
    with pytest.raises(ProviderError):
        MetaTranscriber(client(s), guard).transcribe(wav())
    assert len(s.requests) == 1 and lines(guard) == []


def test_rate_limits_retry_once_but_charge_nothing(guard):
    s = Script((429, {"error": {"message": "slow down"}}), (429, {"error": {"message": "slow down"}}))
    with pytest.raises(ProviderError):
        MetaSegmenter(client(s), guard).segment(PNG, "label", mime="image/png")
    assert len(s.requests) == 2 and lines(guard) == []


def test_malformed_200_body_is_charged_at_the_estimate(guard):
    s = Script((200, {"unexpected": True}), (200, SAM_OK))
    MetaSegmenter(client(s), guard).segment(PNG, "label", mime="image/png")
    first, _ = lines(guard)
    assert first["estimated"] is True


# --- Spark keeps every attempt in the returned trace ------------------------------------------------------

def test_spark_retry_trace_keeps_the_first_attempt(guard):
    s = Script((200, chat("not json", cid="chat_1")), (200, chat(LABEL, cid="chat_2")))
    reading, trace = MetaLabelReader(client(s), guard).read(PNG, REGION, mime="image/png")
    assert trace.call_id == "chat_2" and trace.prior_call_ids == ["chat_1"]
    assert trace.prior_cost_usd == Decimal("0.00125") + Decimal("0.00085")
    assert [x.get("estimated", False) for x in lines(guard)] == [False, False]  # both real, both on the ledger


def test_claim_extractor_charges_a_timeout_then_succeeds(guard):
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=10, transcript="Concor five")]
    body = json.dumps({"claims": []})
    s = Script(httpx.ReadTimeout("slow"), (200, chat(body)))
    claims, trace = MetaClaimExtractor(client(s), guard).extract(turns)
    first, second = lines(guard)
    bound = spark_call_estimate(json.loads(s.requests[0].content))  # batch 18: the request's upper bound
    assert first["estimated"] is True and Decimal(first["cost_usd"]) == bound
    assert trace.prior_cost_usd == bound


# --- the cap counts estimated charges ---------------------------------------------------------------------

def test_estimated_charges_count_toward_the_cap(tmp_path):
    g = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal("0.004"))
    s = Script(httpx.ReadTimeout("slow"), (200, SAM_OK))
    with pytest.raises(SpendCapExceeded):  # 0.0025 estimated + 0.0025 next attempt > 0.004
        MetaSegmenter(client(s), g).segment(PNG, "label", mime="image/png")
    assert len(s.requests) == 1 and g.total_usd == Decimal("0.0025")


def test_ledger_lines_say_what_they_are(guard):
    s = Script((503, {"error": {"message": "busy"}}), (200, VOICE_OK))
    MetaTranscriber(client(s), guard).transcribe(wav())
    for line in lines(guard):
        assert {"call_id", "model_id", "cost_usd", "time_utc", "estimated"} <= set(line)
        assert line["model_id"] == "muse-voice-transcribe-1.0"
