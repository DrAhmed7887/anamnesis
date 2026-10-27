"""Fixed, advice-free text for reconciliation findings."""

import re

from anamnesis.schema.templates import PATIENT_QUESTIONS, QUESTION_FOR, TEMPLATES

__all__ = ["PATIENT_QUESTIONS", "QUESTION_FOR", "TEMPLATES", "AdviceLeak", "assert_no_advice"]


class AdviceLeak(Exception):
    """Text contains dosing instructions or advice."""


_ADVICE = re.compile(
    r"\b(?:you should|you must|take|increase|decrease|reduce|stop taking|double|skip|"
    r"split|halve|continue|keep taking|safe|"
    r"debe|tome|tomar|nehmen sie|sollten)\b",
    re.IGNORECASE,
)


def assert_no_advice(text: str) -> None:
    """Reject phrases that could instruct medication dosing."""
    if _ADVICE.search(text):
        raise AdviceLeak(text)
