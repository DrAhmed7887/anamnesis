"""Batch 20 contract, part 1: a number a model writes is kept only if the source states it. Written by the CEO; Muse
must not edit it.

SPEC §2 "Amounts must be stated". The legal-agent workshop (meta-models, 27 Oct) refuses a quote that is not on the
page. Batch 16 already did that for `name_text`; here it covers every amount: a claim amount must be stated in a turn
the claim cites, digits or number words in English or Arabic, and a label amount must be printed in `label_text`.
An amount that isn't stated is dropped like one that doesn't parse, so it can never decide a finding.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_pair
from anamnesis.providers.base import ProviderError
from anamnesis.providers.claims import _SYSTEM_PROMPT as CLAIM_PROMPT
from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.meta import _SYSTEM_PROMPT as LABEL_PROMPT
from anamnesis.providers.spark import parse_label_json
from anamnesis.providers.stated import stated_amounts
from anamnesis.schema import AudioTurn, IngredientAmount, PackObservation, Strength
from anamnesis.schema import DiscrepancyType as D

ROOT = Path(__file__).resolve().parents[2]
CAT = load_catalogue()


def n(*values):
    return {Decimal(v) for v in values}


# --- stated_amounts: digits ------------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("Concor 5 mg", n("5")),
    ("Concor 2,5 mg", n("2.5")),
    ("2.5mg twice", n("2.5")),
    ("100mg", n("100")),
    ("0.125 mg", n("0.125")),
    ("Augmentin 875 mg/125 mg", n("875", "125")),
    ("كونكور ٥ ملغ", n("5")),
    ("٢٫٥ ملي", n("2.5")),
    ("one or 2 tablets", n("1", "2")),
])
def test_digits_are_stated(text, expected):
    assert expected <= stated_amounts(text)


@pytest.mark.parametrize("text", ["1,000 mg", "1.000 mg", "2.500 mg", "0 mg", "once a day", "twice", "", "مرتين"])
def test_ambiguous_numbers_zero_and_frequency_words_state_nothing(text):
    assert stated_amounts(text) == frozenset()


def test_the_result_is_a_frozenset_of_decimals():
    found = stated_amounts("Concor 5 mg")
    assert isinstance(found, frozenset) and all(isinstance(value, Decimal) for value in found)


# --- stated_amounts: English and Arabic number words -----------------------------------------------------

@pytest.mark.parametrize("text,value", [
    ("I take Concor five milligrams once a day", "5"),
    ("fifty milligrams", "50"),
    ("twenty-five mg", "25"),
    ("twelve", "12"),
    ("two hundred and fifty", "250"),
    ("two hundred fifty", "250"),
    ("one thousand", "1000"),
    ("two and a half milligrams", "2.5"),
    ("half a gram", "0.5"),
    ("two point five", "2.5"),
    ("zero point one two five", "0.125"),
    ("Five milligrams", "5"),
    ("انا باخد كونكور خمسة ملي جرام مرة في اليوم", "5"),
    ("BelocZok خمسين ملي جرام مرتين في اليوم", "50"),
    ("خمسه وعشرين", "25"),
    ("ميتين وخمسين", "250"),
    ("اتنين ونص", "2.5"),
    ("نص حباية", "0.5"),
    ("تلات ميه", "300"),
    ("خمسمية مللي", "500"),
    ("ثلاثمائة", "300"),
    ("الف", "1000"),
    ("الفين", "2000"),
    ("عشرة", "10"),
    ("خمستاشر", "15"),
    ("أربعين", "40"),
    ("وخمسين", "50"),
])
def test_number_words_are_stated(text, value):
    assert Decimal(value) in stated_amounts(text)


def test_each_word_of_a_run_also_states_its_own_value():
    assert n("2", "100", "50", "250") <= stated_amounts("two hundred and fifty")
    assert n("2", "0.5", "2.5") <= stated_amounts("اتنين ونص")


def test_words_that_are_not_numbers_end_a_run():
    found = stated_amounts("five tablets and fifty drops")
    assert n("5", "50") <= found and Decimal("55") not in found


def test_a_and_and_only_join_number_words():
    assert stated_amounts("a day and a night") == frozenset()
    assert Decimal("1.5") in stated_amounts("one and a half")


# --- claims: an amount must be stated in a turn the claim cites ------------------------------------------

TURNS = [
    AudioTurn(turn_id="turn-0", start_ms=0, end_ms=4000, transcript="I take Concor five milligrams once a day."),
    AudioTurn(turn_id="turn-1", start_ms=4000, end_ms=9000, transcript="Panadol 500 mg when I need it."),
    AudioTurn(turn_id="turn-2", start_ms=9000, end_ms=12000, transcript="It is the 10 mg box."),
]


def amount(value, inn="bisoprolol", unit="mg"):
    return {"inn": inn, "amount": value, "unit": unit}


def strength(*parts, per="tablet", release="unknown"):
    return {"ingredients": list(parts), "per": per, "release": release}


def claim(name="Concor", turn_ids=("turn-0",), **fields):
    return {"name_text": name, "inn": None, "strength": None, "intake_amount": None, "regimen": None,
            "status": "active", "turn_ids": list(turn_ids)} | fields


def parse_one(**fields):
    [found] = parse_claims_json(json.dumps({"claims": [claim(**fields)]}), TURNS)
    return found


def test_a_spoken_amount_is_kept():
    found = parse_one(intake_amount=amount("5"))
    assert found.intake_amount.amount == Decimal("5")


def test_an_amount_nobody_said_becomes_null():
    assert parse_one(intake_amount=amount("10")).intake_amount is None


def test_an_unstated_strength_takes_the_stated_intake_with_it():
    found = parse_one(intake_amount=amount("5"), strength=strength(amount("20")))
    assert found.strength is None and found.intake_amount is None


def test_an_unstated_intake_takes_the_stated_strength_with_it():
    found = parse_one(intake_amount=amount("2"), strength=strength(amount("5")))
    assert found.strength is None and found.intake_amount is None


def test_every_ingredient_of_a_combination_must_be_stated():
    turns = [AudioTurn(turn_id="t", start_ms=0, end_ms=1000, transcript="Augmentin 875 mg twice a day")]
    reply = claim("Augmentin", ("t",), strength=strength(amount("875", "amoxicillin"),
                                                          amount("125", "clavulanic acid")))
    [found] = parse_claims_json(json.dumps({"claims": [reply]}), turns)
    assert found.strength is None


def test_an_amount_said_only_in_a_turn_the_claim_does_not_cite_does_not_count():
    assert parse_one(intake_amount=amount("10")).intake_amount is None  # "10 mg" is in turn-2, not cited
    found = parse_one(turn_ids=("turn-0", "turn-2"), intake_amount=amount("10"))
    assert found.intake_amount.amount == Decimal("10")


def test_amounts_are_compared_as_numbers():
    turns = [AudioTurn(turn_id="t", start_ms=0, end_ms=1000, transcript="Concor 2,5 mg")]
    [found] = parse_claims_json(json.dumps({"claims": [claim(turn_ids=("t",), intake_amount=amount("2.50"))]}),
                                turns)
    assert found.intake_amount.amount == Decimal("2.5")


def test_half_a_gram_written_in_grams_is_stated():
    turns = [AudioTurn(turn_id="t", start_ms=0, end_ms=1000, transcript="Panadol, half a gram")]
    reply = claim("Panadol", ("t",), intake_amount=amount("0.5", "paracetamol", "g"))
    [found] = parse_claims_json(json.dumps({"claims": [reply]}), turns)
    assert found.intake_amount.amount == Decimal("0.5")


def test_an_invented_amount_cannot_decide_a_finding():
    """Concor 5 mg on the pack; the patient said "five". A reply that invents 10 mg would make strength_mismatch."""
    pack = PackObservation(observation_id="o1", label_text="Concor 5 mg", readability="readable",
                           strength=Strength(ingredients=[IngredientAmount(inn="bisoprolol", amount=5, unit="mg")],
                                             per="tablet", release="immediate"), visual_evidence=["r1"])
    invented = parse_one(intake_amount=amount("10"))
    assert reconcile_pair(invented, pack, CAT).type is D.INSUFFICIENT_INFORMATION
    said = parse_one(intake_amount=amount("5"))
    assert reconcile_pair(said, pack, CAT).type is D.MATCH


def test_regimen_numbers_are_not_checked():
    found = parse_one(regimen={"units_per_intake": "1", "intakes_per_day": "3", "as_needed": None})
    assert found.regimen.intakes_per_day == Decimal("3") and found.regimen.units_per_intake == Decimal("1")


@pytest.mark.parametrize("fixture,voice", [
    ("spark_claims_en_live_2026-10-27.json", "evidence/live/2026-10-27/voice_en.json"),
    ("spark_claims_ar_live_run2.json", "evidence/live/2026-10-27/voice_ar.json"),
])
def test_the_live_notes_of_27_october_keep_their_amounts(fixture, voice):
    """'Concor five milligrams' and 'كونكور خمسة ملي جرام' are words; 50 is digits in English and a word in Arabic."""
    turns = [AudioTurn.model_validate(t) for t in json.loads((ROOT / voice).read_text())["turns"]]
    claims = json.loads((ROOT / "tests/fixtures" / fixture).read_text())["claims"]
    raw = []
    for c in claims:
        intake = c["intake_amount"]
        raw.append({"name_text": c["name_text"], "inn": c["inn"], "strength": c["strength"],
                    "intake_amount": {k: intake[k] for k in ("inn", "amount", "unit")} if intake else None,
                    "regimen": c["regimen"], "status": c["status"], "turn_ids": c["audio_evidence"]})
    found = parse_claims_json(json.dumps({"claims": raw}), turns)
    assert [c.intake_amount.amount if c.intake_amount else None for c in found] == \
        [Decimal("5"), Decimal("50"), None]


# --- labels: an amount must be printed on the label ------------------------------------------------------

def label(label_text="Concor 5 mg\nBisoprolol fumarate", amounts=("5",), readability="readable"):
    return json.dumps({"label_text": label_text, "inn": "bisoprolol", "country": None, "readability": readability,
                       "strength": strength(*(amount(a) for a in amounts), release="immediate")})


def test_a_printed_amount_is_kept():
    assert parse_label_json(label(), "r1").strength.ingredients[0].amount == Decimal("5")


def test_an_amount_not_on_the_label_drops_the_strength_but_keeps_the_reading():
    found = parse_label_json(label(amounts=("10",)), "r1")
    assert found.strength is None and found.label_text.startswith("Concor") and found.readability.value == "readable"


def test_no_label_text_means_no_strength():
    found = parse_label_json(label(label_text=None, readability="partial"), "r1")
    assert found.strength is None


def test_every_label_ingredient_must_be_printed():
    reply = json.dumps({"label_text": "Augmentin 875 mg", "inn": None, "country": None, "readability": "readable",
                        "strength": strength(amount("875", "amoxicillin"), amount("125", "clavulanic acid"))})
    assert parse_label_json(reply, "r1").strength is None


def test_a_spanish_decimal_comma_on_a_label_is_printed():
    assert parse_label_json(label("Concor 2,5 mg", ("2.5",)), "r1").strength.ingredients[0].amount == Decimal("2.5")


# --- prompts: amounts as said or printed, never converted ------------------------------------------------

# Batch 21 rewrote both sentences after the 28 Oct live runs: "with the number the patient said" made Spark copy
# number words ("five"), which never parse. The rule that matters here, never convert units, stays pinned.
def test_the_claim_prompt_says_never_convert_units():
    assert "never convert units" in CLAIM_PROMPT


def test_the_label_prompt_says_never_convert_units():
    assert "never convert units" in LABEL_PROMPT


# --- round 2 (supervisor 20) -----------------------------------------------------------------------------

@pytest.mark.parametrize("text,stated,unstated", [
    ("Concor five, two tablets", ("5", "2"), ("7",)),
    ("five. Two of them", ("5", "2"), ("7",)),
    ("five; two", ("5", "2"), ("7",)),
    ("five\ntwo", ("5", "2"), ("7",)),
    ("كونكور خمسة، اتنين حباية", ("5", "2"), ("7",)),
    ("twenty-five milligrams", ("25",), ()),
    ("two and a half.", ("2.5",), ()),
])
def test_a_run_of_number_words_ends_at_punctuation(text, stated, unstated):
    found = stated_amounts(text)
    assert n(*stated) <= found and not (n(*unstated) & found) if unstated else n(*stated) <= found


@pytest.mark.parametrize("text", ["zero point zero", "zero point zero zero"])
def test_a_point_decimal_that_is_zero_states_nothing(text):
    assert stated_amounts(text) == frozenset()


@pytest.mark.parametrize("label_text", [5, ["Concor 5 mg"], {"text": "Concor 5 mg"}, True])
def test_a_label_text_that_is_not_a_string_is_a_malformed_reply(label_text):
    reply = json.dumps({"label_text": label_text, "inn": "bisoprolol", "country": None, "readability": "readable",
                        "strength": strength(amount("5"), release="immediate")})
    with pytest.raises(ProviderError) as caught:
        parse_label_json(reply, "r1")
    assert caught.value.retryable
