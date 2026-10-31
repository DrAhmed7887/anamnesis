"""Numbers a source text states, digits or number words (SPEC §2, batch 20)."""

import re
import unicodedata
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

SPANISH_NUMBERS: dict[str, int] = {
    "cero": 0, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciseis": 16, "dieciséis": 16, "diecisiete": 17, "dieciocho": 18,
    "diecinueve": 19, "veinte": 20,
    "veintiuno": 21, "veintiun": 21, "veintiún": 21,
    "veintidos": 22, "veintidós": 22, "veintitres": 23, "veintitrés": 23,
    "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26, "veintiséis": 26,
    "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
    "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
    "setenta": 70, "ochenta": 80, "noventa": 90,
    "cien": 100, "ciento": 100,
    "doscientos": 200, "doscientas": 200, "trescientos": 300, "trescientas": 300,
    "cuatrocientos": 400, "cuatrocientas": 400, "quinientos": 500, "quinientas": 500,
    "seiscientos": 600, "seiscientas": 600, "setecientos": 700, "setecientas": 700,
    "ochocientos": 800, "ochocientas": 800, "novecientos": 900, "novecientas": 900,
}

SPANISH_THOUSAND = frozenset({"mil"})
SPANISH_HALF = frozenset({"medio", "media"})
SPANISH_ARTICLES = frozenset({"un", "una"})
SPANISH_TENS_WORDS = frozenset({
    "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa",
})
SPANISH_HUNDREDS = frozenset({
    "cien", "ciento", "doscientos", "doscientas", "trescientos", "trescientas",
    "cuatrocientos", "cuatrocientas", "quinientos", "quinientas",
    "seiscientos", "seiscientas", "setecientos", "setecientas",
    "ochocientos", "ochocientas", "novecientos", "novecientas",
})

GERMAN_MULTIPLIERS: dict[str, int] = {
    "ein": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5,
    "sechs": 6, "sieben": 7, "acht": 8, "neun": 9,
}
GERMAN_UNITS: dict[str, int] = {
    "eins": 1, "ein": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5,
    "sechs": 6, "sieben": 7, "acht": 8, "neun": 9,
    "zehn": 10, "elf": 11, "zwölf": 12,
}
GERMAN_TEENS: dict[str, int] = {
    "dreizehn": 13, "vierzehn": 14, "fünfzehn": 15, "sechzehn": 16,
    "siebzehn": 17, "achtzehn": 18, "neunzehn": 19,
}
GERMAN_TENS: dict[str, int] = {
    "zwanzig": 20, "dreissig": 30, "vierzig": 40, "fünfzig": 50,
    "sechzig": 60, "siebzig": 70, "achtzig": 80, "neunzig": 90,
}
GERMAN_UNIT_PREFIXES: dict[str, int] = {
    "ein": 1, "eins": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5,
    "sechs": 6, "sieben": 7, "acht": 8, "neun": 9,
}
GERMAN_HUNDRED = frozenset({"hundert"})
GERMAN_THOUSAND = frozenset({"tausend"})
GERMAN_HALF = frozenset({"halb", "halbe", "halben", "halber", "halbes", "einhalb"})
GERMAN_ARTICLES = frozenset({"ein", "eine", "einen", "einem", "einer"})
GERMAN_CARE_VERBS = frozenset({"geben", "gegeben", "nehmen", "genommen", "lassen", "gelassen"})

_UNIT_RAW = [
    "mg", "g", "mcg", "µg", "μg", "ml",
    "miligramo", "miligramos", "gramo", "gramos",
    "microgramo", "microgramos", "mililitro", "mililitros",
    "milligramm", "gramm", "mikrogramm", "milliliter",
]
UNIT_WORDS = frozenset(catalogue.normalise(word) for word in _UNIT_RAW)

_SPANISH_UNIT_RAW = [
    "miligramo", "miligramos", "gramo", "gramos",
    "microgramo", "microgramos", "mililitro", "mililitros",
]
SPANISH_UNIT_WORDS = frozenset(catalogue.normalise(word) for word in _SPANISH_UNIT_RAW)

_SPANISH_DOSE_RAW = [
    "comprimido", "comprimidos", "pastilla", "pastillas",
    "cápsula", "cápsulas", "capsula", "capsulas",
    "tableta", "tabletas", "gragea", "grageas",
]
SPANISH_DOSE_WORDS = frozenset(catalogue.normalise(word) for word in _SPANISH_DOSE_RAW)

SPANISH_UNIT_OR_DOSE = SPANISH_UNIT_WORDS | SPANISH_DOSE_WORDS

_GATE_LONG_RAW = [
    "milligram", "milligrams", "gram", "grams",
    "microgram", "micrograms",
    "millilitre", "millilitres", "milliliter", "milliliters",
]
_GERMAN_DOSE_RAW = [
    "tablette", "tabletten",
    "filmtablette", "filmtabletten",
    "retardtablette", "retardtabletten",
    "kapsel", "kapseln", "retardkapsel", "retardkapseln",
    "dragee", "dragees",
]
GATE_WORDS = (
    UNIT_WORDS
    | SPANISH_DOSE_WORDS
    | frozenset(catalogue.normalise(word) for word in _GATE_LONG_RAW + _GERMAN_DOSE_RAW)
)

_PLAIN = ENGLISH_NUMBERS | ARABIC_NUMBERS
_HUNDRED = ENGLISH_HUNDRED | ARABIC_HUNDRED
_THOUSAND = ENGLISH_THOUSAND | ARABIC_THOUSAND
_HALF = ENGLISH_HALF | ARABIC_HALF

_DIGIT_RUN = re.compile(r"(?<![\d.,٬])(?>[0-9٠-٩۰-۹]+(?:[.,٬][0-9٠-٩۰-۹]+)?)(?!\d)")
_RUN_BREAK = re.compile(r"[,.;:!?،؛؟\r\n]+")


def _german_number(token: str) -> int | Decimal | None:
    """Read one whole German token as a number up to 9,999 (SPEC §2, batch 24)."""
    if token.endswith("einhalb") and len(token) > len("einhalb"):
        mult = GERMAN_MULTIPLIERS.get(token[: -len("einhalb")])
        if mult is None:
            return None
        return Decimal(mult) + Decimal("0.5")
    if token in ("hundert", "tausend"):
        return None
    rest = token
    value = 0
    for word in sorted(GERMAN_MULTIPLIERS, key=len, reverse=True):
        if rest.startswith(word + "tausend"):
            value += GERMAN_MULTIPLIERS[word] * 1000
            rest = rest[len(word + "tausend"):]
            break
    else:
        if rest.startswith("tausend"):
            value += 1000
            rest = rest[len("tausend"):]
    for word in sorted(GERMAN_MULTIPLIERS, key=len, reverse=True):
        if rest.startswith(word + "hundert"):
            value += GERMAN_MULTIPLIERS[word] * 100
            rest = rest[len(word + "hundert"):]
            break
    else:
        if rest.startswith("hundert"):
            if rest == "hundert" and value == 0:
                return None
            value += 100
            rest = rest[len("hundert"):]
    if rest == "":
        return value if value > 0 else None
    if rest in GERMAN_UNITS:
        return value + GERMAN_UNITS[rest]
    if rest in GERMAN_TEENS:
        return value + GERMAN_TEENS[rest]
    if rest in GERMAN_TENS:
        return value + GERMAN_TENS[rest]
    if "und" in rest:
        for ten_word in sorted(GERMAN_TENS, key=len, reverse=True):
            if rest.endswith(ten_word):
                prefix = rest[: -len(ten_word)]
                if prefix.endswith("und"):
                    unit = GERMAN_UNIT_PREFIXES.get(prefix[: -len("und")])
                    if unit is not None:
                        return value + unit + GERMAN_TENS[ten_word]
                break
        return None
    return None


def _article_counts(tokens: list[str], idx: int) -> bool:
    """An article counts as 1 only before a unit word, or Spanish y medio/media."""
    if tokens[idx] not in SPANISH_ARTICLES and tokens[idx] not in GERMAN_ARTICLES:
        return False
    if idx + 1 >= len(tokens):
        return False
    nxt = tokens[idx + 1]
    if nxt in UNIT_WORDS:
        return True
    return (
        tokens[idx] in SPANISH_ARTICLES
        and nxt == "y"
        and idx + 2 < len(tokens)
        and tokens[idx + 2] in ("medio", "media")
    )


def _y_keeps_open(tokens: list[str], kinds: list[tuple[str, object]], idx: int) -> bool:
    """Spanish y joins only a ten to a 1-9, or a number to medio/media."""
    if idx + 1 >= len(tokens):
        return False
    if tokens[idx + 1] in ("medio", "media"):
        if (
            idx >= 2
            and (tokens[idx - 1] in SPANISH_NUMBERS or tokens[idx - 1] in SPANISH_ARTICLES)
            and tokens[idx - 2] in ("la", "las")
        ):
            return False
        return True
    if idx == 0 or tokens[idx - 1] not in SPANISH_TENS_WORDS:
        return False
    nxt_kind, nxt_val = kinds[idx + 1]
    if (
        nxt_kind == "plain"
        and nxt_val in (1, 2, 3, 4, 5, 6, 7, 8, 9)
        and tokens[idx + 1] in SPANISH_NUMBERS
    ):
        return True
    return (
        nxt_kind == "article"
        and tokens[idx + 1] in SPANISH_ARTICLES
        and _article_counts(tokens, idx + 1)
    )


def _digit_value(token: str) -> int | None:
    """A 0-9 digit word in English, Spanish or German for point/coma/komma."""
    val = ENGLISH_NUMBERS.get(token)
    if val is not None and val <= 9:
        return val
    val = SPANISH_NUMBERS.get(token)
    if val is not None and val <= 9:
        return val
    if token not in GERMAN_ARTICLES:
        gval = _german_number(token)
        if isinstance(gval, int) and 0 <= gval <= 9:
            return gval
    return None


def _is_es_de_digit(token: str) -> bool:
    """A Spanish or German 0-9 digit word (SPEC §2, round 7)."""
    val = SPANISH_NUMBERS.get(token)
    if val is not None and val <= 9:
        return True
    if token == "null":
        return True
    if token not in GERMAN_ARTICLES:
        gval = _german_number(token)
        if isinstance(gval, int) and 0 <= gval <= 9:
            return True
    return False


def _combined_hundreds(word: str) -> int | None:
    """A 300-900 one-word form such as خمسميه (SPEC §2)."""
    for suffix in ARABIC_HUNDRED_SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix):
            stem = ARABIC_HUNDRED_STEMS.get(word[: -len(suffix)])
            if stem is not None:
                return stem * 100
    return None


def _classify(token: str) -> tuple[str, int | Decimal | None]:
    """Kind and plain value of one normalised token."""
    if token in _PLAIN:
        return "plain", _PLAIN[token]
    if token in SPANISH_NUMBERS:
        return "plain", SPANISH_NUMBERS[token]
    if token in _HUNDRED:
        return "hundred", 100
    if token in GERMAN_HUNDRED:
        return "plain", 100
    if token in _THOUSAND:
        return "thousand", 1000
    if token in SPANISH_THOUSAND:
        return "thousand", 1000
    if token in GERMAN_THOUSAND:
        return "plain", 1000
    if token in _HALF:
        return "half", None
    if token in SPANISH_HALF:
        return "half", None
    if token in GERMAN_HALF:
        return "half", None
    if token in ("and", "و"):
        return "and", None
    if token in ("point", "coma", "komma"):
        return "point", None
    if token == "a":
        return "a", None
    if token == "y":
        return "y", None
    if token in SPANISH_ARTICLES or token in GERMAN_ARTICLES:
        return "article", None
    combined = _combined_hundreds(token)
    if combined is not None:
        return "plain", combined
    german = _german_number(token)
    if german is not None:
        return "plain", german
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


def has_number_role(word: str) -> bool:
    """True when the number reader gives the word any role, or it is German null."""
    if not isinstance(word, str):
        return False
    token = catalogue.normalise(word)
    if token == "null":
        return True
    return _classify(token)[0] != "other"


def _run_value(words: list[tuple[str, int | Decimal | None]]) -> Decimal:
    total, current = Decimal(0), Decimal(0)
    for kind, value in words:
        if kind == "plain" and value is not None:
            if value >= 1000:
                total += Decimal(value)
                current = Decimal(0)
            else:
                current += Decimal(value)
        elif kind == "hundred":
            current = (current if current != 0 else Decimal(1)) * 100
        elif kind == "thousand":
            total += (current if current != 0 else Decimal(1)) * 1000
            current = Decimal(0)
        elif kind == "half":
            current += Decimal("0.5")
    return total + current


def _word_values(words: list[tuple[str, int | Decimal | None]], found: set[Decimal]) -> None:
    for kind, value in words:
        if kind == "plain" and value:
            found.add(Decimal(value))
        elif kind == "hundred":
            found.add(Decimal(100))
        elif kind == "thousand":
            found.add(Decimal(1000))
        elif kind == "half":
            found.add(Decimal("0.5"))


def _since_thousand(words: list[tuple[str, int | Decimal | None]]) -> Decimal:
    """Run value after its last thousand word (SPEC §2, batch 21)."""
    start = 0
    for pos, (kind, value) in enumerate(words):
        if kind == "thousand" or (kind == "plain" and value is not None and value >= 1000):
            start = pos + 1
    return _run_value(words[start:])


def _hundred_cut(words: list[tuple[str, int | Decimal | None]], token: str) -> int:
    """Where a new hundreds group starts; a final 1-9 moves with it."""
    if words and words[-1][0] == "plain" and words[-1][1] is not None:
        if words[-1][1] in (1, 2, 3, 4, 5, 6, 7, 8, 9) and not token.startswith("و"):
            return len(words) - 1
    return len(words)


def _is_es_de_plain_under100(token: str, kind: str, value: int | Decimal | None) -> bool:
    """A Spanish or German plain number word under 100 (SPEC §2, round 5 #1)."""
    if kind != "plain" or value is None:
        return False
    if not Decimal(value) < 100:
        return False
    if token in SPANISH_NUMBERS and SPANISH_NUMBERS[token] < 100:
        return True
    german = _german_number(token)
    return german is not None and Decimal(german) < 100


def _is_es_de_token(token: str, kind: str) -> bool:
    """A Spanish or German word that makes its run need a unit after it (round 6)."""
    if kind == "plain":
        if token in SPANISH_NUMBERS:
            return True
        if token in GERMAN_HUNDRED or token in GERMAN_THOUSAND:
            return True
        return _german_number(token) is not None
    if kind == "hundred":
        return token in GERMAN_HUNDRED
    if kind == "thousand":
        return token in SPANISH_THOUSAND or token in GERMAN_THOUSAND
    if kind == "half":
        return token in SPANISH_HALF or token in GERMAN_HALF
    if kind == "article":
        return token in SPANISH_ARTICLES or token in GERMAN_ARTICLES
    if kind == "point":
        return token in ("coma", "komma")
    return False


def _is_german_number_token(token: str, kind: str) -> bool:
    """A German number token, which never joins a number before it (round 6)."""
    if kind != "plain":
        return False
    if token in GERMAN_HUNDRED or token in GERMAN_THOUSAND:
        return True
    return _german_number(token) is not None


def _las_hour_value(token: str) -> int | None:
    """Value of a word or digits that can be an hour after `las` (round 10)."""
    if token == "una":
        return 1
    value = SPANISH_NUMBERS.get(token)
    if value is not None:
        return value
    if token.isdigit():
        try:
            return int(token)
        except ValueError:
            return None
    return None


def _is_hour_number_token(token: str) -> bool:
    """A number up to 24 that can be a Spanish clock hour after `las` (round 9)."""
    value = _las_hour_value(token)
    return value is not None and value <= 24


def _is_clock_hour(tokens: list[str], idx: int) -> bool:
    if idx <= 0:
        return False
    prev = tokens[idx - 1]
    if prev == "la":
        return tokens[idx] == "una"
    if prev == "las":
        return _is_hour_number_token(tokens[idx])
    return False


def _is_clock_minutes(tokens: list[str], idx: int) -> bool:
    token = tokens[idx]
    if token not in SPANISH_NUMBERS:
        return False
    if idx >= 3 and tokens[idx - 1] in ("y", "menos") and _is_clock_hour(tokens, idx - 2):
        return True
    if idx >= 2 and 10 <= SPANISH_NUMBERS[token] <= 59 and _is_clock_hour(tokens, idx - 1):
        return True
    return (
        idx >= 2
        and tokens[idx - 1] == "y"
        and 1 <= SPANISH_NUMBERS[token] <= 9
        and _is_clock_minutes(tokens, idx - 2)
    )


def _is_clock_suppressed(tokens: list[str], idx: int) -> bool:
    """A clock hour or minutes that states nothing (SPEC §2, round 8)."""
    if not (_is_clock_hour(tokens, idx) or _is_clock_minutes(tokens, idx)):
        return False
    nxt = tokens[idx + 1] if idx + 1 < len(tokens) else None
    return nxt is None or nxt not in GATE_WORDS


def _is_es_de_number_word(token: str) -> bool:
    """A Spanish or German number word for coma/komma (SPEC §2, round 8)."""
    if token in SPANISH_NUMBERS or token in SPANISH_THOUSAND:
        return True
    if token == "null":
        return True
    if token in GERMAN_HUNDRED or token in GERMAN_THOUSAND:
        return True
    return _german_number(token) is not None


def _word_amounts(part: str, found: set[Decimal]) -> None:
    """Number-word runs in one punctuation-delimited part (SPEC §2)."""
    tokens = catalogue.normalise(part).split()
    kinds = [_classify(token) for token in tokens]
    words: list[tuple[str, int | Decimal | None]] = []
    flags: list[bool] = []

    def _flush(next_token: str | None) -> None:
        if not words:
            flags.clear()
            return
        if any(flags) and (next_token is None or next_token not in GATE_WORDS):
            words.clear()
            flags.clear()
            return
        value = _run_value(words)
        if value > 0:
            found.add(value)
        _word_values(words, found)
        words.clear()
        flags.clear()

    def _flush_list(
        group: list[tuple[str, int | Decimal | None]],
        group_flags: list[bool],
        next_token: str | None,
    ) -> None:
        if not group:
            return
        if any(group_flags) and (next_token is None or next_token not in GATE_WORDS):
            return
        value = _run_value(group)
        if value > 0:
            found.add(value)
        _word_values(group, found)

    index = 0
    while index < len(tokens):
        kind, value = kinds[index]
        token = tokens[index]
        if _is_clock_suppressed(tokens, index):
            _flush(token)
            index += 1
            continue
        if token == "null" and index + 1 < len(tokens) and tokens[index + 1] == "komma":
            if words:
                _flush(token)
            words.append(("plain", 0))
            flags.append(True)
            index += 1
            continue
        if token == "mil" and kind == "thousand":
            prev_spanish = index > 0 and tokens[index - 1] in SPANISH_NUMBERS
            next_spanish = index + 1 < len(tokens) and (
                tokens[index + 1] in SPANISH_NUMBERS or tokens[index + 1] in SPANISH_UNIT_WORDS
            )
            if not (prev_spanish or next_spanish):
                kind = "other"
        if token in SPANISH_HALF and kind == "half":
            after_number = index > 0 and tokens[index - 1] in SPANISH_NUMBERS
            after_y = (
                index > 1
                and tokens[index - 1] == "y"
                and (
                    tokens[index - 2] in SPANISH_NUMBERS
                    or tokens[index - 2] in SPANISH_ARTICLES
                )
                and not (index > 2 and tokens[index - 3] in ("la", "las"))
            )
            next_ok = index + 1 < len(tokens) and tokens[index + 1] in SPANISH_UNIT_OR_DOSE
            if not (after_number or after_y or next_ok):
                kind = "other"
        if token in ("cien", "ciento") and kind == "plain":
            if index > 0 and tokens[index - 1] == "por":
                kind = "other"
        if token == "acht" and kind == "plain":
            prev_ausser = index > 0 and tokens[index - 1] == "ausser"
            next_care = index + 1 < len(tokens) and tokens[index + 1] in GERMAN_CARE_VERBS
            if prev_ausser or next_care:
                kind = "other"
        if kind in ("plain", "hundred", "thousand", "half"):
            incoming_es_de = _is_es_de_token(token, kind)
            if words:
                run_has_es_de = any(flags)
                run_has_en_ar = any(not flag for flag in flags)
                if (incoming_es_de and run_has_en_ar) or (
                    not incoming_es_de and run_has_es_de
                ):
                    _flush(token)
            if kind == "half" and token in SPANISH_HALF | GERMAN_HALF:
                is_clock_half = (
                    index >= 3
                    and tokens[index - 1] == "y"
                    and (
                        tokens[index - 2] in SPANISH_NUMBERS
                        or tokens[index - 2] in SPANISH_ARTICLES
                    )
                    and tokens[index - 3] in ("la", "las")
                )
                if index == 0 or tokens[index - 1] != "y" or is_clock_half:
                    _flush(token)
            if kind == "hundred" and _since_thousand(words) >= 100:
                if index > 0 and kinds[index - 1][0] == "a":
                    cut = len(words)
                else:
                    cut = _hundred_cut(words, tokens[index])
                earlier = words[:cut]
                earlier_flags = flags[:cut]
                del words[:cut]
                del flags[:cut]
                _flush_list(earlier, earlier_flags, token)
            elif kind == "plain" and value is not None and value >= 100:
                is_spanish = token in SPANISH_HUNDREDS
                is_german = False
                if not is_spanish:
                    gval = _german_number(token)
                    is_german = isinstance(gval, int) and 100 <= gval <= 999
                if token in GERMAN_HUNDRED or token in GERMAN_THOUSAND:
                    is_german = True
                if (is_spanish or is_german) and _since_thousand(words) > 0:
                    _flush(token)
                elif _since_thousand(words) >= 100:
                    _flush(token)
            if (
                kind == "plain"
                and value is not None
                and Decimal(value) < 100
                and words
                and words[-1][0] == "plain"
                and words[-1][1] is not None
                and Decimal(words[-1][1]) < 100
                and index > 0
                and tokens[index - 1] != "y"
                and (_is_es_de_plain_under100(token, kind, value) or flags[-1])
            ):
                _flush(token)
            if kind == "plain" and _is_german_number_token(token, kind) and words:
                _flush(token)
            words.append((kind, value))
            flags.append(_is_es_de_token(token, kind))
            if kind == "half" and token in SPANISH_HALF | GERMAN_HALF:
                after = tokens[index + 1] if index + 1 < len(tokens) else None
                _flush(after)
        elif kind == "a":
            if index == 0 or kinds[index - 1][0] != "and":
                _flush(token)
            # else: filler inside "and a half", the run stays open
        elif kind == "article":
            if _article_counts(tokens, index):
                if words and (index == 0 or tokens[index - 1] != "y"):
                    _flush(token)
                words.append(("plain", 1))
                flags.append(True)
            else:
                _flush(token)
        elif kind == "y":
            if not _y_keeps_open(tokens, kinds, index):
                _flush(token)
        elif kind == "point":
            if token == "point" and words and any(flags):
                look = index + 1
                skipped: list[int] = []
                while look < len(tokens):
                    digit = _digit_value(tokens[look])
                    if digit is None:
                        break
                    skipped.append(digit)
                    look += 1
                words.clear()
                flags.clear()
                if skipped:
                    index = look - 1
            elif token in ("coma", "komma") and (
                not words or index == 0 or not _is_es_de_number_word(tokens[index - 1])
            ):
                _flush(token)
            else:
                digits: list[int] = []
                look = index + 1
                while look < len(tokens):
                    digit = _digit_value(tokens[look])
                    if digit is None and token == "komma" and tokens[look] == "null":
                        digit = 0
                    if digit is None:
                        break
                    digits.append(digit)
                    look += 1
                if digits:
                    after = tokens[look] if look < len(tokens) else None
                    digits_es_de = any(
                        _is_es_de_digit(tokens[pos]) for pos in range(index + 1, look)
                    )
                    is_es_de = any(flags) or token in ("coma", "komma") or digits_es_de
                    if is_es_de and (after is None or after not in GATE_WORDS):
                        words.clear()
                        flags.clear()
                        index = look - 1
                    else:
                        base = _run_value(words)
                        value = base + Decimal("0." + "".join(str(d) for d in digits))
                        if value > 0:
                            found.add(value)
                        _word_values(words, found)
                        for digit in digits:
                            if digit:
                                found.add(Decimal(digit))
                        words.clear()
                        flags.clear()
                        index = look - 1
                else:
                    _flush(token)
        elif kind != "and":
            _flush(token)
        index += 1
    _flush(None)


def _is_digit_clock_hour(dotted: str, match: re.Match[str]) -> bool:
    """True when a digit match is a Spanish clock hour (SPEC §2, round 9)."""
    before = dotted[: match.start()]
    after = dotted[match.end() :]
    before_part = _RUN_BREAK.split(before)[-1] if before else ""
    after_part = _RUN_BREAK.split(after)[0] if after else ""
    before_tokens = catalogue.normalise(before_part).split()
    after_tokens = catalogue.normalise(after_part).split()
    if not before_tokens or before_tokens[-1] not in ("la", "las"):
        return False
    if before_tokens[-1] == "la":
        return False
    amount = parse_amount_text(match.group(0))
    if amount is None or amount != int(amount) or amount > 24:
        return False
    nxt = after_tokens[0] if after_tokens else None
    return nxt is None or nxt not in GATE_WORDS


def stated_amounts(text: str) -> frozenset[Decimal]:
    """Every positive number the text states (SPEC §2, batch 20)."""
    text = unicodedata.normalize("NFC", text)
    found: set[Decimal] = set()
    dotted = text.replace("٫", ".")
    for match in _DIGIT_RUN.finditer(dotted):
        if _is_digit_clock_hour(dotted, match):
            continue
        amount = parse_amount_text(match.group(0))
        if amount is not None:
            found.add(amount)
    for part in _RUN_BREAK.split(text):
        _word_amounts(part, found)
    return frozenset(found)
