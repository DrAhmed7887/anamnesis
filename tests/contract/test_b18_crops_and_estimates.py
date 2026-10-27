"""Batch 18 contract: every label is read from its own crop, the zoom enlarges that crop, and a Spark call's
estimate is an upper bound with no retry after a length stop. Written by the CEO; Muse must not edit it.

SPEC §4 steps 4-5 (Z8) and §5 (C6, C7). Live, 27 Oct: crop reads were 8/8 correct at about a quarter of the input
tokens (evidence/live/2026-10-27/zoom_after/); a full-photo read with the box given as text can describe a
neighbouring pack. Older contracts that assumed a full-photo first read (b14, b15.5) and a fixed $0.03 estimate
(b12) were updated in the same contract commit; their provenance and spend guarantees are unchanged.
"""

import hashlib
import io
import json
from decimal import Decimal

import httpx
import pytest
from PIL import Image

from anamnesis.agent import AgentAction, crop_region, run_intake
from anamnesis.core.catalogue import load_catalogue
from anamnesis.providers import ProviderError, ProviderTrace, SpendGuard
from anamnesis.providers.base import cost_usd
from anamnesis.providers.claims import MetaClaimExtractor
from anamnesis.providers.meta import MetaClient, MetaLabelReader, spark_call_estimate
from anamnesis.providers.spark import LabelReading
from anamnesis.schema import AudioTurn, ImageRegion
from anamnesis.schema import DiscrepancyType as D

CAT = load_catalogue()


def png(w, h, colour=(200, 200, 200)):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), colour).save(buf, "PNG")
    return buf.getvalue()


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
    """Records what each read was shown and answers from a script of readabilities per region, in call order."""

    def __init__(self, script):
        self.script, self.calls = {key: list(value) for key, value in script.items()}, []

    def read(self, image, region, *, mime, cropped=False):
        self.calls.append({"region": region.region_id, "cropped": cropped, "mime": mime, "bytes": image,
                           "size": Image.open(io.BytesIO(image)).size})
        state = self.script[region.region_id].pop(0)
        label = "Concor 5 mg" if state == "readable" else None
        return LabelReading(region_id=region.region_id, label_text=label, readability=state), trace("read")


def intake(image, regions, reader, **kw):
    return run_intake(None, [(image, "image/png")], transcriber=None, extractor=None, segmenter=Segmenter(regions),
                      reader=reader, catalogue=CAT, **kw)


IMAGE = png(200, 100)
R0 = region_on(IMAGE, (110, 10, 189, 89), 0)  # 80x80: its crop is 88x88 with the 5% margin on each side
R1 = region_on(IMAGE, (10, 10, 89, 89), 1)


# --- Z8: the reader only ever sees its own region's crop --------------------------------------------------------

def test_every_read_is_a_png_crop_of_its_region_never_the_full_photo():
    reader = Reader({R0.region_id: ["readable"], R1.region_id: ["readable"]})
    intake(IMAGE, [R0, R1], reader)
    assert len(reader.calls) == 2
    assert all(c["cropped"] and c["mime"] == "image/png" and c["size"] == (88, 88) for c in reader.calls)
    assert all(c["bytes"] != IMAGE for c in reader.calls)


def test_the_zoom_reads_the_same_crop_enlarged_2x_and_keeps_the_region():
    reader = Reader({R1.region_id: ["unreadable", "readable"]})
    report = intake(IMAGE, [R1], reader)
    assert [c["size"] for c in reader.calls] == [(88, 88), (176, 176)]
    assert all(c["cropped"] and c["region"] == R1.region_id for c in reader.calls)
    assert [s.action for s in report.steps].count(AgentAction.ZOOM_READ) == 1
    [obs] = report.observations
    assert obs.readability.value == "readable" and obs.visual_evidence == [R1.region_id]


def test_a_large_crop_is_enlarged_only_until_its_longest_side_is_2048_px():
    big = png(1800, 1000)
    region = region_on(big, (100, 100, 1599, 899))  # 1500x800: its crop is 1650x880
    reader = Reader({region.region_id: ["unreadable", "unreadable"]})
    intake(big, [region], reader)
    (w1, h1), (w2, h2) = [c["size"] for c in reader.calls]
    assert (w1, h1) == (1650, 880)
    assert 2047 <= max(w2, h2) <= 2048 and abs(w2 / h2 - w1 / h1) < 0.01


def test_no_zoom_when_the_crop_is_already_2048_px_or_wider():
    huge = png(2400, 1200)
    region = region_on(huge, (50, 50, 2299, 1149))  # its crop clamps to the whole 2400x1200 frame
    reader = Reader({region.region_id: ["unreadable"]})
    report = intake(huge, [region], reader)
    assert len(reader.calls) == 1 and AgentAction.ZOOM_READ not in [s.action for s in report.steps]
    assert {f.type for f in report.findings} == {D.UNREADABLE_SOURCE}


def test_a_crop_that_fails_logs_one_read_step_and_makes_no_call(monkeypatch):
    def broken(image, region, margin=0.10):
        raise ValueError("crop failed")

    monkeypatch.setattr("anamnesis.agent.loop.crop_region", broken)
    reader = Reader({R0.region_id: []})
    report = intake(IMAGE, [R0], reader)
    assert reader.calls == [] and report.observations == [] and report.calls == 1  # the segment call only
    reads = [(s.target, s.outcome, s.call_ids) for s in report.steps if s.action is AgentAction.READ]
    assert reads == [(R0.region_id, "error: crop failed", [])]


def test_no_crop_is_cut_or_logged_once_the_budget_has_run_out(monkeypatch):
    real = crop_region
    three = [region_on(IMAGE, (10 + 50 * i, 10, 49 + 50 * i, 49), i) for i in range(3)]

    def last_one_fails(image, region, margin=0.10):
        if region.object_id == 2:
            raise ValueError("crop failed")
        return real(image, region, margin)

    monkeypatch.setattr("anamnesis.agent.loop.crop_region", last_one_fails)
    reader = Reader({region.region_id: ["readable"] for region in three})
    report = intake(IMAGE, three, reader, max_provider_calls=2)  # the segment call and one read
    actions = [s.action for s in report.steps]
    assert actions.count(AgentAction.BUDGET_EXHAUSTED) == 1 and actions[-1] is AgentAction.BUDGET_EXHAUSTED
    assert "error: crop failed" not in [s.outcome for s in report.steps]


# --- C6, C7: estimates are upper bounds; a length stop is charged once and not retried ------------------------

def test_a_spark_estimate_is_an_upper_bound_from_the_request_body():
    body = {"model": "muse-spark-1.3", "max_tokens": 4000, "messages": [
        {"role": "system", "content": "abcd"},
        {"role": "user", "content": [{"type": "text", "text": "ef"},
                                     {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}}]},
    ]}
    # input: 6 characters of text // 2 + 5,000 per attached image; output: max_tokens
    assert spark_call_estimate(body) == cost_usd("muse-spark-1.3", input_tokens=5003, output_tokens=4000)
    assert spark_call_estimate(body) == Decimal("0.02325375")


class RecordingGuard(SpendGuard):
    def __init__(self, path, cap):
        super().__init__(path, cap_usd=cap)
        self.checked = []

    def check(self, estimate):
        self.checked.append(Decimal(estimate))
        return super().check(estimate)


def chat(content, cid="chat_1", finish="stop", prompt=100, completion=50):
    return {"id": cid, "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": finish}],
            "usage": {"prompt_tokens": prompt, "completion_tokens": completion}}


def client(replies, seen):
    replies = list(replies)

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=replies.pop(0))

    return MetaClient(api_key="LLM_t_s", transport=httpx.MockTransport(handler))


TURNS = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=10, transcript="Concor five")]
LABEL = json.dumps({"label_text": "Concor 5 mg", "inn": None, "country": None, "readability": "readable",
                    "strength": None})


def test_claim_extraction_asks_for_16000_tokens_and_checks_caps_with_the_bound(tmp_path):
    seen, guard = [], RecordingGuard(tmp_path / "ledger.jsonl", Decimal(5))
    MetaClaimExtractor(client([chat(json.dumps({"claims": []}))], seen), guard).extract(TURNS)
    [body] = seen
    assert body["max_tokens"] == 16000
    assert guard.checked == [spark_call_estimate(body)]


def test_a_label_read_checks_caps_with_its_bound(tmp_path):
    seen, guard = [], RecordingGuard(tmp_path / "ledger.jsonl", Decimal(5))
    MetaLabelReader(client([chat(LABEL)], seen), guard).read(IMAGE, R0, mime="image/png")
    [body] = seen
    assert guard.checked == [spark_call_estimate(body)]


@pytest.mark.parametrize("call", ["claims", "label"])
def test_a_length_stop_is_charged_at_real_usage_and_never_retried(tmp_path, call):
    seen, guard = [], SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal(5))
    reply = chat('{"claims": [', cid="chat_len", finish="length", prompt=500, completion=16000)
    with pytest.raises(ProviderError) as error:
        if call == "claims":
            MetaClaimExtractor(client([reply], seen), guard).extract(TURNS)
        else:
            MetaLabelReader(client([reply], seen), guard).read(IMAGE, R0, mime="image/png")
    assert len(seen) == 1 and not error.value.retryable
    real = cost_usd("muse-spark-1.3", input_tokens=500, output_tokens=16000)
    [line] = [json.loads(text) for text in (tmp_path / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    assert Decimal(line["cost_usd"]) == real and not line.get("estimated", False)
    assert error.value.charged_call_ids == ["chat_len"] and error.value.charged_usd == real
