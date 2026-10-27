"""Evidence models for audio turns and image regions."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonEmptyStr = Annotated[str, Field(min_length=1)]


class AudioTurn(BaseModel):
    """A single timed transcript segment."""

    model_config = ConfigDict(extra="forbid")

    turn_id: NonEmptyStr
    start_ms: int = Field(ge=0)
    end_ms: int
    transcript: str
    speaker: str | None = None
    lang_hint: str | None = None

    @model_validator(mode="after")
    def validate_timing(self) -> "AudioTurn":
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be greater than start_ms")
        return self


class ImageRegion(BaseModel):
    """A bounding region in source image pixels."""

    model_config = ConfigDict(extra="forbid")

    region_id: NonEmptyStr
    image_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    object_id: int = Field(ge=0)
    x1: int = Field(ge=0)
    y1: int = Field(ge=0)
    x2: int = Field(ge=0)
    y2: int = Field(ge=0)
    frame_w: int = Field(gt=0)
    frame_h: int = Field(gt=0)
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_bounds(self) -> "ImageRegion":
        if self.x2 < self.x1:
            raise ValueError("x2 must be greater than or equal to x1")
        if self.y2 < self.y1:
            raise ValueError("y2 must be greater than or equal to y1")
        if self.x2 >= self.frame_w:
            raise ValueError("x2 must be less than frame_w")
        if self.y2 >= self.frame_h:
            raise ValueError("y2 must be less than frame_h")
        return self
