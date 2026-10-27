"""Fixed, advice-free text for reconciliation findings."""

import re
from typing import Any

from anamnesis.schema.templates import PATIENT_QUESTIONS, QUESTION_FOR, TEMPLATES

__all__ = [
    "PATIENT_QUESTIONS",
    "QUESTION_FOR",
    "TEMPLATES",
    "AdviceLeak",
    "assert_no_advice",
    "assert_no_advice_in_ingredients",
]


class AdviceLeak(Exception):
    """Text contains dosing instructions or advice."""


_ADVICE = re.compile(
    r"\b(?:you should|you must|take|increase|decrease|reduce|stop taking|double|skip|"
    r"split|halve|continue|keep taking|safe|"
    r"debe|tome|tomar|nehmen sie|sollten|"
    r"يجب|خذ|تناول|توقف|ضاعف|ينصح)\b",
    re.IGNORECASE,
)


def assert_no_advice(text: str) -> None:
    """Reject phrases that could instruct medication dosing."""
    if _ADVICE.search(text):
        raise AdviceLeak(text)


def assert_no_advice_in_ingredients(data: Any) -> None:
    """Run the advice check over raw strength ingredient `inn` strings.

    Shared by the claim and label parsers (SPEC §2): it runs on the raw
    model-written strings before any amount that doesn't parse is dropped.
    """
    if not isinstance(data, dict):
        return
    strength = data.get("strength")
    if not isinstance(strength, dict):
        return
    ingredients = strength.get("ingredients")
    if not isinstance(ingredients, list):
        return
    for part in ingredients:
        if isinstance(part, dict):
            text = part.get("inn")
            if isinstance(text, str) and text:
                try:
                    assert_no_advice(text)
                except AdviceLeak as exc:
                    raise ValueError("model string failed the advice check") from exc
