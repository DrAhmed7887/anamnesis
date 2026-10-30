"""Batch 26 gaps the contract leaves: GPU pricing, Glimmer request shape and validation."""

import importlib.util
import json
import sys
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from anamnesis.providers import ProviderError, SpendGuard, cost_usd
from anamnesis.providers.claims import _SYSTEM_PROMPT as SPARK_SYSTEM_PROMPT
from anamnesis.providers.claims import MetaClaimExtractor
from anamnesis.providers.glimmer import (
    _SYSTEM_PROMPT,
    GLIMMER_MODEL_ID,
    GLIMMER_TIMEOUT_S,
    GlimmerClaimExtractor,
)
from anamnesis.providers.meta import MetaClient
from anamnesis.providers.openweight import OpenWeightClient
from anamnesis.schema import AudioTurn

ROOT = Path(__file__).resolve().parents[2]
TOKEN = "wk-extra1.ws-extra2"
URL = "https://example--anamnesis-glimmer-serve-server-web.modal.run"
TURNS = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=3200,
                  transcript="I take Concor five milligrams once a day.")]
CLAIM = {
    "name_text": "Concor", "inn": None, "strength": None,
    "intake_amount": {"inn": "bisoprolol", "amount": "5", "unit": "mg"},
    "regimen": {"units_per_intake": None, "intakes_per_day": "1", "as_needed": None},
    "status": "active", "turn_ids": ["turn-0"],
}
RATE = Decimal("0.00127284")


def _payload(**change: object) -> dict:
    return {"id": "glimmer-call-1", "reply": json.dumps({"claims": [CLAIM]}), "opened_answer": True,
            "first_finish": "stop", "answer_finish": "stop", "prompt_tokens": 1200,
            "completion_tokens": 150, **change}


def _extractor(tmp_path: Path, replies: list, cap: Decimal = Decimal(5)):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        reply = replies[min(len(seen), len(replies)) - 1]
        if isinstance(reply, int):
            return httpx.Response(reply, json={"error": {"message": f"echo {TOKEN}"}})
        return httpx.Response(200, json=reply)

    client = OpenWeightClient(api_key=TOKEN, base_url=URL, provider="modal",
                              transport=httpx.MockTransport(handler))
    guard = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=cap)
    return GlimmerClaimExtractor(client, guard), guard, seen


def test_gpu_seconds_round_up_like_audio_seconds():
    assert cost_usd(GLIMMER_MODEL_ID, gpu_ms=0) == 0
    assert cost_usd(GLIMMER_MODEL_ID, gpu_ms=1) == RATE
    assert cost_usd(GLIMMER_MODEL_ID, gpu_ms=1000) == RATE
    assert cost_usd(GLIMMER_MODEL_ID, gpu_ms=1001) == 2 * RATE
    with pytest.raises(ValueError):
        cost_usd(GLIMMER_MODEL_ID, gpu_ms=-1)


def test_other_prices_and_calls_are_unchanged():
    assert cost_usd("muse-spark-1.3", input_tokens=1_000_000) == Decimal("1.25")
    assert cost_usd("muse-voice-transcribe-1.0", audio_ms=1) == Decimal("0.18") / 3600
    assert cost_usd("sam-3.1", images=1) == Decimal("2.50") / 1000


def test_the_system_prompt_is_sparks_plus_the_reasoning_line():
    assert _SYSTEM_PROMPT == SPARK_SYSTEM_PROMPT + "\nReasoning strength: low"


def test_the_user_message_matches_sparks_byte_for_byte(tmp_path):
    def spark_handler(request: httpx.Request) -> httpx.Response:
        spark_seen.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "x", "choices": [{"message": {
            "content": json.dumps({"claims": [CLAIM]})}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}})

    spark_seen: list[dict] = []
    spark = MetaClaimExtractor(
        MetaClient(api_key="k", transport=httpx.MockTransport(spark_handler)),
        SpendGuard(tmp_path / "spark.jsonl", cap_usd=Decimal(5)))
    spark.extract(TURNS)
    extractor, _, seen = _extractor(tmp_path, [_payload()])
    extractor.extract(TURNS)
    assert json.loads(seen[0].content)["messages"][1] == spark_seen[0]["messages"][1]


@pytest.mark.parametrize("change", [
    {"prompt_tokens": True},  # a bool is not an int
    {"completion_tokens": -1},
    {"opened_answer": 1},
    {"first_finish": 5},
    {"answer_finish": 0},
    {"id": None},
])
def test_more_malformed_replies_retry_and_charge_estimates(tmp_path, change):
    estimate = cost_usd(GLIMMER_MODEL_ID, gpu_ms=int(GLIMMER_TIMEOUT_S * 1000))
    extractor, guard, seen = _extractor(tmp_path, [_payload(**change)])
    with pytest.raises(ProviderError) as caught:
        extractor.extract(TURNS)
    assert caught.value.provider == "modal" and caught.value.retryable
    assert len(seen) == 2 and guard.total_usd == 2 * estimate


def test_a_reply_missing_a_field_is_malformed(tmp_path):
    payload = _payload()
    del payload["answer_finish"]
    extractor, guard, seen = _extractor(tmp_path, [payload])
    with pytest.raises(ProviderError) as caught:
        extractor.extract(TURNS)
    assert caught.value.provider == "modal" and caught.value.retryable
    assert len(seen) == 2


def test_a_length_stop_carries_its_trace_and_is_not_retryable(tmp_path):
    extractor, guard, seen = _extractor(tmp_path, [_payload(first_finish="length")])
    with pytest.raises(ProviderError) as caught:
        extractor.extract(TURNS)
    assert caught.value.provider == "modal" and not caught.value.retryable
    assert caught.value.attempt_trace is not None
    assert caught.value.attempt_trace.call_id == "glimmer-call-1"
    assert len(seen) == 1 and guard.total_usd == caught.value.attempt_trace.cost_usd


def test_a_missing_answer_carries_its_trace_and_retries(tmp_path):
    extractor, _, seen = _extractor(tmp_path, [_payload(reply=None, answer_finish=None)])
    with pytest.raises(ProviderError) as caught:
        extractor.extract(TURNS)
    assert caught.value.provider == "modal" and caught.value.retryable
    assert caught.value.attempt_trace is not None and len(seen) == 2


def test_a_rejected_reply_carries_its_trace_and_hides_the_key(tmp_path):
    bad = json.dumps({"claims": [{**CLAIM, "status": TOKEN}]})
    assert TOKEN in bad  # the mock echoes the token, so the redaction check proves something
    extractor, _, seen = _extractor(tmp_path, [_payload(reply=bad)])
    with pytest.raises(ProviderError) as caught:
        extractor.extract(TURNS)
    assert caught.value.provider == "modal" and caught.value.retryable
    assert caught.value.attempt_trace is not None and len(seen) == 2
    assert TOKEN not in str(caught.value)


def _intake_live():
    spec = importlib.util.spec_from_file_location("intake_live_b26_extra", ROOT / "scripts/intake_live.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_printed_timeout_is_the_extractor_clients_own():
    il = _intake_live()
    spark_timed = il.TimedClient(MetaClient(api_key="k"))
    assert il._timeout_ms(spark_timed) == 30000
    modal_timed = il.TimedClient(OpenWeightClient(api_key="k", base_url=URL, provider="modal",
                                                 timeout=GLIMMER_TIMEOUT_S))
    assert il._timeout_ms(modal_timed) == int(GLIMMER_TIMEOUT_S * 1000)


def test_the_docstring_lists_the_new_options():
    text = (ROOT / "scripts/intake_live.py").read_text(encoding="utf-8").split('"""')[1]
    assert "--extractor" in text and "--glimmer-url" in text and "fireworks" in text


def test_the_server_names_the_app_adapter_and_deploy_command():
    source = (ROOT / "finetune/modal_serve.py").read_text(encoding="utf-8")
    assert 'modal.App("anamnesis-glimmer-serve")' in source
    assert 'LoRARequest("r1", 1, "/runs/r1/adapter")' in source
    assert "~/.local/bin/modal deploy finetune/modal_serve.py" in source
    assert "/health" in source and '"ready": True' in source


def _refused(monkeypatch, argv: list[str]) -> str:
    il = _intake_live()

    def no_call(*_args, **_kwargs):
        raise AssertionError("a key was read or a client built before the guard")

    monkeypatch.setattr(il, "keychain", no_call)
    monkeypatch.setattr(il, "MetaClient", no_call)
    monkeypatch.setattr(il, "OpenWeightClient", no_call)
    monkeypatch.delenv("GLIMMER_URL", raising=False)
    monkeypatch.setattr(sys, "argv", ["intake_live.py", *argv])
    with pytest.raises(SystemExit) as stopped:
        il.main()
    return str(stopped.value.code)


VOICE = str(ROOT / "evidence/raw/media/public/voice/U1.wav")


def test_glimmer_refuses_a_symlink_pointing_outside_the_voice_folder(monkeypatch, tmp_path):
    il = _intake_live()
    monkeypatch.setattr(il, "MEDIA", tmp_path / "media")
    voice_dir = tmp_path / "media" / "public" / "voice"
    voice_dir.mkdir(parents=True)
    target = tmp_path / "outside.wav"
    target.write_bytes(b"not a wav, only the path matters for the guard")
    link = voice_dir / "link.wav"
    link.symlink_to(target)

    def no_call(*_args, **_kwargs):
        raise AssertionError("a key was read or a client built before the guard")

    monkeypatch.setattr(il, "keychain", no_call)
    monkeypatch.setattr(il, "MetaClient", no_call)
    monkeypatch.setattr(il, "OpenWeightClient", no_call)
    monkeypatch.delenv("GLIMMER_URL", raising=False)
    monkeypatch.setattr(sys, "argv", ["intake_live.py", "--case", "U1", "--voice", str(link),
                                      "--extractor", "glimmer", "--glimmer-url", URL])
    with pytest.raises(SystemExit) as stopped:
        il.main()
    assert "may go to Modal" in str(stopped.value.code)


def test_glimmer_allows_a_real_file_inside_the_voice_folder(monkeypatch, tmp_path):
    il = _intake_live()
    monkeypatch.setattr(il, "MEDIA", tmp_path / "media")
    voice_dir = tmp_path / "media" / "public" / "voice"
    voice_dir.mkdir(parents=True)
    real = voice_dir / "U1.wav"
    real.write_bytes(b"not a wav, only the path matters for the guard")

    def stop_at_key(_service: str) -> str:
        raise RuntimeError("key read: the voice guard passed")

    def no_client(*_args, **_kwargs):
        raise AssertionError("a client was built before the key read")

    monkeypatch.setattr(il, "keychain", stop_at_key)
    monkeypatch.setattr(il, "MetaClient", no_client)
    monkeypatch.setattr(il, "OpenWeightClient", no_client)
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("GLIMMER_URL", raising=False)
    monkeypatch.setattr(sys, "argv", ["intake_live.py", "--case", "U1", "--voice", str(real),
                                      "--extractor", "glimmer", "--glimmer-url", URL])
    with pytest.raises(RuntimeError, match="key read"):
        il.main()


def test_glimmer_refuses_a_voice2_folder_next_to_voice(monkeypatch):
    voice2 = str(ROOT / "evidence/raw/media/public/voice2/U1.wav")
    message = _refused(monkeypatch, ["--case", "U1", "--voice", voice2,
                                     "--extractor", "glimmer", "--glimmer-url", URL])
    assert "may go to Modal" in message


@pytest.mark.parametrize("url", [
    "https://user@x.modal.run",
    "https://x.modal.run:8443",
    "https://x.modal.run.evil.com",
])
def test_glimmer_refuses_user_port_and_suffix_urls(monkeypatch, url):
    message = _refused(monkeypatch, ["--case", "U1", "--voice", VOICE,
                                     "--extractor", "glimmer", "--glimmer-url", url])
    assert "modal.run" in message


@pytest.mark.parametrize("change", [
    {"first_finish": "abort"},
    {"first_finish": None},
    {"answer_finish": None},
    {"answer_finish": "abort"},
    {"reply": None, "answer_finish": "stop"},
    {"reply": None, "first_finish": "abort", "answer_finish": None},
])
def test_unexpected_stop_reasons_give_no_claims_and_no_retry(tmp_path, change):
    extractor, guard, seen = _extractor(tmp_path, [_payload(**change)])
    with pytest.raises(ProviderError) as caught:
        extractor.extract(TURNS)
    assert caught.value.provider == "modal" and not caught.value.retryable
    assert caught.value.attempt_trace is not None
    assert caught.value.attempt_trace.call_id == "glimmer-call-1"
    assert len(seen) == 1 and guard.total_usd == caught.value.attempt_trace.cost_usd
