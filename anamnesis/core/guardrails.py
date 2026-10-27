"""Fixed, advice-free text for reconciliation findings."""

import re

from anamnesis.schema import DiscrepancyType as D

TEMPLATES: dict[D, str] = {
    D.MATCH: "The reported medication details agree with the pack label.",
    D.STRENGTH_MISMATCH: "Patient-reported strength differs from the pack label.",
    D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH: "Reported intake differs from the strength of one pack unit.",
    D.INGREDIENT_MISMATCH: "Reported and pack ingredients differ.",
    D.RATIO_MISMATCH: "The reported and pack ingredient ratios differ.",
    D.DISCONTINUED_BUT_PRESENT: "The patient reports discontinuation, and the pack is present.",
    D.UNREADABLE_SOURCE: "The pack label is not fully readable.",
    D.UNRESOLVED_NAME: "A medication name could not be resolved in the catalogue.",
    D.MISSING_MODALITY: "Medication evidence is present in only one source.",
}

PATIENT_QUESTIONS: dict[str, str] = {
    "strength": "What strength do you currently use?",
    "intake": "How much do you use at each intake?",
    "ingredients": "Which ingredients are listed on your medicine?",
    "ratio": "What amounts are listed for each ingredient?",
    "discontinued": "When did you stop using this medicine?",
    "unreadable": "Could you provide a clearer image of the pack label?",
    "name": "What is the name shown on the medicine pack?",
    "source": "Could you confirm whether you currently use this medicine?",
}

QUESTION_FOR: dict[D, str | None] = {
    D.MATCH: None,
    D.STRENGTH_MISMATCH: "strength",
    D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH: "intake",
    D.INGREDIENT_MISMATCH: "ingredients",
    D.RATIO_MISMATCH: "ratio",
    D.DISCONTINUED_BUT_PRESENT: "discontinued",
    D.UNREADABLE_SOURCE: "unreadable",
    D.UNRESOLVED_NAME: "name",
    D.MISSING_MODALITY: "source",
}


class AdviceLeak(Exception):
    """Text contains dosing instructions or advice."""


_ADVICE = re.compile(
    r"\b(?:you should|you must|take|increase|decrease|reduce|stop taking|double|skip|"
    r"debe|tome|tomar|nehmen sie|sollten)\b",
    re.IGNORECASE,
)


def assert_no_advice(text: str) -> None:
    """Reject phrases that could instruct medication dosing."""
    if _ADVICE.search(text):
        raise AdviceLeak(text)
