"""Batch 26.1 gaps the contract leaves: non-string efforts, the stored default,
the effort under JSON mode and on a retry, and the live script's docstring."""

import ast
import json
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from anamnesis.providers import SpendGuard
from anamnesis.providers.openweight import PRESETS, OpenWeightClient, OpenWeightLabelReader
from anamnesis.schema import ImageRegion

ROOT = Path(__file__).resolve().parents[2]
REGION = ImageRegion(region_id="r0", image_sha256="0" * 64, object_id=0,
                     x1=1, y1=2, x2=10, y2=20, frame_w=100, frame_h=100)
PHOTO = b"not a real photo, just bytes for the mocked endpoint"
REPLY = {"label_text": "Widget 5 mg", "readability": "readable"}


def _reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"id": "cmpl-1", "choices": [{"message": {"content": content},
                                                                   "finish_reason": "stop"}],
                                     "usage": {"prompt_tokens": 1000, "completion_tokens": 500}})


def _reader(tmp_path: Path, replies: list, json_mode: bool = False, **options):
    sent: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return replies[min(len(sent), len(replies)) - 1]

    client = OpenWeightClient(api_key="fw_secret", base_url=PRESETS["fireworks"]["base_url"],
                              provider="fireworks", transport=httpx.MockTransport(handler))
    guard = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal(5))
    reader = OpenWeightLabelReader(client, guard, model=PRESETS["fireworks"]["model"],
                                   price_key="muse-spark-open@fireworks", json_mode=json_mode,
                                   **options)
    return reader, sent


def test_the_default_effort_is_none_and_is_stored(tmp_path):
    reader, _ = _reader(tmp_path, [_reply(json.dumps(REPLY))])
    assert reader.reasoning_effort is None


def test_a_documented_effort_is_stored(tmp_path):
    reader, _ = _reader(tmp_path, [_reply(json.dumps(REPLY))], reasoning_effort="medium")
    assert reader.reasoning_effort == "medium"


@pytest.mark.parametrize("effort", [True, 0.5, b"low", ["low"], {"effort": "low"}, " low", "low ", "Low"])
def test_near_misses_and_non_strings_are_refused_at_construction(tmp_path, effort):
    with pytest.raises(ValueError):
        _reader(tmp_path, [_reply(json.dumps(REPLY))], reasoning_effort=effort)


def test_the_effort_is_added_under_json_mode_too_and_only_it(tmp_path):
    plain, plain_sent = _reader(tmp_path / "a", [_reply(json.dumps(REPLY))], json_mode=True)
    high, high_sent = _reader(tmp_path / "b", [_reply(json.dumps(REPLY))], json_mode=True,
                              reasoning_effort="xhigh")
    plain.read(PHOTO, REGION, mime="image/png")
    high.read(PHOTO, REGION, mime="image/png")
    assert high_sent[0] == {**plain_sent[0], "reasoning_effort": "xhigh"}


def test_the_retry_request_carries_the_effort_as_well(tmp_path):
    reader, sent = _reader(tmp_path, [_reply("not json"), _reply(json.dumps(REPLY))],
                           reasoning_effort="low")
    reader.read(PHOTO, REGION, mime="image/png")
    assert [body.get("reasoning_effort") for body in sent] == ["low", "low"]


def test_the_live_scripts_docstring_says_fireworks_asks_for_low_effort():
    module = ast.parse((ROOT / "scripts/intake_live.py").read_text(encoding="utf-8"))
    docstring = ast.get_docstring(module) or ""
    assert "low reasoning effort" in docstring
