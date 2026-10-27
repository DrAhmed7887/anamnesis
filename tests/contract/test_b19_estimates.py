"""Batch 19 contract, part 1: the batch 18 estimate follow-ups. Written by the CEO; Muse must not edit it.

SPEC §5 (supervisor 18 #1, #2). A Spark estimate also counts the reply schema, which is billed as prompt tokens:
without it the live claim calls of 27 Oct were bounded at 391 and 383 input tokens against 550 and 559 billed, and a
length stop at that size ended $0.0002 over a cap set to the bound. Label reads keep max_tokens 4000, and the zoom
is a Lanczos upscale; neither was tested before this batch (setting either one wrong passed the whole suite).
"""

import hashlib
import io
import json
import random
from decimal import Decimal

import httpx
import pytest
from PIL import Image

from anamnesis.agent import run_intake
from anamnesis.core.catalogue import load_catalogue
from anamnesis.providers import ProviderError, ProviderTrace, SpendGuard
from anamnesis.providers.base import cost_usd
from anamnesis.providers.claims import MetaClaimExtractor
from anamnesis.providers.meta import MetaClient, MetaLabelReader, spark_call_estimate
from anamnesis.providers.spark import LabelReading
from anamnesis.schema import AudioTurn, ImageRegion

MODEL = "muse-spark-1.3"


def chat(content, cid="chat_1", finish="stop", prompt=100, completion=50):
    return {"id": cid, "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": finish}],
            "usage": {"prompt_tokens": prompt, "completion_tokens": completion}}


def client(replies, seen):
    replies = list(replies)

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=replies.pop(0))

    return MetaClient(api_key="LLM_t_s", transport=httpx.MockTransport(handler))


def claims_body(turn, tmp_path):
    """The request body the claim extractor sends for one turn, captured from a normal reply."""
    seen = []
    guard = SpendGuard(tmp_path / "dry.jsonl", cap_usd=Decimal(5))
    MetaClaimExtractor(client([chat(json.dumps({"claims": []}))], seen), guard).extract([turn])
    return seen[0]


# --- the reply schema counts --------------------------------------------------------------------------------

def test_the_estimate_counts_the_reply_schema():
    schema = {"type": "json_schema", "json_schema": {"name": "x", "strict": True, "schema": {"type": "object"}}}
    body = {"model": MODEL, "max_tokens": 4000, "response_format": schema, "messages": [
        {"role": "system", "content": "abcd"},
        {"role": "user", "content": [{"type": "text", "text": "ef"},
                                     {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}}]},
    ]}
    # input: (6 characters of text + the characters of json.dumps(response_format)) // 2 + 5,000 per image
    chars = 6 + len(json.dumps(schema))
    assert spark_call_estimate(body) == cost_usd(MODEL, input_tokens=chars // 2 + 5000, output_tokens=4000)
    assert spark_call_estimate(body) == Decimal("0.023315")


# The two live claim calls of 27 Oct (evidence/live/2026-10-27/voice_*.json, claims_*.json): the turn, and the
# prompt tokens Meta billed for it.
LIVE = [
    (AudioTurn(turn_id="turn-0", start_ms=60, end_ms=8700, lang_hint="en", transcript=(
        "I take Concor five milligrams once a day. I also take Metoprolol 50 milligrams twice a day. "
        "I stopped taking Panadol last month")), 550),
    (AudioTurn(turn_id="turn-0", start_ms=0, end_ms=12620, lang_hint="ar", transcript=(
        "انا باخد كونكور خمسة ملي جرام مرة في اليوم وباخدد BelocZok خمسين ملي جرام مرتين في اليوم "
        "وقفت الPanadol من شهر")), 559),
]


@pytest.mark.parametrize(("turn", "billed"), LIVE, ids=["en", "ar"])
def test_the_estimate_bounds_the_live_claim_calls(tmp_path, turn, billed):
    body = claims_body(turn, tmp_path)
    assert spark_call_estimate(body) >= cost_usd(MODEL, input_tokens=billed, output_tokens=16000)


def test_a_live_sized_length_stop_stays_inside_a_cap_set_to_the_estimate(tmp_path):
    turn, billed = LIVE[1]
    cap = spark_call_estimate(claims_body(turn, tmp_path))
    guard = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=cap)
    stop = chat('{"claims": [', cid="chat_len", finish="length", prompt=billed, completion=16000)
    with pytest.raises(ProviderError) as error:
        MetaClaimExtractor(client([stop], []), guard).extract([turn])
    assert not error.value.retryable
    real = cost_usd(MODEL, input_tokens=billed, output_tokens=16000)
    assert guard.total_usd == real and guard.total_usd <= cap


# --- label reads keep 4000 tokens; the zoom is Lanczos ----------------------------------------------------------

def png_of(image):
    buf = io.BytesIO()
    image.save(buf, "PNG")
    return buf.getvalue()


def noise(w, h, seed=19):
    """A photo with detail in every pixel, so the resampling filter shows in the zoom."""
    rng = random.Random(seed)
    return png_of(Image.frombytes("RGB", (w, h), bytes(rng.randrange(256) for _ in range(w * h * 3))))


def region_on(image, box, obj=0):
    sha = hashlib.sha256(image).hexdigest()
    w, h = Image.open(io.BytesIO(image)).size
    return ImageRegion(region_id=f"{sha[:12]}-{obj}", image_sha256=sha, object_id=obj, x1=box[0], y1=box[1],
                       x2=box[2], y2=box[3], frame_w=w, frame_h=h, confidence=0.9)


def trace(cid):
    return ProviderTrace(call_id=cid, model_id="fixture:test", latency_ms=1, input_tokens=0, output_tokens=0,
                         cost_usd=Decimal("0.001"))


class Segmenter:
    def __init__(self, regions):
        self.regions = regions

    def segment(self, image, concept, *, mime):
        return list(self.regions), trace("sam")


class Reader:
    """Records the bytes of every read; every label stays unreadable, so each region gets its one zoom."""

    def __init__(self):
        self.calls = []

    def read(self, image, region, *, mime, cropped=False):
        self.calls.append(image)
        return LabelReading(region_id=region.region_id, readability="unreadable"), trace("read")


LABEL = json.dumps({"label_text": "Concor 5 mg", "inn": None, "country": None, "readability": "readable",
                    "strength": None})
PHOTO = noise(120, 80)
REGION = region_on(PHOTO, (20, 10, 99, 69))  # 80x60: its crop is 88x66 with the 5% margin on each side


@pytest.mark.parametrize("cropped", [True, False])
def test_label_reads_ask_for_4000_tokens(tmp_path, cropped):
    seen = []
    guard = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal(5))
    MetaLabelReader(client([chat(LABEL)], seen), guard).read(PHOTO, REGION, mime="image/png", cropped=cropped)
    assert seen[0]["max_tokens"] == 4000


def test_the_zoom_is_a_lanczos_2x_upscale_of_the_crop_the_reader_saw():
    reader = Reader()
    run_intake(None, [(PHOTO, "image/png")], transcriber=None, extractor=None, segmenter=Segmenter([REGION]),
               reader=reader, catalogue=load_catalogue())
    first, zoom = (Image.open(io.BytesIO(data)).convert("RGB") for data in reader.calls)
    assert first.size == (88, 66)
    lanczos = first.resize((176, 132), Image.Resampling.LANCZOS)
    assert zoom.size == (176, 132) and zoom.tobytes() == lanczos.tobytes()
    assert first.resize((176, 132), Image.Resampling.NEAREST).tobytes() != lanczos.tobytes()
