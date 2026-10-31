"""Batch 29 contract: Spark 1.3's claim prompt adds one sentence for combination products (SPEC §2, "Prompts",
batch 29), from U2's live misses and a pilot (evidence/batches/29/). The tuned Glimmer keeps the prompt it was
trained on. Written by the CEO; Muse must not edit it."""

import json
from decimal import Decimal

import httpx

from anamnesis.providers import SpendGuard
from anamnesis.providers.claims import _SYSTEM_PROMPT, MetaClaimExtractor, parse_claims_json
from anamnesis.providers.meta import MetaClient
from anamnesis.schema import AudioTurn
from finetune.common import SYSTEM_CONTENT
from tests.contract.test_b26_open_weight_path import TURNS as CONCOR_TURNS
from tests.contract.test_b26_open_weight_path import _extractor as glimmer_extractor
from tests.contract.test_b26_open_weight_path import _payload

SENTENCE = ("A combination product said with one amount per ingredient, such as 'Augmentin 875 and 125 "
            "milligrams', is its strength: one ingredient per amount, in the order said, each named for the "
            "ingredient it belongs to.")
U2 = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=4000,
                transcript="I take Augmentin, 875 and 125 milligrams, twice a day")]
U2_REPLY = {"claims": [{
    "name_text": "Augmentin", "inn": None,
    "strength": {"ingredients": [{"inn": "amoxicillin", "amount": "875", "unit": "mg"},
                                 {"inn": "clavulanic acid", "amount": "125", "unit": "mg"}],
                 "per": "tablet", "release": "unknown"},
    "intake_amount": None, "regimen": {"units_per_intake": None, "intakes_per_day": "2", "as_needed": None},
    "status": "active", "turn_ids": ["turn-0"]}]}


def _spark(tmp_path, reply):
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "chat_1", "choices": [{"message": {"role": "assistant",
                              "content": json.dumps(reply)}, "finish_reason": "stop"}],
                              "usage": {"prompt_tokens": 900, "completion_tokens": 200}})

    client = MetaClient(api_key="LLM_t_s", transport=httpx.MockTransport(handler))
    return MetaClaimExtractor(client, SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal(5))), sent


def test_spark_gets_the_trained_prompt_and_the_combination_sentence(tmp_path):
    extractor, sent = _spark(tmp_path, U2_REPLY)
    extractor.extract(U2)
    assert sent[0]["messages"][0] == {"role": "system", "content": f"{_SYSTEM_PROMPT} {SENTENCE}"}


def test_a_combination_said_as_two_amounts_keeps_its_strength(tmp_path):
    extractor, _ = _spark(tmp_path, U2_REPLY)
    claims, _ = extractor.extract(U2)
    assert [(part.inn, part.amount) for part in claims[0].strength.ingredients] == [
        ("amoxicillin", Decimal(875)), ("clavulanic acid", Decimal(125))]
    assert parse_claims_json(json.dumps(U2_REPLY), U2)[0].strength is not None


def test_the_trained_prompt_is_unchanged():
    assert "combination product" not in _SYSTEM_PROMPT
    assert SYSTEM_CONTENT == f"{_SYSTEM_PROMPT}\nReasoning strength: low"


def test_the_tuned_glimmer_is_never_sent_the_sentence(tmp_path):
    extractor, _, seen = glimmer_extractor(tmp_path, [_payload()])
    extractor.extract(CONCOR_TURNS)
    system = json.loads(seen[0].content)["messages"][0]["content"]
    assert system == SYSTEM_CONTENT and SENTENCE not in system


def test_the_advice_sentences_stay_word_for_word_in_sparks_prompt(tmp_path):
    extractor, sent = _spark(tmp_path, U2_REPLY)
    extractor.extract(U2)
    system = sent[0]["messages"][0]["content"]
    assert "Give no medical advice. Only report what the patient said." in system
    assert system.startswith(_SYSTEM_PROMPT)
