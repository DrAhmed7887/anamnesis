"""Batch 27.1 extra unit checks: durations, knowing-negation, dropped counts."""

import json
from decimal import Decimal

from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.relations import (
    DURATION_WORDS,
    count_values_for_cited_turns,
)
from anamnesis.schema import AudioTurn


def _turns(*texts):
    return [
        AudioTurn(turn_id=f"turn-{i}", start_ms=4000 * i, end_ms=4000 * i + 3500, transcript=text)
        for i, text in enumerate(texts)
    ]


def _claim(name, amount=None, unit="mg", units=None, per_day=None, status="active"):
    intake = None if amount is None else {"inn": name, "amount": str(amount), "unit": unit}
    return {
        "name_text": name, "inn": None, "strength": None, "intake_amount": intake,
        "regimen": {"units_per_intake": units, "intakes_per_day": per_day, "as_needed": None},
        "status": status, "turn_ids": ["turn-0"],
    }


def _parse(texts, *claims):
    texts = texts if isinstance(texts, tuple) else (texts,)
    return parse_claims_json(json.dumps({"claims": list(claims)}, ensure_ascii=False), _turns(*texts))


def _intake(texts, *claims, index=0):
    kept = _parse(texts, *claims)[index].intake_amount
    return None if kept is None else kept.amount


def _units(texts, *claims, index=0):
    regimen = _parse(texts, *claims)[index].regimen
    return None if regimen is None else regimen.units_per_intake


def test_duration_words_cover_the_spec_lists():
    for word in ("years", "months", "weeks", "days", "hours", "سنين", "شهور", "años", "semanas",
                 "Jahren", "Monaten", "Wochen", "Tagen", "Stunden"):
        assert word in DURATION_WORDS
    for word in ("year", "month", "week", "day", "hour", "سنه", "شهر", "اسبوع", "يوم", "ساعه",
                 "año", "mes", "semana", "día", "hora",
                 "Jahr", "Monat", "Woche", "Tag", "Stunde"):
        assert word not in DURATION_WORDS


def test_a_singular_time_word_keeps_the_amount():
    assert _intake("I take Concor 5 milligrams for one year.", _claim("Concor", 5)) == Decimal(5)
    assert _intake("Ich nehme Concor 5 Milligramm seit einem Jahr.", _claim("Concor", 5)) == Decimal(5)


def test_duration_in_months_neither_splits_nor_grounds():
    said = "I take Concor twelve milligrams a day for six months."
    assert _intake(said, _claim("Concor", 12, per_day="1")) == Decimal(12)
    assert _intake(said, _claim("Concor", 6)) is None


def test_run_ending_in_a_is_never_a_duration():
    said = "I take Concor twenty a day for ten years."
    assert _intake(said, _claim("Concor", 20, per_day="1")) == Decimal(20)
    assert _intake(said, _claim("Concor", 10)) is None


def test_arabic_duration_in_months_keeps_the_daily_amount():
    said = "باخد كونكور عشرة ملي جرام بقالي خمس شهور"
    assert _intake(said, _claim("كونكور", 10)) == Decimal(10)
    assert _intake(said, _claim("كونكور", 5)) is None


def test_german_duration_with_digits_is_never_an_amount():
    said = "Ich nehme Concor 5 Milligramm seit 2 Wochen."
    assert _intake(said, _claim("Concor", 5)) == Decimal(5)
    assert _intake(said, _claim("Concor", 2)) is None


def test_spanish_duration_with_digits_is_never_an_amount():
    said = "Tomo Concor 5 miligramos durante 2 semanas."
    assert _intake(said, _claim("Concor", 5)) == Decimal(5)
    assert _intake(said, _claim("Concor", 2)) is None


def test_only_weiss_cancels_a_negation_right_after_it():
    assert _intake("Ich nehme Concor ich weiß nicht fünf Milligramm", _claim("Concor", 5)) == Decimal(5)
    assert _intake("Ich nehme Concor sicher nicht fünf Milligramm", _claim("Concor", 5)) is None
    assert _intake("With Concor I know not five milligrams", _claim("Concor", 5)) is None


def test_negation_before_knowing_still_negates_the_knowing():
    assert _intake("With Concor I'm not sure five milligrams", _claim("Concor", 5)) == Decimal(5)


def test_plain_negation_still_drops_the_amount():
    assert _intake("Ich nehme Concor nicht zehn Milligramm", _claim("Concor", 10)) is None
    assert _intake("With Concor I know five milligrams, not ten", _claim("Concor", 10)) is None


def test_dropped_amount_keeps_a_backed_tablet_count():
    said = "I take Concor not ten milligrams, two tablets a day."
    assert _intake(said, _claim("Concor", 10, units="2")) is None
    assert _units(said, _claim("Concor", 10, units="2")) == Decimal(2)


def test_dropped_amount_drops_an_unbacked_tablet_count():
    said = "I take Concor not ten milligrams, two a day."
    assert _intake(said, _claim("Concor", 10, units="2")) is None
    assert _units(said, _claim("Concor", 10, units="2")) is None


def test_count_values_read_only_rule_3_counts():
    assert count_values_for_cited_turns(["I take two tablets a day."]) == {Decimal(2)}
    assert count_values_for_cited_turns(["I take two a day."]) == set()
    assert count_values_for_cited_turns(["I take Concor for five years."]) == set()
    assert count_values_for_cited_turns(["I take five milligrams."]) == set()


def test_count_values_skip_negated_another_and_past_counts():
    assert count_values_for_cited_turns(["I take Concor not ten milligrams, not two tablets."]) == set()
    assert count_values_for_cited_turns(
        ["I take Concor not ten milligrams, Panadol two tablets."], ["Concor"], ["Panadol"],
    ) == set()
    assert count_values_for_cited_turns(["I used to take two tablets."]) == set()
    assert count_values_for_cited_turns(
        ["I used to take two tablets."], is_discontinued=True,
    ) == {Decimal(2)}
    assert count_values_for_cited_turns(
        ["I take Concor not ten milligrams, two tablets a day."], ["Concor"], ["Panadol"],
    ) == {Decimal(2)}


def test_dropped_amount_drops_a_negated_or_another_medicines_tablet_count():
    assert _units("I take Concor not ten milligrams, not two tablets.",
                  _claim("Concor", 10, units="2")) is None
    assert _units("I take Concor not ten milligrams, Panadol two tablets.",
                  _claim("Concor", 10, units="2")) is None
