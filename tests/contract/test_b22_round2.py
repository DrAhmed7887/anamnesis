"""Batch 22 contract, round 2: the supervisor's findings of 28 Oct (evidence/batches/22/supervisor.md). Written by
the CEO; Muse must not edit it.

1. A word amount with a sign, comparator, punctuation or tashkeel never parses (SPEC §2). After round 1, "<five"
   ("less than five milligrams") parsed as 5 and the intake reached `match`, and «خُمس» (a fifth) parsed as 5.
2. A model id with "-contributor" anywhere, in any case, is refused, as scripts/batch.sh refuses it.
3. The open-weight reader's own errors name its provider, never "spark".
4. Pins for paths no test covered: the estimate is priced by `price_key`, estimated ledger lines name `price_key`,
   the client's default timeout is 60 s, and the key never appears in a parse error.
"""

import json
from decimal import Decimal

import httpx
import pytest

from anamnesis.providers import ProviderError, base
from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.numbers import parse_amount_text
from anamnesis.providers.openweight import PRESETS, OpenWeightClient, OpenWeightLabelReader
from anamnesis.providers.spend import SpendCapExceeded
from anamnesis.schema import AudioTurn
from tests.contract.test_b19_brief import PHOTO, RC
from tests.contract.test_b22_openweight import KEY, LABEL, guard, ledger_lines, reader, reply

# --- 1. only a bare number word parses ----------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "-five", "~five", "<five", ">five", "five?", "five+", "five%", "≈five", "(five)", "five.", "five,",
    "خُمس", "عُشر", "سُبع", "تُسع", "خَمسة",
])
def test_a_word_with_a_sign_mark_or_tashkeel_does_not_parse(text):
    assert parse_amount_text(text) is None


@pytest.mark.parametrize("text,value", [("FIVE", "5"), ("خمســة", "5"), ("خمسه", "5"), ("إثنين", "2"), ("خمس", "5")])
def test_letter_variants_and_tatweel_still_parse(text, value):
    assert parse_amount_text(text) == Decimal(value)


@pytest.mark.parametrize("amount", ["<five", ">five", "~five", "five?", "-five"])
def test_a_qualified_amount_is_never_kept_as_exact(amount):
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=3000,
                       transcript="I take Concor, less than five milligrams.")]
    raw = {"name_text": "Concor", "inn": None, "strength": None, "regimen": None, "status": "active",
           "turn_ids": ["turn-0"], "intake_amount": {"inn": "Concor", "amount": amount, "unit": "mg"}}
    [found] = parse_claims_json(json.dumps({"claims": [raw]}), turns)
    assert found.intake_amount is None


# --- 2. a contributor model is refused wherever the word is -------------------------------------------------

@pytest.mark.parametrize("model", [
    "muse-spark-open-Contributor", "muse-spark-open-contributor-v2",
    "accounts/fireworks/models/muse-spark-open-contributor:latest", "muse-spark-open-contributor ",
])
def test_a_contributor_model_is_refused_wherever_the_word_is(tmp_path, model):
    client = OpenWeightClient(api_key=KEY, base_url=PRESETS["fireworks"]["base_url"], provider="fireworks",
                              transport=httpx.MockTransport(lambda request: reply("{}")))
    with pytest.raises(ValueError):
        OpenWeightLabelReader(client, guard(tmp_path), model=model, price_key="muse-spark-open@fireworks",
                              json_mode=True)


# --- 3. the reader's own errors name its provider ------------------------------------------------------------

def _no_usage(request):
    return httpx.Response(200, json={"id": "cmpl-x", "choices": [{"message": {"content": "{}"}}]})


@pytest.mark.parametrize("provider", ["fireworks", "baseten"])
@pytest.mark.parametrize("handler", [
    _no_usage,
    lambda request: reply(json.dumps(LABEL), finish="length"),
    lambda request: reply(json.dumps(dict(LABEL, inn="double the dose"))),
], ids=["malformed payload", "length stop", "label that fails the parse"])
def test_the_reader_s_own_errors_name_its_provider(tmp_path, provider, handler):
    with pytest.raises(ProviderError) as caught:
        reader(tmp_path, handler, provider=provider, json_mode=PRESETS[provider]["json_mode"]).read(
            PHOTO, RC, mime="image/png")
    assert caught.value.provider == provider


# --- 4. spend, timeout and key pins -------------------------------------------------------------------------

def test_the_estimate_is_priced_by_the_price_key(tmp_path, monkeypatch):
    dear = {name: rate * 1000 for name, rate in base._PRICES["muse-spark-open@fireworks"].items()}
    monkeypatch.setitem(base._PRICES, "muse-spark-open@fireworks", dear)
    sent = []

    def handler(request):
        sent.append(request)
        return reply(json.dumps(LABEL))

    with pytest.raises(SpendCapExceeded):
        reader(tmp_path, handler).read(PHOTO, RC, mime="image/png")
    assert sent == []


def test_estimated_ledger_lines_name_the_price_key(tmp_path):
    def handler(request):
        raise httpx.ConnectTimeout("timed out", request=request)

    with pytest.raises(ProviderError):
        reader(tmp_path, handler).read(PHOTO, RC, mime="image/png")
    lines = ledger_lines(tmp_path)
    assert len(lines) == 2
    assert {line["model_id"] for line in lines} == {"muse-spark-open@fireworks"}


def test_the_client_waits_60_seconds_by_default(tmp_path):
    seen = {}

    def handler(request):
        seen.update(request.extensions["timeout"])
        return reply(json.dumps(LABEL))

    reader(tmp_path, handler).read(PHOTO, RC, mime="image/png")
    assert seen["read"] == 60.0


def test_the_key_never_appears_in_a_parse_error(tmp_path):
    echoed = json.dumps(dict(LABEL, readability=KEY))  # pydantic quotes the bad value in its error
    with pytest.raises(ProviderError) as caught:
        reader(tmp_path, lambda request: reply(echoed)).read(PHOTO, RC, mime="image/png")
    assert KEY not in str(caught.value)
