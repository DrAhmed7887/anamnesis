"""Parse model-written amount strings into Decimals (SPEC §2, batch 16)."""

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from anamnesis.schema import Strength

_AMOUNT_RE = re.compile(r"[0-9٠-٩۰-۹]+(?:[.,][0-9٠-٩۰-۹]+)?")
_WORD_RE = re.compile(r"(?:[^\W\d_]|ـ)+")


def parse_amount_text(value: object) -> Decimal | None:
    """Return a positive Decimal for one model-written amount, else None.

    ``"2.5"`` and the decimal comma ``"2,5"`` both parse; a comma is a
    decimal mark only when 1-2 digits follow it (``"1,000"`` is ambiguous).
    A dot followed by exactly three digits with a non-zero whole part
    (``"1.000"``) is ambiguous the same way, unless the whole part is zero
    (``"0.125"`` parses). A single number word, the whole amount, parses as
    its value. Ranges, two or more words, empty strings, zero and negatives
    return None.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value if value > 0 else None
    if isinstance(value, int):
        return Decimal(value) if value > 0 else None
    if isinstance(value, float):
        value = str(value)
    if not isinstance(value, str):
        return None
    text = value.strip().replace("٫", ".")
    if not _AMOUNT_RE.fullmatch(text):
        if not _WORD_RE.fullmatch(value.strip()):
            return None
        from anamnesis.core import catalogue
        from anamnesis.providers.stated import ARABIC_NUMBERS, ENGLISH_NUMBERS, _combined_hundreds

        word = catalogue.normalise(value.strip())
        number = ENGLISH_NUMBERS.get(word)
        if number is None:
            number = ARABIC_NUMBERS.get(word)
        if number is None:
            number = _combined_hundreds(word)
        if number is None or number <= 0:
            return None
        return Decimal(number)
    if "," in text:
        head, _, tail = text.partition(",")
        if not 1 <= len(tail) <= 2:
            return None
        text = f"{head}.{tail}"
    elif "." in text:
        head, _, tail = text.partition(".")
        if len(tail) == 3 and int(head) != 0:
            return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    return number if number > 0 else None


def coerce_strength(raw: Any) -> dict[str, Any] | None:
    """Return a strength dict with parsed amounts, or None to drop it.

    The strength becomes null when any ingredient amount doesn't parse, or
    when the Strength model rejects it (for example two salts of one INN).
    """
    if not isinstance(raw, dict):
        return None
    ingredients = raw.get("ingredients")
    if not isinstance(ingredients, list):
        return None
    coerced = []
    for part in ingredients:
        if not isinstance(part, dict):
            return None
        amount = parse_amount_text(part.get("amount"))
        if amount is None:
            return None
        coerced.append({**part, "amount": amount})
    candidate = {**raw, "ingredients": coerced}
    try:
        Strength.model_validate(candidate)
    except (TypeError, ValueError, ValidationError):
        return None
    return candidate
