"""Medication facts stated by a patient or observed on a pack."""

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonEmptyStr = Annotated[str, Field(min_length=1)]


class Unit(StrEnum):
    MG = "mg"
    MCG = "mcg"
    G = "g"
    ML = "ml"
    IU = "iu"


class StrengthPer(StrEnum):
    TABLET = "tablet"
    CAPSULE = "capsule"
    ML = "ml"
    DOSE = "dose"


class MedicationStatus(StrEnum):
    ACTIVE = "active"
    DISCONTINUED = "discontinued"
    UNKNOWN = "unknown"


class Readability(StrEnum):
    READABLE = "readable"
    PARTIAL = "partial"
    UNREADABLE = "unreadable"


class Release(StrEnum):
    IMMEDIATE = "immediate"
    MODIFIED = "modified"
    UNKNOWN = "unknown"


INN_ALIASES: dict[str, tuple[str, str | None]] = {
    "bisoprolol fumarate": ("bisoprolol", "fumarate"),
    "bisoprolol hemifumarate": ("bisoprolol", "hemifumarate"),
    "metoprolol succinate": ("metoprolol", "succinate"),
    "metoprolol tartrate": ("metoprolol", "tartrate"),
    "amlodipine besilate": ("amlodipine", "besilate"),
    "amlodipine besylate": ("amlodipine", "besilate"),
    "amlodipine mesilate": ("amlodipine", "mesilate"),
    "amlodipine maleate": ("amlodipine", "maleate"),
    "metformin hydrochloride": ("metformin", "hydrochloride"),
    "metformin hcl": ("metformin", "hydrochloride"),
    "atorvastatin calcium": ("atorvastatin", "calcium"),
    "atorvastatin calcium trihydrate": ("atorvastatin", "calcium trihydrate"),
    "amoxicillin trihydrate": ("amoxicillin", "trihydrate"),
    "amoxicillin sodium": ("amoxicillin", "sodium"),
    "potassium clavulanate": ("clavulanic acid", "potassium"),
    "clavulanate potassium": ("clavulanic acid", "potassium"),
    "acetaminophen": ("paracetamol", None),
}

SALT_BASIS_EQUIVALENTS: dict[tuple[str, str, Decimal], Decimal] = {
    ("metoprolol", "succinate", Decimal("23.75")): Decimal("25"),
    ("metoprolol", "succinate", Decimal("47.5")): Decimal("50"),
    ("metoprolol", "succinate", Decimal("95")): Decimal("100"),
    ("metoprolol", "succinate", Decimal("190")): Decimal("200"),
}


def _inn_and_salt(name: str) -> tuple[str, str | None]:
    normalised = name.strip().casefold()
    if normalised.endswith(")") and " (as " in normalised:
        moiety, alias = normalised[:-1].split(" (as ", 1)
        mapped = INN_ALIASES.get(alias)
        if mapped and mapped[0] == moiety:
            return mapped
    return INN_ALIASES.get(normalised, (normalised, None))


def canonical_inn(name: str) -> str:
    """Normalise an ingredient name for identity comparisons."""
    return _inn_and_salt(name)[0]


def salt_of(name: str) -> str | None:
    """Return a curated salt for an ingredient name, if one is known."""
    return _inn_and_salt(name)[1]


class IngredientAmount(BaseModel):
    """Amount of one active ingredient."""

    model_config = ConfigDict(extra="forbid")

    inn: NonEmptyStr
    salt: str | None = None
    amount: Decimal = Field(gt=0)
    unit: Unit

    @model_validator(mode="before")
    @classmethod
    def split_inn_and_salt(cls, data: object) -> object:
        if not isinstance(data, dict) or not isinstance(data.get("inn"), str):
            return data
        result = data.copy()
        result["inn"], inferred_salt = _inn_and_salt(data["inn"])
        if "salt" not in result:
            result["salt"] = inferred_salt
        return result


class Strength(BaseModel):
    """Ingredient amounts per tablet, capsule, volume, or dose."""

    model_config = ConfigDict(extra="forbid")

    ingredients: list[IngredientAmount]
    per: StrengthPer
    release: Release = Release.UNKNOWN

    @model_validator(mode="after")
    def require_ingredient(self) -> "Strength":
        if not self.ingredients:
            raise ValueError("strength must contain at least one ingredient")
        inns = [canonical_inn(part.inn) for part in self.ingredients]
        if len(inns) != len(set(inns)):
            raise ValueError("strength contains duplicate canonical INNs")
        return self


class DoseRegimen(BaseModel):
    """Patient-reported intake schedule."""

    model_config = ConfigDict(extra="forbid")

    units_per_intake: Decimal | None = None
    intakes_per_day: Decimal | None = None
    as_needed: bool | None = None

    @model_validator(mode="after")
    def require_positive_values(self) -> "DoseRegimen":
        for name in ("units_per_intake", "intakes_per_day"):
            value = getattr(self, name)
            if value is not None and value <= 0:
                raise ValueError(f"{name} must be greater than zero when provided")
        return self


class PatientClaim(BaseModel):
    """Medication details reported in audio."""

    model_config = ConfigDict(extra="forbid")

    claim_id: NonEmptyStr
    name_text: str
    inn: NonEmptyStr | None = None
    strength: Strength | None = None
    intake_amount: IngredientAmount | None = None
    regimen: DoseRegimen | None = None
    status: MedicationStatus
    audio_evidence: list[NonEmptyStr]

    @model_validator(mode="after")
    def require_audio_evidence(self) -> "PatientClaim":
        if not self.audio_evidence:
            raise ValueError("audio_evidence must contain at least one turn_id")
        return self


class PackObservation(BaseModel):
    """Medication details read from a photographed pack."""

    model_config = ConfigDict(extra="forbid")

    observation_id: NonEmptyStr
    label_text: str | None = None
    inn: NonEmptyStr | None = None
    strength: Strength | None = None
    readability: Readability
    country: str | None = None
    visual_evidence: list[NonEmptyStr]

    @model_validator(mode="after")
    def require_visual_evidence_and_readable_label(self) -> "PackObservation":
        if not self.visual_evidence:
            raise ValueError("visual_evidence must contain at least one region_id")
        if self.readability is Readability.READABLE and not self.label_text:
            raise ValueError("label_text is required when readability is readable")
        return self
