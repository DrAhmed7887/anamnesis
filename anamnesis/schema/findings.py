"""Source discrepancy findings."""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonEmptyStr = Annotated[str, Field(min_length=1)]


class DiscrepancyType(StrEnum):
    MATCH = "match"
    STRENGTH_MISMATCH = "strength_mismatch"
    INTAKE_DIFFERS_FROM_UNIT_STRENGTH = "intake_differs_from_unit_strength"
    INGREDIENT_MISMATCH = "ingredient_mismatch"
    RATIO_MISMATCH = "ratio_mismatch"
    FORMULATION_MISMATCH = "formulation_mismatch"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    DISCONTINUED_BUT_PRESENT = "discontinued_but_present"
    UNREADABLE_SOURCE = "unreadable_source"
    UNRESOLVED_NAME = "unresolved_name"
    MISSING_MODALITY = "missing_modality"


class Finding(BaseModel):
    """A discrepancy with links to supporting audio and image evidence."""

    model_config = ConfigDict(extra="forbid")

    finding_id: NonEmptyStr
    type: DiscrepancyType
    claim_id: NonEmptyStr | None
    observation_id: NonEmptyStr | None
    audio_evidence: list[NonEmptyStr]
    visual_evidence: list[NonEmptyStr]
    needs_clinician_review: bool
    clinician_note: str
    patient_question_id: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_evidence_sides(self) -> "Finding":
        from anamnesis.schema.templates import QUESTION_FOR, TEMPLATES

        has_audio = bool(self.audio_evidence)
        has_visual = bool(self.visual_evidence)
        two_sided = {
            DiscrepancyType.MATCH,
            DiscrepancyType.STRENGTH_MISMATCH,
            DiscrepancyType.INTAKE_DIFFERS_FROM_UNIT_STRENGTH,
            DiscrepancyType.INGREDIENT_MISMATCH,
            DiscrepancyType.RATIO_MISMATCH,
            DiscrepancyType.FORMULATION_MISMATCH,
            DiscrepancyType.INSUFFICIENT_INFORMATION,
            DiscrepancyType.DISCONTINUED_BUT_PRESENT,
        }

        if self.type in two_sided and not (has_audio and has_visual):
            raise ValueError(f"{self.type.value} requires audio and visual evidence")
        if self.type is DiscrepancyType.UNREADABLE_SOURCE and not has_visual:
            raise ValueError("unreadable_source requires visual evidence")
        if self.type is DiscrepancyType.UNRESOLVED_NAME and not (has_audio or has_visual):
            raise ValueError("unresolved_name requires audio or visual evidence")
        if self.type is DiscrepancyType.MISSING_MODALITY and has_audio == has_visual:
            raise ValueError("missing_modality requires exactly one evidence side")
        if self.type is not DiscrepancyType.MATCH and not self.needs_clinician_review:
            raise ValueError(f"{self.type.value} requires clinician review")
        if (self.claim_id is not None) != has_audio:
            raise ValueError("claim_id must correspond to audio evidence")
        if (self.observation_id is not None) != has_visual:
            raise ValueError("observation_id must correspond to visual evidence")
        if self.clinician_note != TEMPLATES[self.type]:
            raise ValueError("clinician_note must use the canonical template")
        if self.patient_question_id != QUESTION_FOR[self.type]:
            raise ValueError("patient_question_id must use the canonical question")
        return self
