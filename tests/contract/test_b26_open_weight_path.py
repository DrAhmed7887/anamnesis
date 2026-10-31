"""Batch 26 contract: the tuned Glimmer on Modal as an optional claim extractor, and Muse Spark Open on
Fireworks as an optional label reader (SPEC §4, "Open-weight claim extractor and the Fireworks reader")."""

import importlib.util
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.providers import ProviderError, SpendCapExceeded, SpendGuard, cost_usd
from anamnesis.providers.claims import CLAIMS_SCHEMA, MetaClaimExtractor, parse_claims_json
from anamnesis.providers.glimmer import GLIMMER_MODEL_ID, GLIMMER_TIMEOUT_S, GlimmerClaimExtractor
from anamnesis.providers.meta import MetaClient, MetaLabelReader
from anamnesis.providers.openweight import PRESETS, OpenWeightClient, OpenWeightLabelReader
from anamnesis.schema import AudioTurn
from finetune import glimmer
from finetune.common import SYSTEM_CONTENT, format_turns

ROOT = Path(__file__).resolve().parents[2]
TOKEN = "wk-contract1.ws-contract2"
URL = "https://example--anamnesis-glimmer-serve-server-web.modal.run"
TURNS = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=3200,
                   transcript="I take Concor five milligrams once a day.")]
CLAIM = {
    "name_text": "Concor", "inn": None, "strength": None,
    "intake_amount": {"inn": "bisoprolol", "amount": "5", "unit": "mg"},
    "regimen": {"units_per_intake": None, "intakes_per_day": "1", "as_needed": None},
    "status": "active", "turn_ids": ["turn-0"],
}
ESTIMATE = cost_usd(GLIMMER_MODEL_ID, gpu_ms=int(GLIMMER_TIMEOUT_S * 1000))


def _payload(**change: object) -> dict:
    return {"id": "glimmer-call-1", "reply": json.dumps({"claims": [CLAIM]}), "opened_answer": True,
            "first_finish": "stop", "answer_finish": "stop", "prompt_tokens": 1200, "completion_tokens": 150,
            **change}


def _extractor(tmp_path: Path, replies: list, cap: Decimal = Decimal(5)):
    """The extractor on a fake Modal endpoint. Each request takes the next reply: a dict (200) or a status."""
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


def test_the_served_prompt_is_the_trained_prompt(tmp_path):
    extractor, _, seen = _extractor(tmp_path, [_payload()])
    extractor.extract(TURNS)
    (request,) = seen
    assert request.method == "POST" and request.url.path.endswith("/extract")
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    body = json.loads(request.content)
    assert body == {"messages": [{"role": "system", "content": SYSTEM_CONTENT},
                                 {"role": "user", "content": format_turns(TURNS)}],
                    "schema": CLAIMS_SCHEMA, "max_tokens": 16000}


def test_no_turns_make_no_call(tmp_path):
    extractor, guard, seen = _extractor(tmp_path, [_payload()])
    assert extractor.extract([]) == ([], None)
    assert seen == [] and guard.total_usd == 0


def test_a_reply_meets_the_products_checks_and_names_the_model(tmp_path):
    extractor, guard, _ = _extractor(tmp_path, [_payload()])
    claims, trace = extractor.extract(TURNS)
    want = parse_claims_json(json.dumps({"claims": [CLAIM]}), TURNS)
    assert [c.model_dump() for c in claims] == [c.model_dump() for c in want]
    assert trace.model_id == GLIMMER_MODEL_ID == "muse-glimmer-30b+lora-r1@modal"
    assert (trace.call_id, trace.input_tokens, trace.output_tokens) == ("glimmer-call-1", 1200, 150)
    assert trace.cost_usd == cost_usd(GLIMMER_MODEL_ID, gpu_ms=trace.latency_ms)
    assert guard.total_usd == trace.cost_usd


@pytest.mark.parametrize("reply", [
    json.dumps({"claims": [{**CLAIM, "name_text": "Lipitor"}]}),  # a name the patient never said
    json.dumps({"claims": [{**CLAIM, "name_text": "Concor, take it with food"}]}),  # a name with advice in it
    "not json",
])
def test_a_reply_the_checks_reject_gives_no_claims_after_one_retry(tmp_path, reply):
    extractor, guard, seen = _extractor(tmp_path, [_payload(reply=reply)])
    with pytest.raises(ProviderError) as caught:
        extractor.extract(TURNS)
    assert caught.value.provider == "modal" and len(seen) == 2
    assert TOKEN not in str(caught.value)


@pytest.mark.parametrize("change", [
    {"reply": None, "opened_answer": False, "first_finish": "length", "answer_finish": None},
    {"reply": '{"claims": [', "answer_finish": "length"},
])
def test_a_length_stop_gives_no_claims_and_no_retry(tmp_path, change):
    extractor, guard, seen = _extractor(tmp_path, [_payload(**change)])
    with pytest.raises(ProviderError) as caught:
        extractor.extract(TURNS)
    assert caught.value.provider == "modal" and not caught.value.retryable
    assert len(seen) == 1
    assert len((tmp_path / "ledger.jsonl").read_text(encoding="utf-8").splitlines()) == 1  # from its trace


def test_a_reply_with_no_answer_retries_once(tmp_path):
    extractor, _, seen = _extractor(tmp_path, [_payload(reply=None, opened_answer=False, answer_finish=None)])
    with pytest.raises(ProviderError) as caught:
        extractor.extract(TURNS)
    assert caught.value.provider == "modal" and len(seen) == 2


@pytest.mark.parametrize("change", [{"id": ""}, {"prompt_tokens": "1200"}, {"reply": 5}, {"opened_answer": None}])
def test_a_malformed_reply_is_retried_and_charged_as_an_estimate(tmp_path, change):
    payload = {key: value for key, value in _payload(**change).items()}
    extractor, guard, seen = _extractor(tmp_path, [payload])
    with pytest.raises(ProviderError):
        extractor.extract(TURNS)
    assert len(seen) == 2 and guard.total_usd == 2 * ESTIMATE


def test_a_401_is_not_retried_or_charged(tmp_path):
    extractor, guard, seen = _extractor(tmp_path, [401])
    with pytest.raises(ProviderError) as caught:
        extractor.extract(TURNS)
    assert caught.value.provider == "modal" and len(seen) == 1 and guard.total_usd == 0
    assert TOKEN not in str(caught.value)


def test_a_5xx_retries_once_and_is_charged_as_estimates(tmp_path):
    extractor, guard, seen = _extractor(tmp_path, [503, 503])
    with pytest.raises(ProviderError) as caught:
        extractor.extract(TURNS)
    assert len(seen) == 2 and guard.total_usd == 2 * ESTIMATE
    assert TOKEN not in str(caught.value)


def test_the_guard_checks_the_whole_timeout_before_the_request(tmp_path):
    extractor, _, seen = _extractor(tmp_path, [_payload()], cap=ESTIMATE - Decimal("0.00001"))
    with pytest.raises(SpendCapExceeded):
        extractor.extract(TURNS)
    assert seen == []


def test_the_price_is_the_evals_list_price_per_second_rounded_up():
    rate = glimmer.usd_per_s(True)
    assert rate == Decimal("0.00127284")
    assert cost_usd(GLIMMER_MODEL_ID, gpu_ms=1) == rate
    assert cost_usd(GLIMMER_MODEL_ID, gpu_ms=2001) == 3 * rate
    assert cost_usd(GLIMMER_MODEL_ID, gpu_ms=0) == 0
    assert GLIMMER_TIMEOUT_S == 120.0
    with pytest.raises(ValueError):
        cost_usd(GLIMMER_MODEL_ID, gpu_ms=-1)


# The live script: which providers each flag builds, and the guards that run before any call.
def _intake_live():
    spec = importlib.util.spec_from_file_location("intake_live_b26", ROOT / "scripts/intake_live.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Built(Exception):
    pass


def _providers(monkeypatch, tmp_path, **clients):
    il = _intake_live()

    def capture(*_args, **kwargs):
        raise _Built(kwargs)

    monkeypatch.setattr(il, "run_intake", capture)
    run = il.Run(SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal(1)), MetaClient("k"), load_catalogue(),
                 Decimal("0.25"), 3, tmp_path, tmp_path, **clients)
    with pytest.raises(_Built) as built:
        il.intake(run, "x", b"", [(b"", "image/png")], "en")
    return built.value.args[0]


def test_without_flags_spark_does_both_steps(monkeypatch, tmp_path):
    kwargs = _providers(monkeypatch, tmp_path)
    assert isinstance(kwargs["extractor"], MetaClaimExtractor)
    assert isinstance(kwargs["reader"], MetaLabelReader)


@pytest.mark.parametrize("provider", ["fireworks", "baseten"])
def test_an_open_weight_reader_reads_with_json_mode_off(monkeypatch, tmp_path, provider):
    client = OpenWeightClient("k", base_url=PRESETS[provider]["base_url"], provider=provider)
    kwargs = _providers(monkeypatch, tmp_path, open_client=client)
    reader = kwargs["reader"]
    assert isinstance(reader, OpenWeightLabelReader) and isinstance(kwargs["extractor"], MetaClaimExtractor)
    assert (reader.model, reader.price_key, reader.json_mode) == (
        PRESETS[provider]["model"], f"muse-spark-open@{provider}", False)
    assert PRESETS["fireworks"]["json_mode"] is True  # the comparison's preset stays as it ran


def test_the_glimmer_flag_builds_the_glimmer_extractor(monkeypatch, tmp_path):
    client = OpenWeightClient(TOKEN, base_url=URL, provider="modal")
    kwargs = _providers(monkeypatch, tmp_path, glimmer_client=client)
    assert isinstance(kwargs["extractor"], GlimmerClaimExtractor)
    assert isinstance(kwargs["reader"], MetaLabelReader)


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
COMMONS = str(ROOT / "evidence/raw/media/public/commons/concor_nanolek_02.jpg")


def test_glimmer_needs_a_staged_case(monkeypatch):
    assert "--case" in _refused(monkeypatch, ["--extractor", "glimmer", "--glimmer-url", URL])


@pytest.mark.parametrize("voice", [
    "/tmp/U1.wav",
    str(ROOT / "evidence/raw/media/real/U1.wav"),
    str(ROOT / "evidence/raw/media/public/voice/../../real/U1.wav"),
])
def test_glimmer_refuses_any_voice_note_but_the_synthetic_ones(monkeypatch, voice):
    message = _refused(monkeypatch, ["--case", "U1", "--voice", voice, "--extractor", "glimmer",
                                     "--glimmer-url", URL])
    assert "may go to Modal" in message


@pytest.mark.parametrize("url", [None, "http://example.modal.run", "https://example.com", "https://modal.run.evil.io"])
def test_glimmer_refuses_a_url_off_modal(monkeypatch, url):
    argv = ["--case", "U1", "--voice", VOICE, "--extractor", "glimmer"]
    message = _refused(monkeypatch, argv + (["--glimmer-url", url] if url else []))
    assert "modal.run" in message


def test_fireworks_needs_a_staged_case(monkeypatch):
    assert "--case" in _refused(monkeypatch, ["--reader", "fireworks"])


@pytest.mark.parametrize("photo", ["/tmp/p1.jpg", str(ROOT / "evidence/raw/media/public/dailymed/x.jpg")])
def test_fireworks_refuses_any_photo_but_the_public_ones(monkeypatch, photo):
    message = _refused(monkeypatch, ["--case", "U1", "--voice", VOICE, "--reader", "fireworks",
                                     "--photo", COMMONS, "--photo", photo])
    assert "may go to Fireworks" in message


# The server: safety properties that must hold in its source (it needs Modal and a GPU to run).
def test_the_server_reuses_the_eval_and_stays_private_and_small():
    source = (ROOT / "finetune/modal_serve.py").read_text(encoding="utf-8")
    assert "requires_proxy_auth=True" in source and "unauthenticated" not in source
    assert re.search(r"max_containers\s*=\s*1\b", source)
    assert not re.search(r"min_containers\s*=\s*[1-9]", source)
    assert re.search(r"scaledown_window\s*=\s*600\b", source)
    assert "_two_passes(" in source and "/runs/r1/adapter" in source
