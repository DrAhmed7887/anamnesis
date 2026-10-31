"""Extra offline checks for batch 20 stated amounts (SPEC §2)."""

import hashlib
import io
import json
from decimal import Decimal

import pytest
from PIL import Image as PILImage

from anamnesis.agent.loop import run_intake
from anamnesis.core.catalogue import load_catalogue
from anamnesis.providers import ProviderTrace
from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.spark import parse_label_json
from anamnesis.providers.stated import stated_amounts
from anamnesis.schema import AudioTurn, ImageRegion
from anamnesis.schema.report import AgentAction


def _turn(text, turn_id="t"):
    return [AudioTurn(turn_id=turn_id, start_ms=0, end_ms=1000, transcript=text)]


def _claim(name, turn_ids, **fields):
    return {"name_text": name, "inn": None, "strength": None, "intake_amount": None,
            "regimen": None, "status": "active", "turn_ids": list(turn_ids)} | fields


def _amount(value, inn="bisoprolol", unit="mg"):
    return {"inn": inn, "amount": value, "unit": unit}


def _strength(*parts):
    return {"ingredients": list(parts), "per": "tablet", "release": "unknown"}


@pytest.mark.parametrize("text,expected", [
    ("one hundred", {"1", "100"}),
    ("three thousand", {"3", "1000", "3000"}),
    ("one thousand two hundred", {"1", "1000", "2", "100", "1200"}),
    ("a hundred", {"100"}),
    ("hundred", {"100"}),
    ("thousand", {"1000"}),
    ("half", {"0.5"}),
    ("zero", set()),
    ("one point zero five", {"1", "5", "1.05"}),
    ("two point", {"2"}),
    ("point five", {"5", "0.5"}),
    ("five and twenty", {"5", "20", "25"}),
    ("ten thousand", {"10", "1000", "10000"}),
])
def test_english_runs(text, expected):
    assert stated_amounts(text) == frozenset(Decimal(v) for v in expected)


@pytest.mark.parametrize("text,expected", [
    ("واحد", {"1"}),
    ("تلاتين", {"30"}),
    ("تسعين", {"90"}),
    ("مايتين وخمسه", {"200", "5", "205"}),
    ("ستمائه", {"600"}),
    ("تسعمايه", {"900"}),
    ("ربعميه", {"400"}),
    ("تمنميه", {"800"}),
    ("سبعمائه", {"700"}),
    ("ستميه", {"600"}),
    ("ميه", {"100"}),
    ("الاف", {"1000"}),
    ("نصف", {"0.5"}),
    ("عشره الاف", {"10", "1000", "10000"}),
    ("واحد وعشرين", {"1", "20", "21"}),
    ("خمسين الف", {"50", "1000", "50000"}),
])
def test_arabic_runs(text, expected):
    assert stated_amounts(text) == frozenset(Decimal(v) for v in expected)


@pytest.mark.parametrize("text,expected", [
    ("7", {"7"}),
    ("007 mg", {"7"}),
    ("5.", {"5"}),
    (".5", set()),
    ("1,00", {"1"}),
    ("12,345", set()),
    ("1-2 tablets", {"1", "2"}),
    ("-5 mg", {"5"}),
    ("version 2 of 10", {"2", "10"}),
    ("١٬٠٠٠", set()),
    ("٣٫٧٥", {"3.75"}),
    ("", set()),
    ("no numbers here", set()),
])
def test_digit_runs(text, expected):
    assert stated_amounts(text) == frozenset(Decimal(str(v)) for v in expected)


def test_mixed_digit_and_word_forms_state_only_their_parts():
    assert stated_amounts("2 and a half") == frozenset({Decimal(2), Decimal("0.5")})
    grouped = stated_amounts("eight seventy-five")
    assert grouped >= {Decimal(8), Decimal(70), Decimal(5)}
    assert Decimal(875) not in grouped


def test_claim_strength_kept_only_when_every_ingredient_is_stated():
    turns = _turn("Augmentin 875 mg and 125 mg twice a day")
    both = _claim("Augmentin", ("t",), strength=_strength(
        _amount("875", "amoxicillin"), _amount("125", "clavulanic acid")))
    [found] = parse_claims_json(json.dumps({"claims": [both]}), turns)
    assert found.strength is not None
    turns = _turn("Augmentin 875 mg twice a day")
    [found] = parse_claims_json(json.dumps({"claims": [both]}), turns)
    assert found.strength is None


def test_claim_word_amount_with_decimal_digits_compares_by_value():
    turns = _turn("Concor two point five milligrams")
    reply = _claim("Concor", ("t",), intake_amount=_amount("2.50"))
    [found] = parse_claims_json(json.dumps({"claims": [reply]}), turns)
    assert found.intake_amount.amount == Decimal("2.5")


def test_claim_amount_stated_nowhere_is_dropped_with_its_pair():
    turns = _turn("Concor for my heart")
    reply = _claim("Concor", ("t",), intake_amount=_amount("5"),
                   strength=_strength(_amount("5")))
    [found] = parse_claims_json(json.dumps({"claims": [reply]}), turns)
    assert found.intake_amount is None and found.strength is None


def test_label_amount_in_arabic_digits_is_printed():
    reply = json.dumps({"label_text": "كونكور ٥ مجم", "inn": None, "country": None,
                        "readability": "readable",
                        "strength": {"ingredients": [_amount("5")], "per": "tablet",
                                     "release": "unknown"}})
    assert parse_label_json(reply, "r1").strength is not None


def test_label_strength_without_label_text_is_always_dropped():
    reply = json.dumps({"label_text": None, "inn": None, "country": None,
                        "readability": "partial",
                        "strength": {"ingredients": [_amount("5")], "per": "tablet",
                                     "release": "unknown"}})
    found = parse_label_json(reply, "r1")
    assert found.strength is None and found.readability.value == "partial"


@pytest.mark.parametrize("label_text", [5, ["Concor 5 mg"], {"text": "Concor 5 mg"}, True])
def test_a_non_string_label_text_is_a_read_error_not_a_crash(label_text):
    """Supervisor 20 #1: the malformed reply must not escape the parser mid-intake."""
    buf = io.BytesIO()
    PILImage.new("RGB", (64, 32)).save(buf, "PNG")
    photo = buf.getvalue()
    sha = hashlib.sha256(photo).hexdigest()
    region = ImageRegion(region_id=f"{sha[:12]}-0", image_sha256=sha, object_id=0,
                         x1=1, y1=1, x2=10, y2=10, frame_w=64, frame_h=32, confidence=0.9)

    class _Segmenter:
        def segment(self, image, concept, *, mime):
            return [region], ProviderTrace(call_id="s", model_id="fixture:test", latency_ms=1,
                                           input_tokens=0, output_tokens=0, cost_usd=Decimal("0.001"))

    class _BadReader:
        def read(self, image, region, *, mime, cropped=False):
            reply = json.dumps({"label_text": label_text, "inn": "bisoprolol", "country": None,
                                "readability": "readable",
                                "strength": {"ingredients": [_amount("5")], "per": "tablet",
                                             "release": "immediate"}})
            trace = ProviderTrace(call_id="r", model_id="fixture:test", latency_ms=1,
                                  input_tokens=0, output_tokens=0, cost_usd=Decimal("0.001"))
            return parse_label_json(reply, region.region_id), trace

    report = run_intake(None, [(photo, "image/png")], transcriber=None, extractor=None,
                        segmenter=_Segmenter(), reader=_BadReader(), catalogue=load_catalogue())
    assert any(step.action is AgentAction.READ and step.outcome == "error: spark ProviderError"
               for step in report.steps)
