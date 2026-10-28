"""Typed Muse Spark label reading boundary."""

import json
import re
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from anamnesis.core.guardrails import AdviceLeak, assert_no_advice, assert_no_advice_in_ingredients
from anamnesis.providers.base import ProviderError
from anamnesis.providers.numbers import coerce_strength, parse_amount_text
from anamnesis.providers.stated import stated_amounts
from anamnesis.schema import Readability, Strength

_COUNTRY_RE = re.compile(r"[A-Za-z]{2}")
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫", "01234567890123456789.")
_AR_LETTERS = "ء-غف-يٮ-ۓ"
_AR_ALL = _AR_LETTERS + "ً-ٰٟـ"
_NOT_AR = f"(?<![{_AR_ALL}])"
_END_AR = f"(?![{_AR_LETTERS}])"
_AR_SUFFIX = f"[{_AR_ALL}]*"
_AL = "(?:ال)?"

_NUM = r"[0-9]+(?:[.,][0-9]+)?"
_LATIN_UNITS = (
    r"milligrammes?|microgrammes?|grammes?|milligrams?|micrograms?|grams?|"
    r"miligramos?|microgramos?|gramos?|unidades|unités|units|unit|mcg|µg|μg|mg|IU|UI|U|g"
)
_AR_UNITS = (
    r"وحدة\s+دولية|مللي\s*جرام|ملي\s*جرام|ميكروجرام|ملجم|ملغ|مجم|مغ|جرام|جم|غ|وحدة"
)
_UNIT = rf"(?:(?:{_LATIN_UNITS})\b|{_NOT_AR}(?:{_AR_UNITS}){_END_AR})"
_CONN = rf"(?:/|∕|／|\bper\b|\bpor\b|\bpar\b|{_NOT_AR}لكل{_END_AR})"
_CONN_IN = rf"(?:{_CONN}|\bin\b|{_NOT_AR}في{_END_AR})"
_ML_END = r"(?!جم|غ|عق|لي\s*جرام|ي\s*جرام)"
_VOLUME_RE = re.compile(
    rf"({_NUM})\s*-?\s*(?:millilitres?|milliliters?|mililitros?|cm3|cm³|ml|cc|مل{_ML_END})",
    re.IGNORECASE,
)
_SPOON_RE = re.compile(
    r"\b(?:teaspoonfuls?|teaspoons?|tablespoonfuls?|tablespoons?|dessertspoonfuls?|"
    r"dessertspoons?|spoonfuls?|spoons?|tbsp|tsp)\b"
    r"|\b(?:cucharas?|cucharadas?|cucharaditas?|cuillères?-mesures?|cuillères?|cuillerées?)\b",
    re.IGNORECASE,
)
_MEASURE_RE = re.compile(
    r"(?:\bper\b|\beach\b|\bevery\b|\ba\b|\bone\b|(?<!\d)1(?!\d))\s+(measure)\b",
    re.IGNORECASE,
)
_AR_SPOON_RE = re.compile(
    rf"{_NOT_AR}{_AL}(?:ملعق|ملاعق){_AR_SUFFIX}"
    rf"|{_NOT_AR}{_AL}(?:معلقتين|معلقتان|معلقة|معلقه|معالق){_END_AR}"
)
_WATER_WORD = rf"(?:\b(?:water|agua|eau)\b|{_NOT_AR}{_AL}ماء{_END_AR})"
_WATER_RE = re.compile(_WATER_WORD, re.IGNORECASE)
_WATER_EXCLUSION_RE = re.compile(
    rf"(?:-(?=\w)|\s*(?:\bfor\s+injection\b|\bpurificada\b|\bdestilada\b|\bestéril\b|"
    rf"\bpurifiée\b|\bdistillée\b|\bstérile\b|{_NOT_AR}(?:مقطر|معقم|للحقن){_END_AR}))",
    re.IGNORECASE,
)
_DISSOLVE_LINK_RE = re.compile(rf"\b(?:of|de|du)\b|\bd'|{_NOT_AR}من{_END_AR}", re.IGNORECASE)
_DISSOLVE_ADJECTIVE_RE = re.compile(
    r"\b(?:lukewarm|warm|drinking|boiled|cooled|cool|cold|fresh|clean|plain|tap)\b", re.IGNORECASE
)
_BRACKET_RE = re.compile(r"\([^()]*\)")
_SQUARE_BRACKET_RE = re.compile(r"\[[^\[\]]*\]")
_WATER_BEFORE_BRACKET_RE = re.compile(rf"{_WATER_WORD}\s*\Z", re.IGNORECASE)

_BRACKET_ANY = r"(?:\([^()]*\)|\[[^\[\]]*\])"
_AFTER_AMOUNT_RE = re.compile(
    rf"{_NUM}\s*(?:{_UNIT}\s*)?(?:{_BRACKET_ANY}\s*)?{_CONN}\s*\(?\s*\Z",
    re.IGNORECASE,
)
_BEFORE_WORD = r"[^\s/∕／()]+"
_EACH = rf"(?:\beach\b|\bevery\b|\bcada\b|\bchaque\b|{_NOT_AR}كل{_END_AR})"
_CONN_WORD = rf"(?:\bper\b|\bpor\b|\bpar\b|\bin\b|{_NOT_AR}لكل{_END_AR}|{_NOT_AR}في{_END_AR})"
_BEFORE_SLASH_RE = re.compile(
    rf"^\s*(?:{_BEFORE_WORD}\s*){{0,5}}(?:/|∕|／)\s*(?:{_EACH}\s*)?\(?\s*$",
    re.IGNORECASE,
)
_BEFORE_WORD_RE = re.compile(
    rf"^\s*(?:{_BEFORE_WORD}\s+){{0,5}}{_CONN_WORD}\s*(?:{_EACH}\s*)?\(?\s*$",
    re.IGNORECASE,
)
_APPROX_RE = re.compile(
    rf"(?:\bapprox\b\.?|\baprox\b\.?|\babout\b|\bca\b\.?|\benv\b\.?|\benviron\b\.?|"
    rf"{_NOT_AR}حوالي{_END_AR})",
    re.IGNORECASE,
)
_ONE = r"(?<!\d)1(?:\.0+)?(?!\d)"
_ML = (
    rf"(?:\bmillilitre\b|\bmilliliter\b|\bmililitro\b|\bml\b|{_NOT_AR}مل{_ML_END})"
)
_PER_1ML_RE = re.compile(
    rf"({_NUM})\s*(?:{_UNIT}\s*)?{_CONN_IN}\s*(?:{_ONE}\s*)?{_ML}", re.IGNORECASE
)
_DOSE_WORD = (
    r"(?:\b(?:dose|dosis|actuation|spray|puff|inhalation|pulverización|pulvérisation|"
    r"drop|gota|goutte)\b|"
    rf"{_NOT_AR}(?:بخة|جرعة|نقطة){_END_AR})"
)
_PER_DOSE_RE = re.compile(
    rf"({_NUM})\s*(?:{_UNIT}\s*)?{_CONN}\s*(?:{_ONE}\s*|\bmetered\b\s*)?{_DOSE_WORD}",
    re.IGNORECASE,
)
_AMOUNT_UNIT_RE = re.compile(rf"({_NUM})\s*({_UNIT})", re.IGNORECASE)
_TABLET_RE = re.compile(
    r"\b(?:tablets?|tabs?|capsules?|caps|comprimidos?|cápsulas?|comprimés?|gélules?)\b"
    rf"|{_NOT_AR}{_AL}(?:قرص|أقراص|اقراص|كبسول){_AR_SUFFIX}",
    re.IGNORECASE,
)
_TABLET_GAP_END_RE = re.compile(r"[.,;!?؛،\r\n]")
_WORD_CHAR_RE = re.compile(r"\w")
_CAPITAL = f"A-ZÀ-Þ{_AR_LETTERS}"
_SENTENCE_END_RE = re.compile(rf";|!|\?|؛|\.(?= +[{_CAPITAL}])|\.(?=\s*$)")
_SENTENCE_DOT_RE = re.compile(rf"\.(?= +[{_CAPITAL}])")
_NUMBER_RE = re.compile(rf"(?<!\d){_NUM}(?!\d)")


class LabelReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_id: Annotated[str, Field(min_length=1)]
    label_text: str | None = None
    inn: Annotated[str, Field(min_length=1)] | None = None
    strength: Strength | None = None
    readability: Readability
    country: str | None = None

    @model_validator(mode="after")
    def require_readable_label(self) -> "LabelReading":
        if self.readability is Readability.READABLE and not self.label_text:
            raise ValueError("label_text is required when readability is readable")
        return self


def _check_no_advice(data: dict[str, Any]) -> None:
    """Run the advice check over raw model-written inn strings (SPEC §2)."""
    text = data.get("inn")
    if isinstance(text, str) and text:
        try:
            assert_no_advice(text)
        except AdviceLeak as exc:
            raise ValueError("label string failed the advice check") from exc
    assert_no_advice_in_ingredients(data)


_STRENGTH_KEYS = frozenset({"ingredients", "per", "release"})
_INGREDIENT_KEYS = frozenset({"inn", "amount", "unit"})


def _check_strength_shape(strength: Any) -> None:
    """Refuse strength keys beyond LABEL_SCHEMA's, so no model-written salt passes (SPEC §2)."""
    if not isinstance(strength, dict):
        return
    if set(strength) - _STRENGTH_KEYS:
        raise ValueError("label strength has keys beyond the schema")
    ingredients = strength.get("ingredients")
    if not isinstance(ingredients, list):
        return
    for part in ingredients:
        if isinstance(part, dict) and set(part) - _INGREDIENT_KEYS:
            raise ValueError("label strength ingredient has keys beyond the schema")


def _coerce_country(value: Any) -> str | None:
    """Keep only an ISO 3166-1 alpha-2 code, stored upper-case."""
    if isinstance(value, str) and _COUNTRY_RE.fullmatch(value):
        return value.upper()
    return None


def _find_dose_volumes(text: str) -> list[tuple[int, int]]:
    """Every volume (a number other than 1) and spoon span in the whole text."""
    spans = []
    for match in _VOLUME_RE.finditer(text):
        volume = parse_amount_text(match.group(1))
        if volume is not None and volume != 1:
            spans.append(match.span())
    spans.extend(match.span() for match in _SPOON_RE.finditer(text))
    spans.extend(match.span(1) for match in _MEASURE_RE.finditer(text))
    spans.extend(match.span() for match in _AR_SPOON_RE.finditer(text))
    return spans


def _skip_fillers(text: str, pos: int) -> int:
    """Skip whitespace and bracketed text (brackets aren't counted)."""
    while True:
        while pos < len(text) and text[pos].isspace():
            pos += 1
        bracket = _BRACKET_RE.match(text, pos)
        if bracket is None:
            return pos
        pos = bracket.end()


def _followed_by_water(text: str, start: int, end: int) -> bool:
    """True when a water word follows, with only the SPEC's short list between."""
    pos = _skip_fillers(text, end)
    if pos < len(text) and text[pos] == ")":
        opening = text.rfind("(", 0, start)
        if opening >= 0 and ")" not in text[opening:start]:
            pos = _skip_fillers(text, pos + 1)
    link = _DISSOLVE_LINK_RE.match(text, pos)
    if link is not None:
        pos = _skip_fillers(text, link.end())
    while (word := _DISSOLVE_ADJECTIVE_RE.match(text, pos)) is not None:
        pos = _skip_fillers(text, word.end())
    water = _WATER_RE.match(text, pos)
    return water is not None and _WATER_EXCLUSION_RE.match(text, water.end()) is None


def _inside_water_brackets(text: str, start: int, end: int) -> bool:
    """True for a lone volume in brackets right after a water word."""
    if start >= len(text) or not text[start].isdigit():
        return False
    opening = text.rfind("(", 0, start)
    if opening < 0 or ")" in text[opening:start]:
        return False
    closing = text.find(")", end)
    if closing < 0 or "(" in text[end:closing]:
        return False
    water = _WATER_BEFORE_BRACKET_RE.search(text[:opening])
    if water is None or _WATER_EXCLUSION_RE.match(text, water.end()) is not None:
        return False
    if text[end:closing].strip():
        return False
    before = text[opening + 1:start].strip()
    return not before or _APPROX_RE.fullmatch(before) is not None


def _counts_as_dose(text: str, start: int, end: int, per: str) -> bool:
    """True when one volume or spoon counts (SPEC §2)."""
    if _AFTER_AMOUNT_RE.search(text[:start]) is not None:
        return True
    if per == "ml":
        return True
    return not (
        _followed_by_water(text, start, end) or _inside_water_brackets(text, start, end)
    )


def _printed_per_1ml(text: str, amount) -> bool:
    for match in _PER_1ML_RE.finditer(text):
        if parse_amount_text(match.group(1)) == amount:
            return True
    return False


def _printed_per_dose(text: str, amount) -> bool:
    for match in _PER_DOSE_RE.finditer(text):
        if parse_amount_text(match.group(1)) == amount:
            return True
    return False


def _printed_per_tablet(text: str, amount) -> bool:
    for match in _AMOUNT_UNIT_RE.finditer(text):
        if parse_amount_text(match.group(1)) != amount:
            continue
        tablet = _TABLET_RE.search(text, match.end())
        if tablet is None:
            continue
        gap = text[match.end():tablet.start()]
        if _TABLET_GAP_END_RE.search(gap) is not None:
            continue
        words = sum(1 for token in gap.split() if _WORD_CHAR_RE.search(token))
        if words > 3:
            continue
        return True
    return False


def _strip_brackets(gap: str) -> str:
    """Remove bracketed text, which the before-form does not count."""
    for _ in range(3):
        stripped = _BRACKET_RE.sub(" ", gap)
        stripped = _SQUARE_BRACKET_RE.sub(" ", stripped)
        if stripped == gap:
            return stripped
        gap = stripped
    return gap


def _gap_has_sentence_end(gap: str) -> bool:
    """True when the before-form gap crosses a sentence end (SPEC §2)."""
    for pos, char in enumerate(gap):
        if char in ";!?؛":
            return True
        if (
            char == "."
            and _SENTENCE_DOT_RE.match(gap, pos) is not None
            and not _is_abbrev_dot(gap, pos)
        ):
            return True
    return False


def _printed_before_volume(text: str, number_end: int, volume_start: int) -> bool:
    """True when the gap holds up to five words, a connector, an optional each, `(`."""
    gap = _strip_brackets(text[number_end:volume_start])
    if _gap_has_sentence_end(gap):
        return False
    if _TABLET_RE.search(gap) is not None:
        return False
    return _BEFORE_SLASH_RE.match(gap) is not None or _BEFORE_WORD_RE.match(gap) is not None


def _starts_own_print(text: str, pos: int, amount, per: str) -> bool:
    """True when the number at pos starts the reading's own per-ml or per-dose print."""
    match = _PER_1ML_RE.match(text, pos)
    if match is not None and parse_amount_text(match.group(1)) == amount:
        return True
    if per == "dose":
        match = _PER_DOSE_RE.match(text, pos)
        return match is not None and parse_amount_text(match.group(1)) == amount
    return False


def _is_abbrev_dot(text: str, dot_pos: int) -> bool:
    """True when the dot follows a word of one to three Latin letters."""
    j = dot_pos - 1
    n = 0
    while j >= 0 and ("A" <= text[j] <= "Z" or "a" <= text[j] <= "z"):
        n += 1
        j -= 1
    return 1 <= n <= 3


def _find_sentence_end(text: str, end: int):
    """First sentence end after a volume, skipping abbreviation dots."""
    tail = text[end:]
    for match in _SENTENCE_END_RE.finditer(tail):
        if match.group(0) == "." and _is_abbrev_dot(text, end + match.start()):
            continue
        return match
    return None


def _printed_beside_a_volume(
    text: str, spans: list[tuple[int, int]], amounts: set, per: str
) -> bool:
    """True when a reading amount is also printed over a volume or after it in its sentence."""
    for start, end in spans:
        for number in _NUMBER_RE.finditer(text[:start]):
            if parse_amount_text(number.group(0)) not in amounts:
                continue
            if _printed_before_volume(text, number.end(), start):
                return True
        tail = text[end:]
        stop = _find_sentence_end(text, end)
        segment = tail[:stop.start()] if stop is not None else tail
        for number in _NUMBER_RE.finditer(segment):
            amount = parse_amount_text(number.group(0))
            if amount not in amounts:
                continue
            if per in ("ml", "dose") and _starts_own_print(text, end + number.start(), amount, per):
                continue
            return True
    return False


def _per_other_volume(label_text: str, strength: dict) -> bool:
    """True when a counting volume or spoon drops the strength (SPEC §2)."""
    text = label_text.translate(_DIGITS)
    amounts = {part["amount"] for part in strength["ingredients"]}
    per = str(strength.get("per")).lower()
    if per not in ("ml", "dose", "tablet", "capsule"):
        return False
    spans = _find_dose_volumes(text)
    if not any(_counts_as_dose(text, start, end, per) for start, end in spans):
        return False
    if per in ("tablet", "capsule", "dose"):
        for start, _ in spans:
            if _AFTER_AMOUNT_RE.search(text[:start]) is not None:
                return True
    if per == "ml":
        printed = all(_printed_per_1ml(text, amount) for amount in amounts)
    elif per == "dose":
        printed = all(
            _printed_per_1ml(text, amount) or _printed_per_dose(text, amount) for amount in amounts
        )
    else:
        printed = all(_printed_per_tablet(text, amount) for amount in amounts)
    if not printed:
        return True
    return _printed_beside_a_volume(text, spans, amounts, per)


def parse_label_json(text: str, region_id: str) -> LabelReading:
    try:
        data = json.loads(text)
        if not isinstance(data, dict) or "region_id" in data:
            raise ValueError("expected a label object without region_id")
        _check_no_advice(data)
        _check_strength_shape(data.get("strength"))
        strength = coerce_strength(data["strength"]) if data.get("strength") is not None else None
        if isinstance(strength, dict):
            label_text = data.get("label_text")
            if label_text is not None and not isinstance(label_text, str):
                raise ValueError("label_text is not a string")
            printed = stated_amounts(label_text or "")
            if not all(part["amount"] in printed for part in strength["ingredients"]):
                strength = None
            elif _per_other_volume(label_text or "", strength):
                strength = None
        validated = {
            **data,
            "region_id": region_id,
            "country": _coerce_country(data.get("country")),
            "strength": strength,
        }
        return LabelReading.model_validate(validated)
    except (TypeError, ValueError, ValidationError) as exc:
        raise ProviderError("spark", f"malformed label reading: {exc}", retryable=True) from exc
