"""Batch 23.1 extra unit checks: the round 9 follow-ups."""

import json
from decimal import Decimal

import pytest

from anamnesis.providers.spark import parse_label_json
from anamnesis.providers.spend import SessionGuard, SpendGuard


def _label(text, amount="250", unit="mg", per="ml"):
    return json.dumps({"label_text": text, "inn": "paracetamol", "country": None,
                       "readability": "readable",
                       "strength": {"ingredients": [{"inn": "paracetamol", "amount": amount,
                                                    "unit": unit}],
                                    "per": per, "release": "unknown"}})


@pytest.mark.parametrize(("text", "amount", "unit", "per"), [
    # 1: after /, per, por, par or لكل a tablet word excuses nothing.
    ("Syrup 250 mg tablet par 5 ml", "250", "mg", "tablet"),
    ("Suspension 250 mg caps ∕ 5 ml", "250", "mg", "capsule"),
    ("Jarabe 250 mg cápsula por 5 ml", "250", "mg", "capsule"),
    ("شراب 250 مجم قرص لكل 5 مل", "250", "mg", "tablet"),
])
def test_tablet_word_before_a_per_connector_drops(text, amount, unit, per):
    reading = parse_label_json(_label(text, amount=amount, unit=unit, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize(("text", "amount", "unit", "per"), [
    # 1: with in or في the dissolving line keeps the tablet strength.
    ("Stir one 500 mg tablet in 30 ml juice", "500", "mg", "tablet"),
    ("500 مجم قرص يذوب في 30 مل عصير", "500", "mg", "tablet"),
])
def test_tablet_word_with_in_keeps_the_dissolving_line(text, amount, unit, per):
    reading = parse_label_json(_label(text, amount=amount, unit=unit, per=per), "r1")
    assert reading.strength is not None


@pytest.mark.parametrize(("text", "amount", "per"), [
    # 2: any number of bracket groups before the connector still counts outright.
    ("Syrup 125 mg (as trihydrate) (sugar free) (cherry flavour) per 5 ml. Take 200 mg per dose",
     "200", "dose"),
    ("Syrup 125 mg [as base] (anhydrous) [sugar free] per 5 ml. 400 mg tablets",
     "400", "tablet"),
])
def test_many_bracket_groups_before_the_connector_drop(text, amount, per):
    reading = parse_label_json(_label(text, amount=amount, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text", [
    # 3: the per-1-ml print accepts the plural volume words.
    "Drops 100 mg per 1 milliliters, 15 ml bottle",
    "Syrup 100 mg per 1 millilitres, 5 ml bottle",
    "Jarabe 100 mg por 1 mililitros, frasco 15 ml",
])
def test_plural_per_1ml_print_beside_a_pack_volume_keeps(text):
    reading = parse_label_json(_label(text, amount="100", per="ml"), "r1")
    assert reading.strength is not None


@pytest.mark.parametrize(("text", "per"), [
    # 4: the colloquial dual in the nominative counts as a spoon.
    ("شراب 250 مجم لكل معلقتان", "ml"),
    ("الجرعة 250 مجم لكل المعلقتان", "dose"),
])
def test_colloquial_dual_nominative_counts(text, per):
    reading = parse_label_json(_label(text, amount="250", per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("model_id", [
    "muse-spark-1.3-contributor",
    "  x-CONTRIBUTOR  ",
    "m-x-CONTRIBUTOR-y",
])
def test_charge_estimate_refuses_a_contributor_model(tmp_path, model_id):
    ledger = tmp_path / "ledger.jsonl"
    guard = SpendGuard(ledger, Decimal("5"))
    session = SessionGuard(guard, Decimal("1"), 10)
    with pytest.raises(ValueError):
        guard.charge_estimate(model_id, Decimal("0.01"), "estimate")
    with pytest.raises(ValueError):
        session.charge_estimate(model_id, Decimal("0.01"), "estimate")
    assert not ledger.exists() or ledger.read_text(encoding="utf-8") == ""
    assert (session.total_usd, guard.total_usd) == (Decimal(0), Decimal(0))


def test_charge_estimate_still_charges_a_plain_model(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    guard = SpendGuard(ledger, Decimal("5"))
    call_id = SessionGuard(guard, Decimal("1"), 10).charge_estimate(
        "muse-spark-1.3", Decimal("0.01"), "estimate")
    assert call_id.startswith("estimated-") and guard.total_usd == Decimal("0.01")
