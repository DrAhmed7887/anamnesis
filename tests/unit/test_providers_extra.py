"""Additional provider boundary and replay cases."""

import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from anamnesis.providers import (
    FixtureSegmenter,
    ProviderError,
    ProviderTrace,
    SpendGuard,
    cost_usd,
    parse_sam_output,
    top_regions,
)

SHA = "a" * 64


def test_voice_cost_rounds_each_clip_to_whole_seconds():
    assert cost_usd("muse-voice-transcribe-1.0", audio_ms=1001) == Decimal("0.18") * 2 / 3600


def test_sam_rejects_duplicate_ids_and_out_of_bounds_boxes():
    record = "0<|box;x1=0;y1=0;x2=1;y2=1;w=2;h=2|><|mask;x=0;y=0;data=1,1,~a|>"
    with pytest.raises(ProviderError):
        parse_sam_output(f"<0f>{record},{record}", SHA)
    with pytest.raises(ProviderError):
        parse_sam_output(f"<0f>{record.replace('x2=1', 'x2=2')}", SHA)
    with pytest.raises(ProviderError):
        parse_sam_output(f"<0f>{record.replace('data=1,1,~a', 'payload=a')}", SHA)


def test_top_regions_uses_object_id_to_break_confidence_ties():
    text = (
        "<0f>9<|box;x1=0;y1=0;x2=0;y2=0;w=1;h=1;c=0.5|><|mask;x=0;y=0;data=1,1,~a|>,"
        "2<|box;x1=0;y1=0;x2=0;y2=0;w=1;h=1;c=0.5|><|mask;x=0;y=0;data=1,1,~b|>"
    )
    assert [region.object_id for region in top_regions(parse_sam_output(text, SHA))] == [2, 9]


def test_spend_guard_reads_external_charges_before_checking(tmp_path):
    ledger = tmp_path / "spend.jsonl"
    first = SpendGuard(ledger, Decimal("1"))
    second = SpendGuard(ledger, Decimal("1"))
    trace = ProviderTrace(
        call_id="one", model_id="sam-3.1", latency_ms=0,
        input_tokens=0, output_tokens=0, cost_usd=Decimal("0.6"),
    )
    first.charge(trace)
    assert second.total_usd == Decimal("0.6")
    assert json.loads(ledger.read_text(encoding="utf-8"))["cost_usd"] == "0.6"


def test_fixture_segmenter_trace_is_deterministic(tmp_path):
    (tmp_path / "sam").mkdir()
    (tmp_path / "sam" / f"{SHA}.txt").write_text("", encoding="utf-8")
    adapter = FixtureSegmenter(tmp_path)
    assert adapter.segment(SHA, "pack")[1] == adapter.segment(SHA, "pack")[1]
    assert adapter.segment(SHA, "pack")[1].call_id != adapter.segment(SHA, "bottle")[1].call_id


def test_trace_rejects_negative_and_contributor_values():
    fields = dict(
        call_id="c", model_id="sam-3.1", latency_ms=0,
        input_tokens=0, output_tokens=0, cost_usd=Decimal(0),
    )
    with pytest.raises(ValidationError):
        ProviderTrace(**{**fields, "cost_usd": Decimal("-0.01")})
    with pytest.raises(ValidationError):
        ProviderTrace(**{**fields, "model_id": "sam-3.1-contributor"})


def test_sam_mask_payload_may_contain_pipes_and_angle_brackets() -> None:
    # Reviewer fix: SAM masks are base85, whose alphabet includes "|" and ">".
    from anamnesis.providers import parse_sam_output

    sha = "c" * 64
    text = (
        "<0f>3<|box;x1=1;y1=1;x2=5;y2=5;w=10;h=10|><|mask;x=0;y=0;data=4,4,~a|b>c|>,"
        "4<|box;x1=2;y1=2;x2=6;y2=6;w=10;h=10;c=0.5|><|mask;x=0;y=0;data=4,4,!|>|>"
    )
    assert [r.object_id for r in parse_sam_output(text, image_sha256=sha)] == [3, 4]
