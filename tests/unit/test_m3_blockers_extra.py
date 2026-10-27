"""Batch 15 gaps: charges before a cap refusal, and exact strengths against a nominal amount."""

import hashlib
import io
import json
from decimal import Decimal

import httpx
import pytest
from PIL import Image

from anamnesis.agent import AgentAction, run_intake
from anamnesis.agent.session import IntakeSession
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import _strength_type
from anamnesis.providers import SpendGuard
from anamnesis.providers.claims import MetaClaimExtractor
from anamnesis.providers.meta import MetaClient, MetaLabelReader, MetaSegmenter, spark_call_estimate
from anamnesis.providers.spend import SessionCapExceeded, SessionGuard
from anamnesis.schema import AudioTurn, ImageRegion, IngredientAmount, Strength
from anamnesis.schema import DiscrepancyType as D

CAT = load_catalogue()


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (40, 40)).save(buf, format="PNG")
    return buf.getvalue()


IMAGE = _png()
SHA = hashlib.sha256(IMAGE).hexdigest()
REGION = ImageRegion(region_id=f"{SHA[:12]}-0", image_sha256=SHA, object_id=0, x1=0, y1=0, x2=9, y2=9,
                     frame_w=40, frame_h=40)


def _client(handler):
    return MetaClient(api_key="LLM_t_s", transport=httpx.MockTransport(handler))


def _timeout(request):
    raise httpx.ReadTimeout("slow")


def _not_json(request):
    return httpx.Response(200, json={"id": "a", "choices": [{"message": {"content": "not json"}}],
                                     "usage": {"prompt_tokens": 1000, "completion_tokens": 200}})


def test_cap_refusing_attempt_two_still_reports_the_charged_timeout(tmp_path):
    parent = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal("5"))
    guard = SessionGuard(parent, max_usd=Decimal("0.003"), max_calls=10)
    segmenter = MetaSegmenter(_client(_timeout), guard)
    report = run_intake(None, [(IMAGE, "image/png")], transcriber=None, extractor=None, segmenter=segmenter,
                        reader=None, catalogue=CAT)
    assert parent.total_usd == Decimal("0.0025")
    assert report.spend_usd == parent.total_usd
    exhausted = next(s for s in report.steps if s.action is AgentAction.BUDGET_EXHAUSTED)
    assert len(exhausted.call_ids) == 1


def test_cap_refusing_attempt_two_still_reports_the_paid_invalid_reply(tmp_path):
    parent = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal("5"))
    guard = SessionGuard(parent, max_usd=Decimal("5"), max_calls=1)
    reader = MetaLabelReader(_client(_not_json), guard)
    session = IntakeSession(max_provider_calls=5)
    read = lambda: reader.read(IMAGE, REGION, mime="image/png")  # noqa: E731
    assert session.call(AgentAction.READ, "r1", read, str) is None
    assert parent.total_usd == Decimal("0.0021")
    assert session.spend_usd == parent.total_usd
    assert session.steps[-1].action is AgentAction.BUDGET_EXHAUSTED and session.steps[-1].call_ids == ["a"]


def test_session_cap_error_carries_no_charge_by_default():
    exc = SessionCapExceeded("cap")
    assert exc.charged_call_ids == [] and exc.charged_usd == Decimal(0)


def test_stated_strength_equal_to_nominal_matches_but_a_multiple_of_the_literal_does_not():
    def st(amount):
        return Strength(ingredients=[IngredientAmount(inn="metoprolol", amount=Decimal(amount), unit="mg")],
                        per="tablet")

    nominal = {"metoprolol": Decimal(100)}
    assert _strength_type(st(100), st(50), CAT, nominal) is D.MATCH  # nominal, though 100 = 2 x literal 50
    assert _strength_type(st(100), st(50), CAT, None) is D.STRENGTH_MISMATCH
    assert _strength_type(st(25), st(50), CAT, nominal) is D.STRENGTH_MISMATCH


def _timeout_then_empty_id(seen):
    replies = iter([httpx.ReadTimeout("slow"), None])

    def handler(request):
        seen.append(json.loads(request.content))
        step = next(replies)
        if step is not None:
            raise step
        return httpx.Response(200, json={"id": "", "choices": [{"message": {"content": "{}"}}],
                                         "usage": {"prompt_tokens": 10, "completion_tokens": 2}})
    return handler


def _read_label(guard, seen):
    reader = MetaLabelReader(_client(_timeout_then_empty_id(seen)), guard)
    return lambda: reader.read(IMAGE, REGION, mime="image/png")


def _extract_claims(guard, seen):
    turn = AudioTurn(turn_id="turn-0", start_ms=0, end_ms=10, transcript="Concor five")
    extractor = MetaClaimExtractor(_client(_timeout_then_empty_id(seen)), guard)
    return lambda: extractor.extract([turn])


@pytest.mark.parametrize("make_call", [_read_label, _extract_claims])
def test_a_paid_spark_reply_with_an_empty_id_is_counted(tmp_path, make_call):
    parent = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal("5"))
    guard = SessionGuard(parent, max_usd=Decimal("5"), max_calls=10)
    session = IntakeSession(max_provider_calls=5)
    seen = []
    assert session.call(AgentAction.READ, "x", make_call(guard, seen), str) is None
    assert parent.total_usd == 2 * spark_call_estimate(seen[0])  # each attempt charged at its bound
    assert session.spend_usd == parent.total_usd
    assert len(session.steps[-1].call_ids) == 2


def test_a_value_error_after_charged_attempts_is_still_counted():
    session = IntakeSession(max_provider_calls=5)

    def fail():
        exc = ValueError("boom")
        exc.charged_call_ids, exc.charged_usd = ["e1"], Decimal("0.01")
        raise exc

    assert session.call(AgentAction.READ, "x", fail, str) is None
    assert session.spend_usd == Decimal("0.01") and session.steps[-1].call_ids == ["e1"]
