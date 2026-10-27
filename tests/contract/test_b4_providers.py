"""Batch 4 contract: typed provider adapters, offline (SPEC.md §1, §4, §5). Written by the reviewer; do not edit."""

import json
from decimal import Decimal

import pytest

from anamnesis.providers import (
    FixtureLabelReader,
    FixtureSegmenter,
    FixtureTranscriber,
    LabelReading,
    ProviderError,
    ProviderTrace,
    SpendCapExceeded,
    SpendGuard,
    cost_usd,
    parse_label_json,
    parse_sam_output,
    parse_transcribe_response,
    top_regions,
    with_one_retry,
)
from anamnesis.schema import AudioTurn, ImageRegion, Readability

SHA = "b" * 64

# --- Voice Transcribe (docs/muse/muse-voice-transcribe.md) -------------------

VOICE = {
    "audioDurationMs": 15000,
    "turns": [
        {"turnId": 0, "startMs": 400, "endMs": 6100, "transcript": "باخد كونكور خمسة", "speaker": "A"},
        {"turnId": 1, "startMs": 6500, "endMs": 14800, "transcript": "and metoprolol 50 twice a day", "speaker": "A"},
    ],
}


def test_transcribe_response_maps_to_audio_turns():
    turns = parse_transcribe_response(VOICE, lang_hint="ar")
    assert [t.turn_id for t in turns] == ["turn-0", "turn-1"]
    assert all(isinstance(t, AudioTurn) for t in turns)
    assert turns[0].transcript == "باخد كونكور خمسة"  # raw text kept, never normalized or translated
    assert turns[1].start_ms == 6500 and turns[1].speaker == "A" and turns[1].lang_hint == "ar"


def test_transcribe_empty_turns_is_valid_and_empty():
    assert parse_transcribe_response({"audioDurationMs": 900, "turns": []}) == []


@pytest.mark.parametrize("payload", [
    {"audioDurationMs": 10},                                               # no turns key
    {"turns": [{"turnId": 0, "startMs": 5, "endMs": 5, "transcript": "x"}]},  # zero-length turn
    {"turns": "nope"},
])
def test_transcribe_rejects_malformed_payload(payload):
    with pytest.raises(ProviderError):
        parse_transcribe_response(payload)


# --- SAM 3.1 (docs/muse/sam-3-1.md) ------------------------------------------

SAM = (
    "<0f>0<|box;x1=353;y1=382;x2=453;y2=427;w=537;h=561;c=0.91|><|mask;x=0;y=0;data=46,101,~abc|>,"
    "7<|box;x1=10;y1=20;x2=200;y2=300;w=537;h=561;c=0.55|><|mask;x=0;y=0;data=2,2,!zz|>,"
    "9<|box;x1=0;y1=0;x2=5;y2=5;w=537;h=561|><|mask;x=0;y=0;data=1,1,~q|>"
)


def test_sam_output_maps_to_regions_in_source_pixels():
    regions = parse_sam_output(SAM, image_sha256=SHA)
    assert all(isinstance(r, ImageRegion) for r in regions)
    assert [r.object_id for r in regions] == [0, 7, 9]
    first = regions[0]
    assert (first.x1, first.y1, first.x2, first.y2, first.frame_w, first.frame_h) == (353, 382, 453, 427, 537, 561)
    assert first.confidence == pytest.approx(0.91)
    assert regions[2].confidence is None
    assert first.region_id == f"{SHA[:12]}-0"


def test_sam_empty_output_is_zero_regions_not_an_error():
    assert parse_sam_output("", image_sha256=SHA) == []


@pytest.mark.parametrize("bad", ["<0f>0<|box;x1=1;y1=1|>", "garbage", "<0f>0<|box;x1=1;y1=1;x2=999;y2=2;w=10;h=10|>"])
def test_sam_rejects_malformed_output(bad):
    with pytest.raises(ProviderError):
        parse_sam_output(bad, image_sha256=SHA)


def test_top_regions_caps_oversegmentation():
    regions = parse_sam_output(SAM, image_sha256=SHA)
    top = top_regions(regions, k=2)
    assert [r.object_id for r in top] == [0, 7]  # by confidence, unscored last
    assert len(top_regions(regions)) == 3        # default k=3 (SPEC §4)


# --- Muse Spark label reading ------------------------------------------------

def test_label_json_parses_into_reading():
    text = json.dumps({
        "label_text": "Concor 5 mg", "inn": "bisoprolol", "readability": "readable", "country": "DE",
        "strength": {"ingredients": [{"inn": "bisoprolol", "amount": "5", "unit": "mg"}], "per": "tablet"},
    })
    r = parse_label_json(text, region_id="r-0")
    assert isinstance(r, LabelReading) and r.region_id == "r-0"
    assert r.readability is Readability.READABLE and r.strength.ingredients[0].amount == Decimal(5)


@pytest.mark.parametrize("text", [
    "not json",
    '{"label_text": "Concor", "readability": "very readable"}',        # enum outside the closed set
    '{"label_text": "Concor", "readability": "readable", "dose_advice": "x"}',  # extra field
    '{"readability": "readable"}',                                     # readable needs label text
])
def test_label_json_rejects_invalid_output_as_retryable(text):
    with pytest.raises(ProviderError) as e:
        parse_label_json(text, region_id="r-0")
    assert e.value.retryable is True


def test_with_one_retry_retries_once_then_raises():
    calls = []

    def flaky():
        calls.append(1)
        raise ProviderError("spark", "bad json", retryable=True)

    with pytest.raises(ProviderError):
        with_one_retry(flaky)
    assert len(calls) == 2


def test_with_one_retry_does_not_retry_non_retryable():
    calls = []

    def fatal():
        calls.append(1)
        raise ProviderError("meta", "402 billing", retryable=False)

    with pytest.raises(ProviderError):
        with_one_retry(fatal)
    assert len(calls) == 1


def test_with_one_retry_returns_second_success():
    state = {"n": 0}

    def once_bad():
        state["n"] += 1
        if state["n"] == 1:
            raise ProviderError("spark", "timeout", retryable=True)
        return "ok"

    assert with_one_retry(once_bad) == "ok"


# --- costs and traces (SPEC §5) ------------------------------------------------

def test_cost_table_matches_documented_prices():
    assert cost_usd("muse-spark-1.3", input_tokens=1_000_000, output_tokens=0) == Decimal("1.25")
    assert cost_usd("muse-spark-1.3", input_tokens=0, output_tokens=1_000_000) == Decimal("4.25")
    assert cost_usd("sam-3.1", images=1000) == Decimal("2.50")
    assert cost_usd("muse-voice-transcribe-1.0", audio_ms=3_600_000) == Decimal("0.18")
    assert cost_usd("muse-voice-transcribe-1.0", audio_ms=1) == cost_usd("muse-voice-transcribe-1.0", audio_ms=1000)
    with pytest.raises(KeyError):
        cost_usd("unknown-model", input_tokens=1)


def test_provider_trace_is_strict():
    t = ProviderTrace(call_id="call-1", model_id="sam-3.1", latency_ms=120, input_tokens=0, output_tokens=0,
                      cost_usd=Decimal("0.0025"))
    assert t.model_id == "sam-3.1"
    for bad in [dict(latency_ms=-1), dict(call_id=""), dict(model_id="muse-spark-1.3-contributor")]:
        kw = dict(call_id="c", model_id="sam-3.1", latency_ms=1, input_tokens=0, output_tokens=0, cost_usd=Decimal(0))
        kw.update(bad)
        with pytest.raises(ValueError):  # contributor ids let Meta train on the data: never allowed
            ProviderTrace(**kw)


def trace(cost, call_id="c1"):
    return ProviderTrace(call_id=call_id, model_id="muse-spark-1.3", latency_ms=5, input_tokens=10,
                         output_tokens=10, cost_usd=Decimal(cost))


def test_spend_guard_records_and_persists(tmp_path):
    ledger = tmp_path / "spend.jsonl"
    g = SpendGuard(ledger, cap_usd=Decimal("1.00"))
    g.charge(trace("0.40", "a"))
    g.charge(trace("0.40", "b"))
    assert g.total_usd == Decimal("0.80")
    assert SpendGuard(ledger, cap_usd=Decimal("1.00")).total_usd == Decimal("0.80")  # reloaded from disk
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 2


def test_spend_guard_refuses_before_crossing_the_cap(tmp_path):
    g = SpendGuard(tmp_path / "spend.jsonl", cap_usd=Decimal("1.00"))
    g.charge(trace("0.90"))
    with pytest.raises(SpendCapExceeded):
        g.check(Decimal("0.20"))       # pre-flight estimate
    with pytest.raises(SpendCapExceeded):
        g.charge(trace("0.20", "c2"))
    assert g.total_usd == Decimal("0.90")  # a refused charge is not recorded


# --- fixture adapters: offline, deterministic, same interface ----------------

def test_fixture_adapters_replay_offline(tmp_path):
    (tmp_path / "voice").mkdir()
    (tmp_path / "sam").mkdir()
    (tmp_path / "label").mkdir()
    (tmp_path / "voice" / f"{SHA}.json").write_text(json.dumps(VOICE), encoding="utf-8")
    (tmp_path / "sam" / f"{SHA}.txt").write_text(SAM, encoding="utf-8")
    (tmp_path / "label" / f"{SHA[:12]}-0.json").write_text(
        json.dumps({"label_text": None, "readability": "unreadable"}), encoding="utf-8")

    turns, trace = FixtureTranscriber(tmp_path).transcribe(SHA, lang_hint="ar")
    assert len(turns) == 2 and trace.model_id == "fixture:muse-voice-transcribe-1.0" and trace.cost_usd == 0

    regions, trace = FixtureSegmenter(tmp_path).segment(SHA, concept="medicine pack")
    assert len(regions) == 3 and trace.model_id == "fixture:sam-3.1"

    reading, trace = FixtureLabelReader(tmp_path).read(regions[0])
    assert reading.readability is Readability.UNREADABLE and trace.model_id == "fixture:muse-spark-1.3"
    assert reading.region_id == regions[0].region_id  # every reading is grounded in one region


def test_missing_fixture_is_a_non_retryable_provider_error(tmp_path):
    with pytest.raises(ProviderError) as e:
        FixtureTranscriber(tmp_path).transcribe(SHA)
    assert e.value.retryable is False
