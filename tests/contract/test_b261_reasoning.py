"""Batch 26.1 contract: the open-weight reader can ask for a reasoning effort, and `--reader fireworks` asks for
"low", the effort Spark 1.3's own reader asks for (SPEC §4, "Reasoning effort for the open-weight reader").
Written by the CEO; Muse must not edit it."""

import importlib.util
import json
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.providers import ProviderError, SpendGuard
from anamnesis.providers.meta import MetaClient, spark_call_estimate
from anamnesis.providers.openweight import PRESETS, OpenWeightClient, OpenWeightLabelReader
from tests.contract.test_b19_brief import PHOTO, RC

ROOT = Path(__file__).resolve().parents[2]
LABEL = {"label_text": "Concor 5 mg\nBisoprolol fumarate", "inn": "bisoprolol", "country": None,
         "readability": "readable",
         "strength": {"ingredients": [{"inn": "bisoprolol", "amount": "5", "unit": "mg"}], "per": "tablet",
                      "release": "immediate"}}


def _reply(content: str, finish: str = "stop") -> httpx.Response:
    return httpx.Response(200, json={"id": "cmpl-1", "choices": [{"message": {"content": content},
                                                                   "finish_reason": finish}],
                                     "usage": {"prompt_tokens": 1000, "completion_tokens": 500}})


def _reader(tmp_path: Path, replies: list, **options):
    """A Fireworks reader with JSON mode off, as the live script builds it, on a fake endpoint."""
    sent: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return replies[min(len(sent), len(replies)) - 1]

    client = OpenWeightClient(api_key="fw_secret", base_url=PRESETS["fireworks"]["base_url"], provider="fireworks",
                              transport=httpx.MockTransport(handler))
    guard = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal(5))
    reader = OpenWeightLabelReader(client, guard, model=PRESETS["fireworks"]["model"],
                                   price_key="muse-spark-open@fireworks", json_mode=False, **options)
    return reader, guard, sent


def test_by_default_the_request_is_the_comparisons_with_no_reasoning_effort(tmp_path):
    reader, _, sent = _reader(tmp_path, [_reply(json.dumps(LABEL))])
    reader.read(PHOTO, RC, mime="image/png")
    assert "reasoning_effort" not in sent[0]


def test_an_effort_adds_only_that_field_and_leaves_the_estimate_alone(tmp_path):
    plain, _, plain_sent = _reader(tmp_path / "a", [_reply(json.dumps(LABEL))])
    low, _, low_sent = _reader(tmp_path / "b", [_reply(json.dumps(LABEL))], reasoning_effort="low")
    plain.read(PHOTO, RC, mime="image/png")
    reading, _ = low.read(PHOTO, RC, mime="image/png")
    assert low_sent[0] == {**plain_sent[0], "reasoning_effort": "low"}
    assert spark_call_estimate({**low_sent[0], "model": "muse-spark-open@fireworks"}) == \
        spark_call_estimate({**plain_sent[0], "model": "muse-spark-open@fireworks"})
    assert reading.inn == "bisoprolol"


@pytest.mark.parametrize("effort", ["low", "medium", "high", "xhigh"])
def test_the_documented_efforts_are_accepted(tmp_path, effort):
    reader, _, sent = _reader(tmp_path, [_reply(json.dumps(LABEL))], reasoning_effort=effort)
    reader.read(PHOTO, RC, mime="image/png")
    assert sent[0]["reasoning_effort"] == effort


@pytest.mark.parametrize("effort", ["", "LOW", "max", "minimal", 1])
def test_any_other_effort_is_refused_before_any_call(tmp_path, effort):
    with pytest.raises(ValueError):
        _reader(tmp_path, [_reply(json.dumps(LABEL))], reasoning_effort=effort)


def test_a_length_stop_under_low_is_still_not_retried(tmp_path):
    reader, guard, sent = _reader(tmp_path, [_reply('{"label_text": "Con', finish="length")],
                                  reasoning_effort="low")
    with pytest.raises(ProviderError) as caught:
        reader.read(PHOTO, RC, mime="image/png")
    assert not caught.value.retryable and len(sent) == 1


def test_a_malformed_reply_under_low_is_retried_once(tmp_path):
    reader, _, sent = _reader(tmp_path, [_reply("not json"), _reply(json.dumps(LABEL))], reasoning_effort="low")
    reading, _ = reader.read(PHOTO, RC, mime="image/png")
    assert len(sent) == 2 and reading.inn == "bisoprolol"


# The live script: Fireworks asks for "low"; Baseten and Spark 1.3 are unchanged.
def _intake_live():
    spec = importlib.util.spec_from_file_location("intake_live_b261", ROOT / "scripts/intake_live.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Built(Exception):
    pass


def _reader_built(monkeypatch, tmp_path, provider):
    il = _intake_live()

    def capture(*_args, **kwargs):
        raise _Built(kwargs["reader"])

    monkeypatch.setattr(il, "run_intake", capture)
    client = OpenWeightClient("k", base_url=PRESETS[provider]["base_url"], provider=provider)
    run = il.Run(SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal(1)), MetaClient("k"), load_catalogue(),
                 Decimal("0.25"), 3, tmp_path, tmp_path, open_client=client)
    with pytest.raises(_Built) as built:
        il.intake(run, "x", b"", [(b"", "image/png")], "en")
    return built.value.args[0]


def test_the_fireworks_reader_asks_for_low_effort(monkeypatch, tmp_path):
    reader = _reader_built(monkeypatch, tmp_path, "fireworks")
    assert (reader.json_mode, reader.reasoning_effort) == (False, "low")


def test_the_baseten_reader_asks_for_no_effort(monkeypatch, tmp_path):
    reader = _reader_built(monkeypatch, tmp_path, "baseten")
    assert (reader.json_mode, reader.reasoning_effort) == (False, None)


def test_presets_and_the_timeout_stay_as_they_were():
    assert PRESETS["fireworks"] == {"base_url": "https://api.fireworks.ai/inference/v1",
                                    "model": "accounts/fireworks/models/muse-spark-open", "json_mode": True}
    client = OpenWeightClient("k", base_url=PRESETS["fireworks"]["base_url"], provider="fireworks")
    assert client._http.timeout.read == 60.0
