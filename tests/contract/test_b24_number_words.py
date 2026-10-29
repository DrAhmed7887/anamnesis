"""Batch 24: Spanish and German number words (SPEC §2, "Spanish and German (batch 24)"), with the 29 Oct plan
grill's traps (evidence/grills/plan-2026-10-29/effect.md #1, #2, #4-#6) and the CEO's reference build
(evidence/batches/24/reference.md)."""

from decimal import Decimal

import pytest

from anamnesis.providers.numbers import parse_amount_text
from anamnesis.providers.stated import stated_amounts

STATED = [
    # Spanish
    ("tomo quinientos miligramos", "500"),
    ("veinticinco miligramos", "25"),
    ("treinta y cinco miligramos", "35"),
    ("ochocientos setenta y cinco miligramos", "875"),
    ("cien miligramos", "100"),
    ("ciento veinte miligramos", "120"),
    ("mil miligramos", "1000"),
    ("dos mil miligramos", "2000"),
    ("doscientas cincuenta miligramos", "250"),
    ("dos coma cinco miligramos", "2.5"),
    ("medio comprimido", "0.5"),
    ("uno y medio comprimidos", "1.5"),
    ("dos y media pastillas", "2.5"),
    ("un gramo", "1"),
    ("veintitrés miligramos", "23"),
    ("veintitres miligramos", "23"),
    ("dieciséis miligramos", "16"),
    ("Quinientos miligramos", "500"),
    ("treinta y un miligramos", "31"),  # "un" before a unit word is 1, and "y" joins it to the ten
    # German
    ("fünfhundert Milligramm", "500"),
    ("fünfhundertfünfundsiebzig Milligramm", "575"),
    ("zweihundertfünfzig Milligramm", "250"),
    ("dreißig Milligramm", "30"),
    ("einundzwanzig Milligramm", "21"),
    ("hundert Milligramm", "100"),
    ("einhundert Milligramm", "100"),
    ("tausend Milligramm", "1000"),
    ("zweitausend Milligramm", "2000"),
    ("zwei Komma fünf Milligramm", "2.5"),
    ("eine halbe Tablette", "0.5"),
    ("zweieinhalb Tabletten", "2.5"),
    ("eineinhalb Tabletten", "1.5"),
    ("einhalb Tablette", "0.5"),  # a half: only eineinhalb is 1.5 (CEO's reference build)
    ("fünf hundert Milligramm", "100"),  # German numbers never combine (round 6)
    ("ein Gramm", "1"),
    ("zwölf Milligramm", "12"),
    ("sechzehn Milligramm", "16"),
    ("siebzehn Milligramm", "17"),
    ("sechzig Milligramm", "60"),
    ("siebzig Milligramm", "70"),
]


@pytest.mark.parametrize(("text", "value"), STATED)
def test_a_spanish_or_german_number_is_stated(text, value):
    assert Decimal(value) in stated_amounts(text)


NEVER = [
    ("tomo comprimidos de diez y cincuenta miligramos", "60"),  # "y" joins only a ten to a unit (#4)
    ("ochocientos setenta y cinco cien", "870"),  # "cien" is never a multiplier (#5)
    ("ochocientos setenta y cinco cien", "500"),
    ("zweieinhalb Tabletten", "1"),  # no 1 from the "ein" inside (#6)
    ("eineinhalb Tabletten", "1"),
    ("einhalb Tablette", "1.5"),
    ("tomo once miligramos", "11"),  # Spanish "once" is left out: it is English "once"
    ("cinco cien", "105"),  # a hundreds word closes a run that holds a number
    ("cinco cien", "500"),
    ("fünf hundert Milligramm", "500"),  # German numbers never combine (round 6)
]


@pytest.mark.parametrize(("text", "value"), NEVER)
def test_these_never_state_the_value(text, value):
    assert Decimal(value) not in stated_amounts(text)


@pytest.mark.parametrize("text", [
    "tomo Panadol una vez al día",  # an article is not 1 (#2)
    "ich nehme eine Tablette",
    "zweimal täglich",  # as "twice" states nothing
    "Bitte Achtung",  # a token that isn't wholly a number (#6)
    "eine Einheit",
    "dos veces al día",  # a Spanish or German number outside an amount (round 6)
])
def test_these_state_nothing(text):
    assert stated_amounts(text) == frozenset()


def test_the_separate_numbers_of_a_spanish_list_stay_separate():
    found = stated_amounts("tomo comprimidos de diez miligramos y cincuenta miligramos")
    assert {Decimal(10), Decimal(50)} <= found
    found = stated_amounts("ochocientos setenta y cinco miligramos, cien miligramos")
    assert {Decimal(875), Decimal(100)} <= found


@pytest.mark.parametrize(("word", "value"), [
    ("quinientos", "500"), ("veinticinco", "25"), ("fünfzig", "50"), ("dreißig", "30"),
    ("fünfhundertfünfundsiebzig", "575"), ("zweieinhalb", "2.5"),
])
def test_a_single_spanish_or_german_word_parses_like_its_digits(word, value):
    assert parse_amount_text(word) == Decimal(value)


@pytest.mark.parametrize("word", ["Achtung", "zweimal", "una", "eine"])
def test_these_words_do_not_parse_as_amounts(word):
    assert parse_amount_text(word) is None


def test_english_and_arabic_are_unchanged():
    assert stated_amounts("two point five milligrams") == {Decimal(2), Decimal("2.5"), Decimal(5)}
    assert Decimal(500) in stated_amounts("خمسمية")
    assert stated_amounts("I take it once a day") == frozenset()
