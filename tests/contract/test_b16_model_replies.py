"""Batch 16 contract: every string a model writes is checked at the parser (SPEC §2, "Model replies").

Written by the CEO (Claude Code); the builder (Muse Code) must not edit it. Findings: code grill C5 (numbers, nullable
optional fields) and C3 (name grounding, ISO country, advice in model strings), evidence/grills/pre-b16/effect.md.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_pair
from anamnesis.providers.base import ProviderError
from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.spark import parse_label_json
from anamnesis.schema import AudioTurn, IngredientAmount, PackObservation, PatientClaim, Strength
from anamnesis.schema import DiscrepancyType as D

ROOT = Path(__file__).resolve().parents[2]
TURNS = [
    AudioTurn(turn_id="turn-0", start_ms=0, end_ms=4000, transcript="I take Concor 2,5 mg once a day."),
    AudioTurn(turn_id="turn-1", start_ms=4000, end_ms=9000,
              transcript="Panadol one or two times a day. I stopped BelocZok."),
]


def amount(value, inn="bisoprolol", unit="mg"):
    return {"inn": inn, "amount": value, "unit": unit}


def regimen(units=None, per_day=None):
    return {"units_per_intake": units, "intakes_per_day": per_day, "as_needed": None}


def claim(name="Concor", turn_ids=("turn-0",), **fields):
    return {"name_text": name, "inn": None, "strength": None, "intake_amount": None, "regimen": None,
            "status": "active", "turn_ids": list(turn_ids)} | fields


def claims_reply(*claims):
    return json.dumps({"claims": list(claims)})


def label_reply(**fields):
    base = {"label_text": "Concor 2,5 mg", "inn": "bisoprolol", "country": None, "readability": "readable",
            "strength": {"ingredients": [amount("2,5")], "per": "tablet", "release": "immediate"}}
    return json.dumps(base | fields)


# --- numbers: decimal commas parse; anything else that isn't one positive number becomes null --------------------

@pytest.mark.parametrize("text,expected", [
    ("2.5", Decimal("2.5")), ("2,5", Decimal("2.5")), ("0,25", Decimal("0.25")), ("850", Decimal("850")),
    ("1,000", None), ("1-2", None), ("two", None), ("0", None), ("-5", None), ("", None),
])
def test_an_intake_amount_parses_or_becomes_null(text, expected):
    [found] = parse_claims_json(claims_reply(claim(intake_amount=amount(text))), TURNS)
    assert (found.intake_amount.amount if found.intake_amount else None) == expected


@pytest.mark.parametrize("text,expected", [("1", Decimal("1")), ("0,5", Decimal("0.5")), ("1-2", None),
                                           ("twice", None)])
def test_regimen_numbers_become_null_one_field_at_a_time(text, expected):
    [found] = parse_claims_json(claims_reply(claim(regimen=regimen(units=text, per_day="2"))), TURNS)
    assert found.regimen.units_per_intake == expected and found.regimen.intakes_per_day == Decimal("2")


def test_one_unparseable_field_never_loses_the_other_claims():
    found = parse_claims_json(claims_reply(
        claim(intake_amount=amount("2,5"), regimen=regimen(per_day="1")),
        claim("Panadol", ("turn-1",), regimen=regimen(units="1", per_day="1-2")),
        claim("BelocZok", ("turn-1",), status="discontinued"),
    ), TURNS)
    assert [c.name_text for c in found] == ["Concor", "Panadol", "BelocZok"]
    assert found[0].intake_amount.amount == Decimal("2.5") and found[1].regimen.intakes_per_day is None


@pytest.mark.parametrize("text,expected", [("1.000", None), ("2.500", None), ("10.000", None),
                                           ("0.125", Decimal("0.125")), ("12.5", Decimal("12.5"))])
def test_a_dot_before_exactly_three_digits_is_ambiguous_unless_the_whole_part_is_zero(text, expected):
    [found] = parse_claims_json(claims_reply(claim(intake_amount=amount(text))), TURNS)
    assert (found.intake_amount.amount if found.intake_amount else None) == expected


PANADOL_PACK = PackObservation(observation_id="o1", label_text="Panadol 500 mg", readability="readable",
                               strength=Strength(ingredients=[IngredientAmount(inn="paracetamol", amount=500,
                                                                               unit="mg")], per="tablet",
                                                 release="immediate"), visual_evidence=["r1"])
CONCOR_PACK = PackObservation(observation_id="o1", label_text="Concor 5 mg", readability="readable",
                              strength=Strength(ingredients=[IngredientAmount(inn="bisoprolol", amount=5, unit="mg")],
                                                per="tablet", release="immediate"), visual_evidence=["r1"])


@pytest.mark.parametrize("raw,pack", [
    # supervisor 16 #1: a combination whose caffeine amount doesn't parse must not match plain Panadol
    (claim("Panadol", ("turn-1",), intake_amount=amount("500", inn="paracetamol"),
           strength={"ingredients": [amount("500", inn="paracetamol"), amount("65 mg", inn="caffeine")],
                     "per": "tablet", "release": "unknown"}), PANADOL_PACK),
    # an intake range must not leave the strength alone to match the pack
    (claim(intake_amount=amount("5-10"), strength={"ingredients": [amount("5")], "per": "tablet",
                                                   "release": "unknown"}), CONCOR_PACK),
])
def test_a_dropped_claim_amount_takes_the_other_with_it_so_nothing_false_matches(raw, pack):
    [found] = parse_claims_json(claims_reply(raw), TURNS)
    assert found.strength is None and found.intake_amount is None
    finding = reconcile_pair(found, pack, load_catalogue())
    assert finding.type is not D.MATCH and finding.needs_clinician_review


def test_a_decimal_comma_on_a_label_parses():
    assert parse_label_json(label_reply(), "r1").strength.ingredients[0].amount == Decimal("2.5")


@pytest.mark.parametrize("ingredients", [
    [amount("1-2")],
    [amount("5"), amount("n/a", inn="caffeine")],
    [amount("95", inn="metoprolol succinate"), amount("100", inn="metoprolol tartrate")],  # an equivalence line
])
def test_a_label_strength_that_cannot_be_kept_becomes_null_not_a_failure(ingredients):
    strength = {"ingredients": ingredients, "per": "tablet", "release": "modified"}
    reading = parse_label_json(label_reply(strength=strength), "r1")
    assert reading.strength is None and reading.label_text == "Concor 2,5 mg"
    assert reading.readability.value == "readable"


def test_a_claim_strength_that_cannot_be_kept_becomes_null():
    strength = {"ingredients": [amount("five")], "per": "tablet", "release": "unknown"}
    [found] = parse_claims_json(claims_reply(claim(strength=strength)), TURNS)
    assert found.strength is None


# --- the label's country: an ISO 3166-1 alpha-2 code or nothing ---------------------------------------------------

@pytest.mark.parametrize("country,expected", [
    ("es", "ES"), ("DE", "DE"), ("Spain", None), ("Spain - ask your pharmacist to double the dose", None),
    ("E", None), ("", None), (None, None),
])
def test_a_label_country_is_kept_only_as_an_iso_code(country, expected):
    assert parse_label_json(label_reply(country=country), "r1").country == expected


# --- name_text must be something the patient said, in a turn the claim cites -------------------------------------

@pytest.mark.parametrize("bad", [claim("Concor - you should keep taking this every morning"),
                                 claim("Concor", ("turn-1",))])
def test_name_text_must_occur_in_a_turn_the_claim_cites(bad):
    with pytest.raises(ProviderError) as error:
        parse_claims_json(claims_reply(bad), TURNS)
    assert error.value.retryable


def test_grounding_accepts_the_spellings_voice_writes():
    turns = [AudioTurn(turn_id="t0", start_ms=0, end_ms=3000, transcript="وقفت الPanadol وباخد BelocZok و كونكور")]
    names = ("Panadol", "BelocZok", "كونكور", "panadol")
    assert len(parse_claims_json(claims_reply(*(claim(name, ("t0",)) for name in names)), turns)) == 4


# --- no advice in any string a model wrote, except quoted label text ----------------------------------------------

@pytest.mark.parametrize("fields", [
    {"inn": "bisoprolol, keep taking it"},
    {"intake_amount": amount("5", inn="bisoprolol - double the dose")},
    {"strength": {"ingredients": [amount("5", inn="bisoprolol; take two")], "per": "tablet", "release": "unknown"}},
])
def test_advice_in_a_claim_string_is_rejected(fields):
    with pytest.raises(ProviderError) as error:
        parse_claims_json(claims_reply(claim(**fields)), TURNS)
    assert error.value.retryable


def test_advice_in_name_text_is_rejected_even_when_it_was_spoken():
    turns = [AudioTurn(turn_id="t0", start_ms=0, end_ms=3000, transcript="My doctor said keep taking Concor.")]
    with pytest.raises(ProviderError):
        parse_claims_json(claims_reply(claim("keep taking Concor", ("t0",))), turns)


PLAIN = {"ingredients": [amount("5")], "per": "tablet", "release": "immediate"}  # parses today: tests advice only


@pytest.mark.parametrize("fields", [
    {"inn": "bisoprolol, take one daily", "strength": PLAIN},
    {"strength": {**PLAIN, "ingredients": [amount("5", inn="bisoprolol: double if needed")]}},
])
def test_advice_in_a_label_ingredient_is_rejected(fields):
    with pytest.raises(ProviderError) as error:
        parse_label_json(label_reply(**fields), "r1")
    assert error.value.retryable


def test_label_text_is_quoted_as_printed_even_with_directions():
    reading = parse_label_json(label_reply(label_text="Concor 2,5 mg. Take one tablet daily."), "r1")
    assert reading.label_text == "Concor 2,5 mg. Take one tablet daily."


# --- the live replies recorded on 27 Oct still parse to exactly the same claims ----------------------------------

def _raw_amount(part):
    if part is None:
        return None
    inn = part["inn"] + (f" {part['salt']}" if part.get("salt") else "")
    return {"inn": inn, "amount": part["amount"], "unit": part["unit"]}


def _raw_claim(parsed):
    strength = parsed["strength"]
    if strength is not None:
        strength = {**strength, "ingredients": [_raw_amount(part) for part in strength["ingredients"]]}
    return {"name_text": parsed["name_text"], "inn": parsed["inn"], "strength": strength,
            "intake_amount": _raw_amount(parsed["intake_amount"]), "regimen": parsed["regimen"],
            "status": parsed["status"], "turn_ids": parsed["audio_evidence"]}


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_the_recorded_live_replies_still_parse_to_the_same_claims(lang):
    report = json.loads((ROOT / f"evidence/live/2026-10-27/report_{lang}.json").read_text(encoding="utf-8"))
    turns = [AudioTurn.model_validate(turn) for turn in report["turns"]]
    parsed = parse_claims_json(json.dumps({"claims": [_raw_claim(c) for c in report["claims"]]}), turns)
    expected = [PatientClaim.model_validate(c).model_dump(mode="json") for c in report["claims"]]
    assert [c.model_dump(mode="json") for c in parsed] == expected
