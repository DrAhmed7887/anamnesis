"""Numbers a source text states, digits or number words (SPEC §2, batch 20)."""

import re
from decimal import Decimal

from anamnesis.core import catalogue
from anamnesis.providers.numbers import parse_amount_text

ENGLISH_NUMBERS: dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

ENGLISH_HUNDRED = frozenset({"hundred"})
ENGLISH_THOUSAND = frozenset({"thousand"})
ENGLISH_HALF = frozenset({"half"})

ARABIC_NUMBERS: dict[str, int] = {
    "واحد": 1, "واحده": 1, "احد": 1,
    "اتنين": 2, "اثنين": 2, "اثنان": 2, "اتنان": 2, "اثنا": 2, "اثني": 2,
    "تلاته": 3, "ثلاثه": 3, "تلات": 3, "ثلاث": 3,
    "اربعه": 4, "اربع": 4,
    "خمسه": 5, "خمس": 5,
    "سته": 6, "ست": 6,
    "سبعه": 7, "سبع": 7,
    "تمانيه": 8, "ثمانيه": 8, "تماني": 8, "ثماني": 8, "تمن": 8, "ثمان": 8,
    "تسعه": 9, "تسع": 9,
    "عشره": 10, "عشر": 10,
    "حداشر": 11, "اتناشر": 12, "تلتاشر": 13, "اربعتاشر": 14, "خمستاشر": 15,
    "ستاشر": 16, "سبعتاشر": 17, "تمنتاشر": 18, "تسعتاشر": 19,
    "عشرين": 20, "عشرون": 20,
    "تلاتين": 30, "ثلاثين": 30, "ثلاثون": 30,
    "اربعين": 40, "اربعون": 40,
    "خمسين": 50, "خمسون": 50,
    "ستين": 60, "ستون": 60,
    "سبعين": 70, "سبعون": 70,
    "تمانين": 80, "ثمانين": 80, "ثمانون": 80,
    "تسعين": 90, "تسعون": 90,
    "ميتين": 200, "مايتين": 200, "مئتين": 200, "مئتان": 200,
    "مائتين": 200, "مائتان": 200,
    "الفين": 2000,
}

ARABIC_HUNDRED = frozenset({"ميه", "مايه", "مائه", "مئه", "ميت"})
ARABIC_THOUSAND = frozenset({"الف", "الاف"})
ARABIC_HALF = frozenset({"نص", "نصف"})

ARABIC_HUNDRED_SUFFIXES = ("مايه", "مائه", "ميه", "مئه")
ARABIC_HUNDRED_STEMS: dict[str, int] = {
    "تلت": 3, "ثلاث": 3, "ربع": 4, "اربع": 4, "خمس": 5, "ست": 6,
    "سبع": 7, "تمن": 8, "ثمان": 8, "تسع": 9,
}

_PLAIN = ENGLISH_NUMBERS | ARABIC_NUMBERS
_HUNDRED = ENGLISH_HUNDRED | ARABIC_HUNDRED
_THOUSAND = ENGLISH_THOUSAND | ARABIC_THOUSAND
_HALF = ENGLISH_HALF | ARABIC_HALF

_DIGIT_RUN = re.compile(r"(?<![0-9٠-٩.,])[0-9٠-٩]+(?:[.,][0-9٠-٩]+)?")
_RUN_BREAK = re.compile(r"[,.;:!?،؛؟\r\n]+")


def _combined_hundreds(word: str) -> int | None:
    """A 300-900 one-word form such as خمسميه (SPEC §2)."""
    for suffix in ARABIC_HUNDRED_SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix):
            stem = ARABIC_HUNDRED_STEMS.get(word[: -len(suffix)])
            if stem is not None:
                return stem * 100
    return None


def _classify(token: str) -> tuple[str, int | None]:
    """Kind and plain value of one normalised token."""
    if token in _PLAIN:
        return "plain", _PLAIN[token]
    if token in _HUNDRED:
        return "hundred", 100
    if token in _THOUSAND:
        return "thousand", 1000
    if token in _HALF:
        return "half", None
    if token in ("and", "و"):
        return "and", None
    if token == "point":
        return "point", None
    if token == "a":
        return "a", None
    combined = _combined_hundreds(token)
    if combined is not None:
        return "plain", combined
    if token.startswith("و") and len(token) > 1:
        rest = token[1:]
        if rest in _PLAIN:
            return "plain", _PLAIN[rest]
        if rest in _HUNDRED:
            return "hundred", 100
        if rest in _THOUSAND:
            return "thousand", 1000
        if rest in _HALF:
            return "half", None
        combined = _combined_hundreds(rest)
        if combined is not None:
            return "plain", combined
    return "other", None


def _run_value(words: list[tuple[str, int | None]]) -> Decimal:
    total, current = Decimal(0), Decimal(0)
    for kind, value in words:
        if kind == "plain" and value is not None:
            current += Decimal(value)
        elif kind == "hundred":
            current = (current if current != 0 else Decimal(1)) * 100
        elif kind == "thousand":
            total += (current if current != 0 else Decimal(1)) * 1000
            current = Decimal(0)
        elif kind == "half":
            current += Decimal("0.5")
    return total + current


def _word_values(words: list[tuple[str, int | None]], found: set[Decimal]) -> None:
    for kind, value in words:
        if kind == "plain" and value:
            found.add(Decimal(value))
        elif kind == "hundred":
            found.add(Decimal(100))
        elif kind == "thousand":
            found.add(Decimal(1000))
        elif kind == "half":
            found.add(Decimal("0.5"))


def _close(words: list[tuple[str, int | None]], found: set[Decimal]) -> None:
    if not words:
        return
    value = _run_value(words)
    if value > 0:
        found.add(value)
    _word_values(words, found)
    words.clear()


def _word_amounts(part: str, found: set[Decimal]) -> None:
    """Number-word runs in one punctuation-delimited part (SPEC §2)."""
    tokens = catalogue.normalise(part).split()
    kinds = [_classify(token) for token in tokens]
    words: list[tuple[str, int | None]] = []
    index = 0
    while index < len(tokens):
        kind, value = kinds[index]
        if kind in ("plain", "hundred", "thousand", "half"):
            words.append((kind, value))
        elif kind == "and":
            pass
        elif kind == "a":
            if index == 0 or kinds[index - 1][0] != "and":
                _close(words, found)
            # else: filler inside "and a half", the run stays open
        elif kind == "point":
            digits: list[int] = []
            look = index + 1
            while look < len(tokens) and ENGLISH_NUMBERS.get(tokens[look], 10) <= 9:
                digits.append(ENGLISH_NUMBERS[tokens[look]])
                look += 1
            if digits:
                base = _run_value(words)
                value = base + Decimal("0." + "".join(str(d) for d in digits))
                if value > 0:
                    found.add(value)
                _word_values(words, found)
                for digit in digits:
                    if digit:
                        found.add(Decimal(digit))
                words.clear()
                index = look - 1
            else:
                _close(words, found)
        else:
            _close(words, found)
        index += 1
    _close(words, found)


def stated_amounts(text: str) -> frozenset[Decimal]:
    """Every positive number the text states (SPEC §2, batch 20)."""
    found: set[Decimal] = set()
    for match in _DIGIT_RUN.finditer(text.replace("٫", ".")):
        amount = parse_amount_text(match.group(0))
        if amount is not None:
            found.add(amount)
    for part in _RUN_BREAK.split(text):
        _word_amounts(part, found)
    return frozenset(found)
