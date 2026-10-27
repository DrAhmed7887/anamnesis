"""Batch 18 gaps the contract leaves: the estimate helper, the zoom enlarger, and length stops."""

import hashlib
import io
import json
from decimal import Decimal

import httpx
import pytest
from PIL import Image

from anamnesis.agent.crop import enlarge_crop
from anamnesis.providers import ProviderError, SpendGuard
from anamnesis.providers.base import cost_usd
from anamnesis.providers.claims import MetaClaimExtractor
from anamnesis.providers.meta import MetaClient, MetaLabelReader, spark_call_estimate
from anamnesis.schema import AudioTurn, ImageRegion


def _png(w, h):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (200, 200, 200)).save(buf, "PNG")
    return buf.getvalue()


def _size(raw):
    return Image.open(io.BytesIO(raw)).size


def test_estimate_counts_string_content_text_parts_images_and_max_tokens():
    body = {"model": "muse-spark-1.3", "max_tokens": 16000, "messages": [
        {"role": "system", "content": "abcd"},
        {"role": "user", "content": "ef"},
        {"role": "user", "content": [{"type": "text", "text": "gh"},
                                     {"type": "image_url", "image_url": {"url": "data:,"}},
                                     {"type": "image_url", "image_url": {"url": "data:,"}}]},
    ]}
    assert spark_call_estimate(body) == cost_usd("muse-spark-1.3", input_tokens=8 // 2 + 10000,
                                                output_tokens=16000)


def test_enlarge_crop_doubles_a_small_crop_as_png():
    assert _size(enlarge_crop(_png(88, 88))) == (176, 176)


def test_enlarge_crop_caps_the_longest_side_at_2048_px():
    assert _size(enlarge_crop(_png(1650, 880)))[0] == 2048
    assert enlarge_crop(_png(2400, 1200)) is None
    assert enlarge_crop(_png(2048, 100)) is None


IMAGE = _png(200, 100)
REGION = ImageRegion(region_id="r-0", image_sha256=hashlib.sha256(IMAGE).hexdigest(), object_id=0,
                     x1=110, y1=10, x2=189, y2=89, frame_w=200, frame_h=100)
TURNS = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=10, transcript="Concor five")]


def _length_client(seen, content):
    def handler(request):
        seen.append(1)
        return httpx.Response(200, json={
            "id": "chat_len", "choices": [{"message": {"content": content}, "finish_reason": "length"}],
            "usage": {"prompt_tokens": 500, "completion_tokens": 16000},
        })

    return MetaClient(api_key="LLM_t_s", transport=httpx.MockTransport(handler))


@pytest.mark.parametrize("call", ["claims", "label"])
def test_a_length_stop_never_leaks_the_model_text(tmp_path, call):
    seen, guard = [], SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal(5))
    secret = "SECRET-MODEL-TEXT"
    with pytest.raises(ProviderError) as error:
        if call == "claims":
            MetaClaimExtractor(_length_client(seen, secret), guard).extract(TURNS)
        else:
            MetaLabelReader(_length_client(seen, secret), guard).read(IMAGE, REGION, mime="image/png")
    assert secret not in str(error.value) and len(seen) == 1


def test_claim_extraction_body_uses_16000_max_tokens(tmp_path):
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={
            "id": "c", "choices": [{"message": {"content": json.dumps({"claims": []})},
                                    "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        })

    guard = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal(5))
    MetaClaimExtractor(MetaClient(api_key="k", transport=httpx.MockTransport(handler)), guard).extract(TURNS)
    assert seen[0]["max_tokens"] == 16000
