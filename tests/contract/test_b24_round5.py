"""Batch 24 round 5: the supervisor's round 4 review (evidence/batches/24/supervisor.md), pinned (SPEC §2, round 5).
Each case stated a number nobody said, and an invented amount of that number reached a false match."""

import json
import unicodedata
from decimal import Decimal

import pytest

from anamnesis.core.catalogue import load_catalogue, normalise
from anamnesis.core.reconcile import reconcile_all
from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.stated import stated_amounts
from anamnesis.schema import AudioTurn, IngredientAmount, PackObservation, Strength
from anamnesis.schema import DiscrepancyType as D

CAT = load_catalogue()


def turn(said):
    return AudioTurn(turn_id="turn-0", start_ms=0, end_ms=1000, transcript=said, speaker=None, lang_hint="en")


def finding(said, name, inn, amount, label):
    raw = {"name_text": name, "inn": inn, "strength": None, "intake_amount": {"inn": inn, "amount": amount, "unit": "mg"},
           "regimen": None, "status": "active", "turn_ids": ["turn-0"]}
    [claim] = parse_claims_json(json.dumps({"claims": [raw]}, ensure_ascii=False), [turn(said)])
    pack = PackObservation(observation_id="o1", label_text=label, readability="readable", visual_evidence=["r_o1"],
                           strength=Strength(ingredients=[IngredientAmount(inn=inn, amount=Decimal(amount), unit="mg")],
                                             per="tablet", release="unknown"))
    [found] = reconcile_all([claim], [pack], CAT)
    return found.type


@pytest.mark.parametrize(("said", "name", "inn", "amount", "label"), [
    ("Tomo Lipitor a las diez treinta de la noche.", "Lipitor", "atorvastatin", "40", "Lipitor 40 mg"),  # 10:30
    ("Ich nehme Lipitor abends um zehn dreißig.", "Lipitor", "atorvastatin", "40", "Lipitor 40 mg"),
    ("Tomo Concor, dos tres pastillas al día.", "Concor", "bisoprolol", "5", "Concor 5 mg"),
    ("Ich nehme Concor so zwei drei Tabletten am Tag.", "Concor", "bisoprolol", "5", "Concor 5 mg"),
    ("Ich nehme Concor, zweieinhalb Fünf-Milligramm-Tabletten am Tag.", "Concor", "bisoprolol", "7.5", "Concor 7,5 mg"),
    ("Tomo Concor, un comprimido a las dos y medio comprimido a las diez.", "Concor", "bisoprolol", "2.5",
     "Concor 2,5 mg"),  # a clock hour, then a half before a dose word
    ("Ich nehme Candesartan, beim Blutdruck muss ich mich in Acht nehmen.", "Candesartan", "candesartan", "8",
     "Candesartan 8 mg"),  # "in Acht nehmen": to take care
])
def test_an_idiom_never_lets_an_invented_amount_reach_match(said, name, inn, amount, label):
    assert finding(said, name, inn, amount, label) is D.INSUFFICIENT_INFORMATION


@pytest.mark.parametrize(("text", "value"), [
    ("dos cincuenta", "52"), ("zwei fünfzig", "52"), ("a las ocho cuarenta y cinco", "53"),
    ("una pastilla a las siete y media pastilla a las nueve", "7.5"), ("a la una y medio comprimido", "1.5"),
    ("außer Acht lassen", "8"), ("Acht geben", "8"),
])
def test_these_never_state_the_value(text, value):
    assert Decimal(value) not in stated_amounts(text)


@pytest.mark.parametrize(("text", "value"), [
    ("ciento veinte miligramos", "120"), ("doscientos cincuenta miligramos", "250"), ("mil quinientos miligramos", "1500"),
    ("cuarenta y cinco miligramos", "45"), ("una y media pastillas", "1.5"), ("acht Tabletten", "8"),
])
def test_these_still_read(text, value):
    assert Decimal(value) in stated_amounts(text)


def test_a_decomposed_number_word_label_takes_the_claims_name():
    label = unicodedata.normalize("NFD", "fünf")
    raw = {"name_text": "Farxiga", "inn": None, "strength": None, "intake_amount": {"inn": label, "amount": "5", "unit": "mg"},
           "regimen": None, "status": "active", "turn_ids": ["turn-0"]}
    said = unicodedata.normalize("NFD", "Farxiga fünf Milligramm")  # both decomposed, as a transcript can arrive
    [claim] = parse_claims_json(json.dumps({"claims": [raw]}, ensure_ascii=False), [turn(said)])
    assert claim.intake_amount is not None and normalise(claim.intake_amount.inn) == "farxiga"
