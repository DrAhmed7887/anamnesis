"""Batch 27 extra unit checks: relation rules on invented transcripts."""

import json
from decimal import Decimal

from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.relations import (
    is_amount_grounded,
    mentions_in_turn,
    tokenize_turn,
)
from anamnesis.schema import AudioTurn


def _turns(*texts):
    return [
        AudioTurn(turn_id=f"turn-{i}", start_ms=4000 * i, end_ms=4000 * i + 3500, transcript=text)
        for i, text in enumerate(texts)
    ]


def _claim(name, amount=None, unit="mg", status="active", turn_ids=("turn-0",)):
    intake = None if amount is None else {"inn": name, "amount": str(amount), "unit": unit}
    return {
        "name_text": name, "inn": None, "strength": None, "intake_amount": intake,
        "regimen": {"units_per_intake": None, "intakes_per_day": None, "as_needed": None},
        "status": status, "turn_ids": list(turn_ids),
    }


def _intake(texts, *claims, index=0):
    texts = texts if isinstance(texts, tuple) else (texts,)
    kept = parse_claims_json(json.dumps({"claims": list(claims)}), _turns(*texts))[index].intake_amount
    return None if kept is None else kept.amount


def test_tokenizer_keeps_decimals_and_splits_clauses():
    tokens = tokenize_turn("I take 2.5 mg but now I take 5 mg.")
    texts = [(token.text, token.is_digit) for token in tokens]
    assert ("2.5", True) in texts
    first = next(token for token in tokens if token.text == "2.5")
    last = next(token for token in tokens if token.text == "5")
    assert first.clause != last.clause


def test_bare_number_grounds_any_unit():
    assert _intake("I take Concor five.", _claim("Concor", 5)) == Decimal(5)
    assert _intake("I take Concor five.", _claim("Concor", 5, "mcg")) == Decimal(5)


def test_german_keine_negates_while_later_clause_keeps_five():
    said = "Ich nehme Concor, keine zehn Milligramm, ich nehme aber fünf Milligramm."
    assert _intake(said, _claim("Concor", 10)) is None
    assert _intake(said, _claim("Concor", 5)) == Decimal(5)


def test_german_daily_total_split_is_not_one_intake():
    said = "Ich nehme Concor, zehn Milligramm täglich, fünf Milligramm morgens."
    assert _intake(said, _claim("Concor", 10)) is None
    assert _intake(said, _claim("Concor", 5)) == Decimal(5)


def test_count_word_before_the_number_is_a_count():
    assert _intake("She takes Concor capsules three daily.", _claim("Concor", 3)) is None


def test_of_phrase_with_other_medicine_drops_for_this_claim():
    said = "I take twenty milligrams of Lipitor and Concor five milligrams."
    assert _intake(said, _claim("Concor", 20)) is None
    assert _intake(said, _claim("Concor", 5)) == Decimal(5)
    assert _intake(said, _claim("Lipitor", 20)) == Decimal(20)


def test_third_split_daily_total_is_not_one_intake():
    said = "I take Concor, fifteen milligrams a day, five each time, three times."
    assert _intake(said, _claim("Concor", 15)) is None
    assert _intake(said, _claim("Concor", 5)) == Decimal(5)


def test_unresolved_claim_still_matches_the_unit():
    said = "I take Zyloric ein Gramm daily."
    assert _intake(said, _claim("Zyloric", 1, "g")) == Decimal(1)
    assert _intake(said, _claim("Zyloric", 1)) is None


def test_past_marker_does_not_reach_past_another_medicine():
    said = "I used to take Protonix twenty milligrams also taking Concor five milligrams."
    both = [_claim("Protonix", 20), _claim("Concor", 5)]
    assert _intake(said, *both, index=0) is None
    assert _intake(said, *both, index=1) == Decimal(5)


def test_splitter_in_another_medicines_clause_does_not_split():
    said = "I take metoprolol the pill has twenty-five milligrams and Concor forty milligrams a day."
    both = [_claim("metoprolol", 25), _claim("Concor", 40)]
    assert _intake(said, *both, index=1) == Decimal(40)


def test_past_blocker_survives_a_brand_slip_suffix():
    said = "I used to take Protonixix twenty milligrams also taking Concor five milligrams."
    both = [_claim("Protonix", 20), _claim("Concor", 5)]
    assert _intake(said, *both, index=1) == Decimal(5)


def test_twenty_a_day_without_a_unit_is_a_split_daily_total():
    said = "He takes Concor twenty a day, ten in the morning and ten at night."
    assert _intake(said, _claim("Concor", 20)) is None
    assert _intake(said, _claim("Concor", 10)) == Decimal(10)


def test_mili_alone_counts_as_the_unit_word():
    assert _intake("بياخد حباية كونكور عشرة ملي", _claim("كونكور", 10)) == Decimal(10)
    split = "بياخد كونكور عشرين ملي في اليوم، عشرة الصبح وعشرة بالليل"
    assert _intake(split, _claim("كونكور", 20)) is None
    assert _intake(split, _claim("كونكور", 10)) == Decimal(10)
    of_other = "بياخد كونكور وميتين ملي من البنادول"
    both = [_claim("كونكور", 200), _claim("بنادول", 200)]
    assert _intake(of_other, *both, index=0) is None
    assert _intake(of_other, *both, index=1) == Decimal(200)


def test_arabic_thousands_mark_states_no_stray_digit():
    assert _intake("بياخد كونكور مش اتنين، ٢٬٠٠٠", _claim("كونكور", 2)) is None


def test_extra_does_not_pass_for_panadol_extra():
    said = "With Concor I used to take extra ten milligrams but now I take five milligrams"
    assert _intake(said, _claim("Concor", 10)) is None
    assert _intake(said, _claim("Concor", 5)) == Decimal(5)


def test_negated_knowing_keeps_the_amount():
    assert _intake("With Concor I don't remember five milligrams", _claim("Concor", 5)) == Decimal(5)
    assert _intake("Ich nehme Concor, nicht sicher fünf Milligramm.", _claim("Concor", 5)) == Decimal(5)


def test_of_naming_the_claim_beats_the_walk_back():
    said = "I take Lipitor. Ten milligrams of Concor."
    assert _intake(said, _claim("Concor", 10)) == Decimal(10)
    assert _intake(said, _claim("Lipitor", 10)) is None


def test_mentions_carry_units_and_grounding_matches_them():
    mentions = mentions_in_turn("I take five micrograms.", ["Concor"], ["Panadol"])
    assert [(m.value, m.unit) for m in mentions] == [(Decimal(5), "mcg")]
    assert is_amount_grounded(Decimal(5), "mcg", mentions, True)
    assert not is_amount_grounded(Decimal(5), "mg", mentions, True)
