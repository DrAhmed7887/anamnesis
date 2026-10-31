"""Batch 29 gaps the contract leaves: the sentence constant, the join, and who gets what prompt."""

import json
from decimal import Decimal

import httpx

from anamnesis.providers import SpendGuard
from anamnesis.providers.claims import (
    _COMBINATION_SENTENCE,
    _SPARK_CLAIM_PROMPT,
    _SYSTEM_PROMPT,
    MetaClaimExtractor,
)
from anamnesis.providers.glimmer import _SYSTEM_PROMPT as GLIMMER_PROMPT
from anamnesis.providers.meta import MetaClient
from anamnesis.schema import AudioTurn
from finetune.common import SYSTEM_CONTENT

TURNS = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=2500,
                  transcript="I take one tablet every morning.")]


def test_the_combination_sentence_is_the_specs_word_for_word():
    assert _COMBINATION_SENTENCE == (
        "A combination product said with one amount per ingredient, such as "
        "'Augmentin 875 and 125 milligrams', is its strength: one ingredient per amount, "
        "in the order said, each named for the ingredient it belongs to.")


def test_sparks_claim_prompt_is_the_trained_prompt_plus_one_space_plus_the_sentence():
    assert _SPARK_CLAIM_PROMPT == f"{_SYSTEM_PROMPT} {_COMBINATION_SENTENCE}"
    assert _SPARK_CLAIM_PROMPT[len(_SYSTEM_PROMPT)] == " "
    assert "combination product" not in _SYSTEM_PROMPT


def test_spark_sends_sparks_claim_prompt_as_its_system_message(tmp_path):
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "chat_1", "choices": [{"message": {"role": "assistant",
                              "content": '{"claims": []}'}, "finish_reason": "stop"}],
                              "usage": {"prompt_tokens": 900, "completion_tokens": 10}})

    client = MetaClient(api_key="LLM_t_s", transport=httpx.MockTransport(handler))
    claims, _ = MetaClaimExtractor(client, SpendGuard(tmp_path / "ledger.jsonl",
                                                     cap_usd=Decimal(5))).extract(TURNS)
    assert claims == []
    assert sent[0]["messages"][0] == {"role": "system", "content": _SPARK_CLAIM_PROMPT}


def test_glimmer_and_the_finetune_keep_the_trained_prompt_without_the_sentence():
    assert GLIMMER_PROMPT == SYSTEM_CONTENT == f"{_SYSTEM_PROMPT}\nReasoning strength: low"
    assert _COMBINATION_SENTENCE not in GLIMMER_PROMPT
    assert _COMBINATION_SENTENCE not in SYSTEM_CONTENT
