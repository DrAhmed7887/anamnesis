"""Batch 24: grounded ingredient fields and the empty strength (SPEC §2, "Ingredient fields are grounded" and
"An empty strength is no strength"), from the 29 Oct fine-tune evaluation (evidence/finetune/results.md)."""

import json
from decimal import Decimal

from anamnesis.core.catalogue import normalise
from anamnesis.providers.claims import parse_claims_json
from anamnesis.schema import AudioTurn


def turn(text, tid="turn-0"):
    return AudioTurn(turn_id=tid, start_ms=0, end_ms=1000, transcript=text, speaker=None, lang_hint="en")


def parse(said, **fields):
    claim = {"name_text": "Farxiga", "inn": None, "strength": None, "intake_amount": None, "regimen": None,
             "status": "active", "turn_ids": ["turn-0"], **fields}
    return parse_claims_json(json.dumps({"claims": [claim]}, ensure_ascii=False), [turn(said)])[0]


def amount(label, value, unit="mg"):
    return {"inn": label, "amount": value, "unit": unit}


FARXIGA = "I'm also on Farxiga. Five milligrams three times a day."


def test_the_schema_name_as_a_label_takes_the_claims_name():  # test_iid #79, Spark, 29 Oct
    claim = parse(FARXIGA, intake_amount=amount("string", "5"))
    assert claim.intake_amount is not None and claim.intake_amount.amount == Decimal(5)
    assert normalise(claim.intake_amount.inn) == "farxiga"


def test_an_empty_label_no_longer_drops_the_intake():
    claim = parse(FARXIGA, intake_amount=amount("", "5"))
    assert claim.intake_amount is not None and normalise(claim.intake_amount.inn) == "farxiga"


def test_a_label_made_of_units_or_numbers_is_never_grounded():
    for label in ("mg", "5 mg", "50", "cinco"):
        claim = parse("Farxiga cinco mg", intake_amount=amount(label, "5"))
        assert normalise(claim.intake_amount.inn) == "farxiga", label


def test_an_unsaid_inn_becomes_null():
    claim = parse("I take Concor every morning", name_text="Concor", inn="bisoprolol")
    assert claim.inn is None


def test_a_said_inn_is_kept_and_labels_an_amount():
    claim = parse("Concor, that's bisoprolol, five milligrams", name_text="Concor", inn="bisoprolol",
                  intake_amount=amount("", "5"))
    assert normalise(claim.inn) == "bisoprolol"
    assert normalise(claim.intake_amount.inn) == "bisoprolol"


def test_a_spanish_ingredient_name_grounds_the_english_inn():
    claim = parse("tomo metformina 850 mg", name_text="metformina", inn="metformin",
                  intake_amount=amount("metformin", "850"))
    assert normalise(claim.inn) == "metformin"
    assert normalise(claim.intake_amount.inn) == "metformin"


def test_an_arabic_inn_with_an_attached_clitic_is_kept():
    claim = parse("باخد الباراسيتامول خمسميه", name_text="الباراسيتامول", inn="باراسيتامول",
                  intake_amount=amount("باراسيتامول", "500"))
    assert claim.inn is not None and claim.intake_amount is not None
    assert claim.intake_amount.amount == Decimal(500)


def test_a_strength_label_is_grounded_too():
    strength = {"ingredients": [amount("unknown", "5")], "per": "tablet", "release": "unknown"}
    claim = parse("Concor 5 mg tablets", name_text="Concor", strength=strength)
    assert claim.strength is not None and normalise(claim.strength.ingredients[0].inn) == "concor"


# --- the empty strength --------------------------------------------------------------------------------------

NAPROSYN = "Naprosyn خمسمية وخمسين ملي جرام، باخد منه حبايتين كل مرة"  # test_shift #34, Spark's reply


def test_an_empty_strength_keeps_the_stated_intake():
    strength = {"ingredients": [], "per": "tablet", "release": "unknown"}
    claim = parse(NAPROSYN, name_text="Naprosyn", strength=strength, intake_amount=amount("Naprosyn", "550"),
                  regimen={"units_per_intake": "2", "intakes_per_day": None, "as_needed": None})
    assert claim.strength is None
    assert claim.intake_amount is not None and claim.intake_amount.amount == Decimal(550)


def test_an_empty_strength_drops_its_release_but_not_the_intake():
    strength = {"ingredients": [], "per": "tablet", "release": "modified"}
    claim = parse("Beloc-Zok 50 mg every morning", name_text="Beloc-Zok", strength=strength,
                  intake_amount=amount("Beloc-Zok", "50"))
    assert claim.strength is None and claim.intake_amount.amount == Decimal(50)


def test_an_unstated_amount_still_takes_the_other_with_it():
    strength = {"ingredients": [amount("Concor", "10")], "per": "tablet", "release": "unknown"}
    claim = parse("Concor 5 mg", name_text="Concor", strength=strength, intake_amount=amount("Concor", "5"))
    assert claim.strength is None and claim.intake_amount is None
