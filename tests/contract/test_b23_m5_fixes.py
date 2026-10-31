"""Batch 23 contract, part 2: the Gemini 4 milestone review M5, findings #5–#7 (evidence/grills/m5-openweight/
effect.md). Written by the CEO; Muse must not edit it.

#5 is a pin, not a change: a regimen count is not checked against the turns (SPEC §2 Known limits), so an unstated
"two" can still reach intake_differs_from_unit_strength, but never `match`. #6: `catalogue.normalise` maps both
Arabic-Indic digit sets. #7: every reader, the claim extractor and ProviderTrace refuse a contributor model wherever
the word is, as the open-weight reader does since batch 22 round 2.
"""

import json
from decimal import Decimal

import httpx
import pytest

from anamnesis.core.catalogue import normalise
from anamnesis.providers import SpendGuard
from anamnesis.providers.base import ProviderTrace
from anamnesis.providers.claims import MetaClaimExtractor, parse_claims_json
from anamnesis.providers.meta import MetaClient, MetaLabelReader
from anamnesis.schema import AudioTurn
from tests.contract import test_b19_brief as b19

IDS = ["muse-spark-1.3-Contributor", "muse-spark-1.3-contributor-v2", " muse-spark-1.3-contributor ",
       "accounts/x/models/muse-spark-1.3-contributor:latest"]


def client():
    return MetaClient(api_key="LLM_t_s", transport=httpx.MockTransport(lambda request: httpx.Response(500)))


# --- #7: no contributor model, wherever the word is ----------------------------------------------------------

@pytest.mark.parametrize("model", IDS)
def test_no_reader_or_extractor_takes_a_contributor_model(tmp_path, model):
    guard = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal("1"))
    with pytest.raises(ValueError):
        MetaLabelReader(client(), guard, model=model)
    with pytest.raises(ValueError):
        MetaClaimExtractor(client(), guard, model=model)


@pytest.mark.parametrize("model", IDS)
def test_a_trace_refuses_a_contributor_model(model):
    with pytest.raises(ValueError):
        ProviderTrace(call_id="c", model_id=model, latency_ms=0, input_tokens=0, output_tokens=0,
                      cost_usd=Decimal(0))


def test_the_standard_models_are_still_accepted(tmp_path):
    guard = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal("1"))
    MetaLabelReader(client(), guard, model="muse-spark-1.3")
    MetaClaimExtractor(client(), guard, model="muse-spark-1.3")
    ProviderTrace(call_id="c", model_id="muse-spark-1.3", latency_ms=0, input_tokens=0, output_tokens=0,
                  cost_usd=Decimal(0))


# --- #6: both Arabic-Indic digit sets normalise to ASCII ------------------------------------------------------

def test_normalise_maps_both_arabic_indic_digit_sets():
    assert normalise("۰۱۲۳۴۵۶۷۸۹") == normalise("٠١٢٣٤٥٦٧٨٩") == "0123456789"
    assert normalise("كونكور ۵") == normalise("كونكور ٥") == normalise("كونكور 5")


# --- #5: an unstated units count never reaches match ---------------------------------------------------------

@pytest.mark.parametrize("units", ["two", "2", "اتنين"])
def test_an_unstated_units_count_never_reaches_match(units):
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=3000, transcript="I take Concor 5 mg every morning.")]
    raw = {"name_text": "Concor", "inn": "bisoprolol", "strength": None, "status": "active", "turn_ids": ["turn-0"],
           "regimen": {"units_per_intake": units, "intakes_per_day": "1", "as_needed": False},
           "intake_amount": {"inn": "bisoprolol", "amount": "5", "unit": "mg"}}
    [found] = parse_claims_json(json.dumps({"claims": [raw]}), turns)
    pack = b19.reading("Concor 5 mg\nBisoprolol fumarate", b19.st(b19.mg("bisoprolol fumarate", 5)))
    report = b19.intake(b19.AUDIO[0], [(b19.PHOTO, "image/png")], turns=turns, claims=[found],
                        by_sha={b19.RC.image_sha256: [b19.RC]}, reads={b19.RC.region_id: [pack]})
    assert report.findings
    assert "match" not in [finding.type.value for finding in report.findings]
