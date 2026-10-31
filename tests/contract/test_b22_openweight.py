"""Batch 22 contract: an open-weight label reader for a zero-shot comparison with Spark 1.3. Written by the CEO;
Muse must not edit it.

SPEC §4 "Open-weight label reader". Ahmed added it on 28 Oct, after the training research found no time for a
fine-tune before the freeze. Muse Spark Open, and Glimmer if an endpoint is up, read the same crops with the same
system prompt, schema and parser as Spark 1.3, through an OpenAI-compatible endpoint (Fireworks or Baseten). Only the
public test photos go to these providers (docs/DATA_HANDLING.md).
"""

import json
from decimal import Decimal

import httpx
import pytest

from anamnesis.agent import run_intake
from anamnesis.providers import ProviderError, SpendGuard
from anamnesis.providers.base import cost_usd
from anamnesis.providers.meta import _SYSTEM_PROMPT, LABEL_SCHEMA, MetaClient, MetaLabelReader
from anamnesis.providers.openweight import PRESETS, OpenWeightClient, OpenWeightLabelReader
from anamnesis.providers.spend import SpendCapExceeded
from tests.contract.test_b19_brief import CAT, PHOTO, RC, Extractor, Segmenter, Transcriber, claim

KEY = "fw_secret_for_test"
LABEL = {"label_text": "Concor 5 mg\nBisoprolol fumarate", "inn": "bisoprolol", "country": None,
         "readability": "readable",
         "strength": {"ingredients": [{"inn": "bisoprolol", "amount": "5", "unit": "mg"}], "per": "tablet",
                      "release": "immediate"}}


def reply(content, call_id="cmpl-1", prompt=1000, completion=500, finish="stop"):
    return httpx.Response(200, json={"id": call_id, "choices": [{"message": {"content": content},
                                                                  "finish_reason": finish}],
                                     "usage": {"prompt_tokens": prompt, "completion_tokens": completion}})


def guard(tmp_path, cap="5"):
    return SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal(cap))


def reader(tmp_path, handler, *, json_mode=True, provider="fireworks", cap="5"):
    client = OpenWeightClient(api_key=KEY, base_url=PRESETS[provider]["base_url"], provider=provider,
                              transport=httpx.MockTransport(handler))
    return OpenWeightLabelReader(client, guard(tmp_path, cap), model=PRESETS[provider]["model"],
                                 price_key=f"muse-spark-open@{provider}", json_mode=json_mode)


def ledger_lines(tmp_path):
    path = tmp_path / "ledger.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


# --- the same request as Spark 1.3 ---------------------------------------------------------------------------

def test_presets_name_the_two_providers():
    assert PRESETS["fireworks"]["base_url"] == "https://api.fireworks.ai/inference/v1"
    assert PRESETS["fireworks"]["model"] == "accounts/fireworks/models/muse-spark-open"
    assert PRESETS["fireworks"]["json_mode"] is True
    assert PRESETS["baseten"]["base_url"] == "https://inference.baseten.co/v1"
    assert PRESETS["baseten"]["json_mode"] is False


@pytest.mark.parametrize("cropped", [False, True])
def test_it_sends_spark_s_prompt_schema_and_image(tmp_path, cropped):
    seen = {}

    def capture(name):
        def handler(request):
            seen[name] = json.loads(request.content)
            return reply(json.dumps(LABEL))
        return handler

    spark = MetaLabelReader(MetaClient(api_key="LLM_t_s", transport=httpx.MockTransport(capture("spark"))),
                            guard(tmp_path))
    spark.read(PHOTO, RC, mime="image/png", cropped=cropped)
    reader(tmp_path, capture("open")).read(PHOTO, RC, mime="image/png", cropped=cropped)
    spark_body, open_body = seen["spark"], seen["open"]
    assert open_body["messages"] == spark_body["messages"]
    assert open_body["messages"][0] == {"role": "system", "content": _SYSTEM_PROMPT}
    assert open_body["response_format"] == spark_body["response_format"]
    assert open_body["model"] == "accounts/fireworks/models/muse-spark-open"


def test_without_json_mode_the_schema_is_in_the_text_and_fenced_json_parses(tmp_path):
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return reply("```json\n" + json.dumps(LABEL) + "\n```")

    reading, _ = reader(tmp_path, handler, json_mode=False, provider="baseten").read(PHOTO, RC, mime="image/png")
    body = seen[0]
    assert "response_format" not in body
    user_text = " ".join(part["text"] for part in body["messages"][1]["content"] if part["type"] == "text")
    assert json.dumps(LABEL_SCHEMA, sort_keys=True) in user_text
    assert body["messages"][0] == {"role": "system", "content": _SYSTEM_PROMPT}
    assert reading.label_text.startswith("Concor 5 mg")
    assert reading.strength.ingredients[0].amount == Decimal("5")


# --- the same checks as Spark 1.3 ----------------------------------------------------------------------------

def test_an_amount_not_printed_on_the_label_is_dropped(tmp_path):
    invented = dict(LABEL, label_text="Concor\nBisoprolol fumarate")

    reading, _ = reader(tmp_path, lambda request: reply(json.dumps(invented))).read(PHOTO, RC, mime="image/png")
    assert reading.strength is None


def test_a_malformed_reply_is_retried_once_and_both_attempts_are_charged(tmp_path):
    replies = iter([reply("not json", call_id="cmpl-a"), reply(json.dumps(LABEL), call_id="cmpl-b")])
    reading, trace = reader(tmp_path, lambda request: next(replies)).read(PHOTO, RC, mime="image/png")
    assert reading.readability.value == "readable"
    assert trace.call_id == "cmpl-b" and trace.prior_call_ids == ["cmpl-a"]
    assert [line["call_id"] for line in ledger_lines(tmp_path)] == ["cmpl-a", "cmpl-b"]


def test_two_malformed_replies_raise_and_stay_charged(tmp_path):
    replies = iter([reply("{", call_id="cmpl-a"), reply("still not json", call_id="cmpl-b")])
    with pytest.raises(ProviderError) as caught:
        reader(tmp_path, lambda request: next(replies)).read(PHOTO, RC, mime="image/png")
    assert caught.value.charged_call_ids == ["cmpl-a", "cmpl-b"]
    assert len(ledger_lines(tmp_path)) == 2


def test_advice_in_an_ingredient_makes_the_reply_malformed(tmp_path):
    advice = dict(LABEL, inn="double the dose")
    replies = iter([reply(json.dumps(advice), call_id="cmpl-a"), reply(json.dumps(LABEL), call_id="cmpl-b")])
    _, trace = reader(tmp_path, lambda request: next(replies)).read(PHOTO, RC, mime="image/png")
    assert trace.prior_call_ids == ["cmpl-a"]


# --- spend, keys and refusals ----------------------------------------------------------------------------------

@pytest.mark.parametrize("provider", ["fireworks", "baseten"])
def test_spend_uses_the_open_weight_price_and_names_the_provider(tmp_path, provider):
    assert cost_usd(f"muse-spark-open@{provider}", input_tokens=1_000_000) == Decimal("1.25")
    assert cost_usd(f"muse-spark-open@{provider}", output_tokens=1_000_000) == Decimal("4.25")
    content = json.dumps(LABEL) if provider == "fireworks" else "```json\n" + json.dumps(LABEL) + "\n```"
    _, trace = reader(tmp_path, lambda request: reply(content), provider=provider,
                      json_mode=PRESETS[provider]["json_mode"]).read(PHOTO, RC, mime="image/png")
    expected = Decimal(1000) * Decimal("1.25") / 1_000_000 + Decimal(500) * Decimal("4.25") / 1_000_000
    assert trace.cost_usd == expected
    assert trace.model_id == f"muse-spark-open@{provider}"
    assert [line["model_id"] for line in ledger_lines(tmp_path)] == [f"muse-spark-open@{provider}"]


def test_a_contributor_model_is_refused(tmp_path):
    client = OpenWeightClient(api_key=KEY, base_url=PRESETS["fireworks"]["base_url"], provider="fireworks",
                              transport=httpx.MockTransport(lambda request: reply("{}")))
    with pytest.raises(ValueError):
        OpenWeightLabelReader(client, guard(tmp_path), model="muse-spark-open-contributor",
                              price_key="muse-spark-open@fireworks", json_mode=True)


def test_the_key_never_appears_in_an_error(tmp_path):
    def handler(request):
        assert request.headers["Authorization"] == f"Bearer {KEY}"
        return httpx.Response(401, json={"error": {"message": f"bad key {KEY}"}})

    with pytest.raises(ProviderError) as caught:
        reader(tmp_path, handler).read(PHOTO, RC, mime="image/png")
    assert KEY not in str(caught.value) and "[redacted]" in str(caught.value)
    assert caught.value.provider == "fireworks"


def test_the_cap_refuses_before_any_request_is_sent(tmp_path):
    sent = []

    def handler(request):
        sent.append(request)
        return reply(json.dumps(LABEL))

    with pytest.raises(SpendCapExceeded):
        reader(tmp_path, handler, cap="0.000001").read(PHOTO, RC, mime="image/png")
    assert sent == []


def test_a_length_stop_is_not_retried(tmp_path):
    replies = iter([reply("{\"label_text\": \"Con", finish="length"), reply(json.dumps(LABEL))])
    with pytest.raises(ProviderError) as caught:
        reader(tmp_path, lambda request: next(replies)).read(PHOTO, RC, mime="image/png")
    assert caught.value.retryable is False
    assert len(ledger_lines(tmp_path)) == 1


# --- it plugs into the loop ---------------------------------------------------------------------------------

def test_the_reader_plugs_into_run_intake(tmp_path):
    from anamnesis.schema import AudioTurn
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=3000, transcript="Concor 5 mg once a day.")]
    from tests.contract.test_b19_brief import mg
    report = run_intake(b"wav", [(PHOTO, "image/png")], transcriber=Transcriber(turns),
                        extractor=Extractor([claim("c1", "Concor", ["turn-0"], intake=mg("Concor", 5), per_day=1)]),
                        segmenter=Segmenter({RC.image_sha256: [RC]}),
                        reader=reader(tmp_path, lambda request: reply(json.dumps(LABEL))), catalogue=CAT)
    [observation] = report.observations
    assert observation.label_text.startswith("Concor 5 mg")
    assert [f.type.value for f in report.findings] == ["match"]

