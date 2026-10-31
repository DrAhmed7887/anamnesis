"""Batch 24 round 4: the supervisor's round 3 review and the CEO's idiom sweep (evidence/batches/24/supervisor.md),
pinned (SPEC §2, round 4). Each idiom below states a number nobody said, and an invented amount of that number
reached a false match."""

import json
from decimal import Decimal

import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all
from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.stated import stated_amounts
from anamnesis.schema import AudioTurn, IngredientAmount, PackObservation, Strength
from anamnesis.schema import DiscrepancyType as D

CAT = load_catalogue()


def finding(said, name, inn, amount, label):
    turn = AudioTurn(turn_id="turn-0", start_ms=0, end_ms=1000, transcript=said, speaker=None, lang_hint="en")
    raw = {"name_text": name, "inn": inn, "strength": None, "intake_amount": {"inn": inn, "amount": amount, "unit": "mg"},
           "regimen": None, "status": "active", "turn_ids": ["turn-0"]}
    [claim] = parse_claims_json(json.dumps({"claims": [raw]}, ensure_ascii=False), [turn])
    pack = PackObservation(observation_id="o1", label_text=label, readability="readable", visual_evidence=["r_o1"],
                           strength=Strength(ingredients=[IngredientAmount(inn=inn, amount=Decimal(amount), unit="mg")],
                                             per="tablet", release="unknown"))
    [found] = reconcile_all([claim], [pack], CAT)
    return found.type


@pytest.mark.parametrize(("said", "name", "inn", "amount", "label"), [
    ("Ich nehme Concor jeden Tag um halb zwei.", "Concor", "bisoprolol", "2.5", "Concor 2,5 mg"),  # 1:30
    ("Tomo sertralina, me bajó la ansiedad un veinte por ciento.", "sertralina", "sertraline", "100",
     "Sertralina 100 mg"),
    ("Tomo alprazolam, lo leí en un medio sobre salud.", "alprazolam", "alprazolam", "0.5", "Alprazolam 0.5 mg"),
    ("Tomo Concor a las dos y media.", "Concor", "bisoprolol", "2.5", "Concor 2,5 mg"),  # 2:30, the CEO's sweep
])
def test_an_idiom_never_lets_an_invented_amount_reach_match(said, name, inn, amount, label):
    assert finding(said, name, inn, amount, label) is D.INSUFFICIENT_INFORMATION


@pytest.mark.parametrize(("text", "value"), [
    ("halb zwei", "2.5"), ("halb zwölf", "12.5"), ("um halb acht", "7.5"), ("um halb acht", "8.5"),
    ("eine halbe Zehn-Milligramm-Tablette", "10.5"), ("uno y medio diez miligramos", "11.5"),
    ("un veinte por ciento", "100"), ("lo leí en un medio sobre salud", "0.5"), ("una media de dos al día", "0.5"),
    ("es un medio para dormir", "0.5"), ("por el trabajo y medio ambiente", "0.5"),
    ("tengo un nivel medio sobre el tema", "0.5"), ("a las dos y media", "2.5"), ("las cinco y media de la tarde", "5.5"),
])
def test_these_never_state_the_value(text, value):
    assert Decimal(value) not in stated_amounts(text)


@pytest.mark.parametrize(("text", "value"), [
    ("uno y medio comprimidos", "1.5"), ("dos y media pastillas", "2.5"), ("medio comprimido", "0.5"),
    ("media pastilla", "0.5"), ("eine halbe Tablette", "0.5"), ("zweieinhalb Tabletten", "2.5"),
    ("veinte miligramos", "20"),
])
def test_real_halves_and_numbers_still_read(text, value):
    assert Decimal(value) in stated_amounts(text)


def test_a_one_letter_word_is_grounded_only_as_a_whole_word():
    turn = AudioTurn(turn_id="turn-0", start_ms=0, end_ms=1000, transcript="Tomo vitamina C de 1000 unidades cada día.",
                     speaker=None, lang_hint="en")
    raw = {"name_text": "vitamina C", "inn": "vitamin d", "strength": None, "intake_amount": None, "regimen": None,
           "status": "active", "turn_ids": ["turn-0"]}
    [claim] = parse_claims_json(json.dumps({"claims": [raw]}, ensure_ascii=False), [turn])
    assert claim.inn is None
