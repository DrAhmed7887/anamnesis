"""Canonical finding text and patient question mappings."""

from anamnesis.schema.findings import DiscrepancyType as D

TEMPLATES: dict[D, str] = {
    D.MATCH: "The compared identity and strength details agree.",
    D.STRENGTH_MISMATCH: "Patient-reported strength differs from the pack label.",
    D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH: "Reported intake differs from the strength of one pack unit.",
    D.INGREDIENT_MISMATCH: "Reported and pack ingredients differ.",
    D.RATIO_MISMATCH: "The reported and pack ingredient ratios differ.",
    D.FORMULATION_MISMATCH: "Reported and pack formulations differ (salt or release form).",
    D.INSUFFICIENT_INFORMATION: "The available evidence cannot confirm agreement.",
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
    "formulation": "What release form is shown on your medicine pack?",
    "information": "Could you provide the missing medication details?",
    "discontinued": "When did you stop using this medicine?",
    "unreadable": "Could you provide a clearer image of the pack label?",
    "name": "What is the name shown on the medicine pack?",
    "source": "Could you confirm whether you currently use this medicine?",
}

SCOPE_LINES: tuple[str, ...] = (
    "Anamnesis reports where the patient's account and the pack photos disagree. It gives no medical advice.",
    "Prescribed directions, timing, adherence and supply were not assessed.",
    "Over-the-counter, herbal and non-tablet products may be missing from this brief: ask about them.",
    "Checks across medicines cover shared ingredients and one curated class (beta-blockers); "
    "interactions were not assessed.",
)

SAME_INGREDIENT_NOTE = (
    "More than one product the patient mentioned, and did not report as stopped, "
    "contains this ingredient. Concurrent use is unconfirmed."
)
SAME_CLASS_NOTE = (
    "More than one medicine the patient mentioned, and did not report as stopped, "
    "belongs to this class. Concurrent use is unconfirmed."
)

SECTION_ORDER: tuple[str, ...] = (
    "disagree", "across", "unconfirmed", "agree", "stopped", "coverage", "photos", "voice",
)

SECTION_HEADINGS: dict[str, str] = {
    "disagree": "Disagreements",
    "across": "Across medicines",
    "unconfirmed": "Unconfirmed",
    "agree": "Agreement",
    "stopped": "Stopped medicines",
    "coverage": "Coverage",
    "photos": "Photos",
    "voice": "Voice note",
}

BRIEF_TITLE = "Medication intake brief"

NONE_TEXT = "None."
UNNAMED_PACK = "Unnamed pack"
NOT_MENTIONED = "Not mentioned."
NOT_PHOTOGRAPHED = "Not photographed."

MENTIONED_NOT_PHOTOGRAPHED = "Mentioned, not photographed"
PHOTOGRAPHED_NOT_MENTIONED = "Photographed, not mentioned"
REPORTED_STOPPED_NOT_PHOTOGRAPHED = "Reported as stopped, not photographed"

PATIENT_SIDE_HEADING = "Patient account"
PACK_SIDE_HEADING = "Pack photo"

FIELD_NAME = "Name"
FIELD_INN = "Ingredient"
FIELD_STRENGTH = "Strength"
FIELD_INTAKE = "Intake amount"
FIELD_REGIMEN = "Regimen"
FIELD_STATUS = "Status"
FIELD_LABEL = "Label text"
FIELD_READABILITY = "Readability"
FIELD_COUNTRY = "Country"

STRENGTH_PER = " per "

REGIMEN_UNITS_PER_INTAKE = "Units per intake"
REGIMEN_INTAKES_PER_DAY = "Intakes per day"
REGIMEN_AS_NEEDED = "As needed"

YES = "yes"
NO = "no"

PHOTO_ALT = "Photo {i}"
REGION_ALT = "Region {region_id}"

HEARD_IN = "Heard in"
SEEN_IN = "Seen in"
SEEN_REGION = "region {region_id}"
HEARD_TURN = "{turn_id} ({start}–{end})"
TURN_BUTTON = "▶ {start}–{end}"

REGION_CAPTION = "Photo {i}, region {region_id}, {readability}"
NOT_READ = "not read"

COVERAGE_PHOTOS_RECEIVED = "Photos received: {n}."
COVERAGE_NOT_OPENED = "Photo {i}: could not be opened; no model saw it."
COVERAGE_NOT_EXAMINED = "Photo {i}: not examined; the call budget ran out first."
COVERAGE_DETECTION_FAILED = "Photo {i}: pack detection failed."
COVERAGE_NO_PACK = "Photo {i}: no pack found."
COVERAGE_PACKS_FOUND = "Photo {i}: packs found {r}, labels read {o}, not fully readable {u}."
COVERAGE_VOICE_NONE = "Voice note: none."
COVERAGE_VOICE_NOT_TRANSCRIBED = "Voice note: not transcribed."
COVERAGE_VOICE_NO_EXTRACT = "Voice note: turns {t}; medicines could not be extracted."
COVERAGE_VOICE_OK = "Voice note: turns {t}, medicines mentioned {c}."
COVERAGE_BUDGET = "The intake stopped early: the call budget ran out, so later steps were skipped."

QUESTION_FOR: dict[D, str | None] = {
    D.MATCH: None,
    D.STRENGTH_MISMATCH: "strength",
    D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH: "intake",
    D.INGREDIENT_MISMATCH: "ingredients",
    D.RATIO_MISMATCH: "ratio",
    D.FORMULATION_MISMATCH: "formulation",
    D.INSUFFICIENT_INFORMATION: "information",
    D.DISCONTINUED_BUT_PRESENT: "discontinued",
    D.UNREADABLE_SOURCE: "unreadable",
    D.UNRESOLVED_NAME: "name",
    D.MISSING_MODALITY: "source",
}
