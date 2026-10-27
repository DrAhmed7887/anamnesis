"""Clinician review and photo requests (SPEC §8, batch 20)."""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonEmptyStr = Annotated[str, Field(min_length=1)]


class RequestKind(StrEnum):
    UNREADABLE = "unreadable"
    NOT_PHOTOGRAPHED = "not_photographed"


class RequestStatus(StrEnum):
    OPEN = "open"
    ANSWERED = "answered"
    WITHDRAWN = "withdrawn"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    AWAITING_PATIENT = "awaiting_patient"
    APPROVED = "approved"


class PhotoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: NonEmptyStr
    kind: RequestKind
    target_id: NonEmptyStr
    status: RequestStatus
    photo_index: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def check_photo_index(self) -> "PhotoRequest":
        if (self.photo_index is not None) != (self.status is RequestStatus.ANSWERED):
            raise ValueError("photo_index is set exactly when answered")
        return self


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intake_id: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    status: ReviewStatus
    requests: list[PhotoRequest] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_status(self) -> "Review":
        waiting = self.status is ReviewStatus.AWAITING_PATIENT
        if waiting != any(r.status is RequestStatus.OPEN for r in self.requests):
            raise ValueError("awaiting_patient exactly when a request is open")
        return self
