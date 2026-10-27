"""Batch 8 contract: Muse Spark extracts PatientClaims from transcript turns. Written by the reviewer; do not edit.

Offline: a fake HTTP transport replays what Spark would return. The live run is scripts/smoke_live.py.
"""

import json
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all
from anamnesis.providers import ProviderError, SpendCapExceeded, SpendGuard
from anamnesis.providers.claims import CLAIMS_SCHEMA, MetaClaimExtractor, parse_claims_json
from anamnesis.providers.meta import MetaClient
from anamnesis.providers.spark import LabelReading
from anamnesis.schema import AudioTurn, MedicationStatus, PackObservation
from anamnesis.schema import DiscrepancyType as D

FIX = Path(__file__).parents[1] / "fixtures"
TURNS = [AudioTurn.model_validate(t) for t in
         json.loads((FIX / "voice_en_live_2026-10-27.json").read_text(encoding="utf-8"))["turns"]]

# What Spark should return for the live English voice note (amounts with a frequency are intakes).
CLAIMS = {"claims": [
    {"name_text": "Concor", "inn": None, "strength": None,
     "intake_amount": {"inn": "bisoprolol", "amount": "5", "unit": "mg"},
     "regimen": {"units_per_intake": None, "intakes_per_day": "1", "as_needed": None},
     "status": "active", "turn_ids": ["turn-0"]},
    {"name_text": "Metoprolol", "inn": "metoprolol", "strength": None,
     "intake_amount": {"inn": "metoprolol", "amount": "50", "unit": "mg"},
     "regimen": {"units_per_intake": None, "intakes_per_day": "2", "as_needed": None},
     "status": "active", "turn_ids": ["turn-0"]},
    {"name_text": "Panadol", "inn": None, "strength": None, "intake_amount": None, "regimen": None,
     "status": "discontinued", "turn_ids": ["turn-0"]},
]}


class Recorder:
    def __init__(self, *responses):
        self.responses, self.requests = list(responses), []

    def __call__(self, request):
        self.requests.append(request)
        return httpx.Response(200, json=self.responses.pop(0))


def chat(content, usage=(800, 300)):
    return {"id": "chat_c", "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": usage[0], "completion_tokens": usage[1]}}


@pytest.fixture
def guard(tmp_path):
    return SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal("5.00"))


def extractor(rec, guard, **kw):
    return MetaClaimExtractor(MetaClient(api_key="LLM_t_s", transport=httpx.MockTransport(rec)), guard, **kw)


# --- parsing ---------------------------------------------------------------------------

def test_parse_maps_each_claim_with_ids_and_evidence():
    claims = parse_claims_json(json.dumps(CLAIMS), TURNS)
    assert [c.claim_id for c in claims] == ["c1", "c2", "c3"]
    assert all(c.audio_evidence == ["turn-0"] for c in claims)
    concor, meto, panadol = claims
    assert concor.intake_amount.amount == Decimal(5) and concor.regimen.intakes_per_day == Decimal(1)
    assert concor.regimen.as_needed is None  # unknown stays unknown
    assert meto.intake_amount.inn == "metoprolol" and meto.strength is None
    assert panadol.status is MedicationStatus.DISCONTINUED


def test_parse_splits_salts_through_the_schema():
    one = {"claims": [dict(CLAIMS["claims"][0],
                           intake_amount={"inn": "Bisoprolol fumarate", "amount": "5", "unit": "mg"})]}
    (claim,) = parse_claims_json(json.dumps(one), TURNS)
    assert (claim.intake_amount.inn, claim.intake_amount.salt) == ("bisoprolol", "fumarate")


def test_no_medicines_mentioned_is_an_empty_list():
    assert parse_claims_json('{"claims": []}', TURNS) == []


@pytest.mark.parametrize("bad", [
    "not json",
    json.dumps({"claims": [dict(CLAIMS["claims"][0], turn_ids=["turn-9"])]}),   # cites a turn that doesn't exist
    json.dumps({"claims": [dict(CLAIMS["claims"][0], turn_ids=[])]}),           # no evidence
    json.dumps({"claims": [dict(CLAIMS["claims"][0], advice="take two")]}),     # extra field
    json.dumps({"claims": [dict(CLAIMS["claims"][0], status="maybe")]}),        # outside the closed enum
])
def test_invalid_extractions_are_retryable_errors(bad):
    with pytest.raises(ProviderError) as e:
        parse_claims_json(bad, TURNS)
    assert e.value.retryable is True


# --- the live adapter, offline -------------------------------------------------------------

def test_extractor_request_shape(guard):
    rec = Recorder(chat(json.dumps(CLAIMS)))
    claims, trace = extractor(rec, guard).extract(TURNS)
    sent = json.loads(rec.requests[0].content)
    assert str(rec.requests[0].url) == "https://api.meta.ai/v1/chat/completions"
    assert sent["model"] == "muse-spark-1.3" and sent["response_format"]["type"] == "json_schema"
    assert "$ref" not in json.dumps(sent["response_format"]) and "$ref" not in json.dumps(CLAIMS_SCHEMA)
    prompt = json.dumps(sent["messages"], ensure_ascii=False)
    assert "turn-0" in prompt and "Concor five milligrams" in prompt   # turns are cited by id, text verbatim
    assert "advice" in prompt.lower()                                 # the system prompt forbids advice
    assert len(claims) == 3 and trace.cost_usd == Decimal("0.001") + Decimal("0.001275")
    assert guard.total_usd == trace.cost_usd


def test_extractor_retries_once_and_pays_for_both(guard):
    rec = Recorder(chat("oops"), chat(json.dumps(CLAIMS)))
    claims, _ = extractor(rec, guard).extract(TURNS)
    assert len(claims) == 3 and len(rec.requests) == 2
    assert len(guard.ledger_path.read_text(encoding="utf-8").splitlines()) == 2


def test_extractor_refuses_contributor_models(guard):
    with pytest.raises(ValueError):
        extractor(Recorder(), guard, model="muse-spark-1.3-contributor")


def test_extractor_respects_the_spend_cap(tmp_path):
    rec = Recorder()
    with pytest.raises(SpendCapExceeded):
        extractor(rec, SpendGuard(tmp_path / "l.jsonl", cap_usd=Decimal("0.001"))).extract(TURNS)
    assert rec.requests == []


def test_no_turns_means_no_call(guard):
    rec = Recorder()
    assert extractor(rec, guard).extract([]) == ([], None)
    assert rec.requests == []


# --- end to end, offline: extracted claims vs the live label readings ------------------------

def test_extracted_claims_reconcile_against_the_live_packs(guard):
    claims, _ = extractor(Recorder(chat(json.dumps(CLAIMS))), guard).extract(TURNS)
    packs = []
    for i, item in enumerate(json.loads((FIX / "spark_labels_live_2026-10-27.json").read_text(encoding="utf-8"))):
        r = LabelReading.model_validate(item["reading"])
        packs.append(PackObservation(observation_id=f"o{i}", label_text=r.label_text, inn=r.inn, strength=r.strength,
                                     readability=r.readability, country=r.country, visual_evidence=[r.region_id]))
    found = {(f.claim_id, f.observation_id): f.type for f in reconcile_all(claims, packs, load_catalogue())}
    assert found == {
        ("c1", "o1"): D.MATCH,                               # Concor 5 mg once a day = one 5 mg tablet
        ("c2", "o0"): D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH,   # metoprolol 50 mg vs Beloc-Zok 100 mg (scored)
        ("c3", None): D.MISSING_MODALITY,                    # Panadol: stopped, and no pack in the photo
    }
