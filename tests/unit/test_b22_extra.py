"""Batch 22 gaps the contract leaves: request shape, client errors, and one-word amounts."""

import json
from decimal import Decimal

import httpx
import pytest

from anamnesis.providers import ProviderError
from anamnesis.providers.meta import LABEL_SCHEMA, spark_call_estimate
from anamnesis.providers.numbers import parse_amount_text
from anamnesis.providers.openweight import PRESETS, OpenWeightClient, OpenWeightLabelReader
from anamnesis.providers.spend import SpendCapExceeded, SpendGuard
from anamnesis.providers.stated import stated_amounts
from tests.contract.test_b19_brief import PHOTO, RC

KEY = "ow_secret_for_test"
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


def test_the_baseten_preset_names_its_model():
    assert PRESETS["baseten"]["model"] == "meta-models/muse-spark-open"
    assert PRESETS["baseten"]["json_mode"] is False


@pytest.mark.parametrize("provider", ["fireworks", "baseten"])
def test_it_sends_max_tokens_and_no_reasoning_effort(tmp_path, provider):
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        content = json.dumps(LABEL) if provider == "fireworks" else "```\n" + json.dumps(LABEL) + "\n```"
        return reply(content)

    reader(tmp_path, handler, provider=provider,
           json_mode=PRESETS[provider]["json_mode"]).read(PHOTO, RC, mime="image/png")
    assert seen[0]["max_tokens"] == 4000
    assert "reasoning_effort" not in seen[0]


def test_without_json_mode_the_schema_sentence_is_appended_and_a_plain_fence_parses(tmp_path):
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return reply("```\n" + json.dumps(LABEL) + "\n```")

    reading, _ = reader(tmp_path, handler, json_mode=False, provider="baseten").read(
        PHOTO, RC, mime="image/png")
    [text] = [part["text"] for part in seen[0]["messages"][1]["content"] if part["type"] == "text"]
    assert text.endswith("Reply with only one JSON object that matches this JSON schema: "
                         + json.dumps(LABEL_SCHEMA, sort_keys=True))
    assert reading.strength.ingredients[0].amount == Decimal("5")


def test_client_errors_name_the_provider_and_keep_metas_classes(tmp_path):
    def status_500(request):
        return httpx.Response(500, json={"error": {"message": "boom"}})

    with pytest.raises(ProviderError) as caught:
        reader(tmp_path, status_500, provider="baseten").read(PHOTO, RC, mime="image/png")
    assert caught.value.provider == "baseten"
    assert caught.value.retryable and caught.value.billable_uncertain

    def timeout(request):
        raise httpx.ConnectTimeout("slow")

    with pytest.raises(ProviderError) as caught:
        reader(tmp_path, timeout).read(PHOTO, RC, mime="image/png")
    assert caught.value.provider == "fireworks"
    assert caught.value.retryable and caught.value.billable_uncertain

    with pytest.raises(ProviderError) as caught:
        reader(tmp_path, lambda request: httpx.Response(200, content=b"not json {{{")).read(
            PHOTO, RC, mime="image/png")
    assert caught.value.provider == "fireworks" and caught.value.retryable


def test_a_rejected_request_is_not_retryable_and_not_charged(tmp_path):
    with pytest.raises(ProviderError) as caught:
        reader(tmp_path, lambda request: httpx.Response(400, json={"error": {"message": "bad"}})).read(
            PHOTO, RC, mime="image/png")
    assert caught.value.provider == "fireworks"
    assert not caught.value.retryable and not caught.value.billable_uncertain


def test_the_estimate_is_priced_by_price_key(tmp_path):
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return reply(json.dumps(LABEL))

    reader(tmp_path, handler).read(PHOTO, RC, mime="image/png")
    estimate = spark_call_estimate({**seen[0], "model": "muse-spark-open@fireworks"})
    sent = []
    with pytest.raises(SpendCapExceeded):
        reader(tmp_path, lambda request: sent.append(request) or reply(json.dumps(LABEL)),
               cap=str(estimate - Decimal("0.000001"))).read(PHOTO, RC, mime="image/png")
    assert sent == []


@pytest.mark.parametrize("text,value", [
    ("TEN", "10"), ("  three  ", "3"), ("الفين", "2000"), ("تلتمية", "300"), ("تسعين", "90"),
])
def test_more_single_number_words_parse(text, value):
    assert parse_amount_text(text) == Decimal(value)


@pytest.mark.parametrize("text", ["twenty-five", "نص", "thousand", "2 five", "five5", "once a day"])
def test_more_than_one_word_is_still_rejected(text):
    assert parse_amount_text(text) is None


@pytest.mark.parametrize("text", ["<five", "-five", "five?", "(five)", "خُمس"])
def test_a_qualified_or_vowelled_word_does_not_parse(text):
    assert parse_amount_text(text) is None


@pytest.mark.parametrize("model", [
    "muse-spark-open-Contributor",
    "accounts/fireworks/models/muse-spark-open-contributor:latest",
])
def test_a_contributor_model_is_refused_anywhere(tmp_path, model):
    client = OpenWeightClient(api_key=KEY, base_url=PRESETS["fireworks"]["base_url"],
                              provider="fireworks",
                              transport=httpx.MockTransport(lambda request: reply("{}")))
    with pytest.raises(ValueError):
        OpenWeightLabelReader(client, guard(tmp_path), model=model,
                              price_key="muse-spark-open@fireworks", json_mode=True)


def test_stated_amounts_still_reads_runs_of_words():
    assert Decimal(250) in stated_amounts("two hundred and fifty")
    assert Decimal(5) in stated_amounts("five")
