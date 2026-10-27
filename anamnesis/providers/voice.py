"""Muse Voice Transcribe response boundary."""

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from anamnesis.providers.base import ProviderError
from anamnesis.schema import AudioTurn


class _VoiceTurn(BaseModel):
    turnId: int = Field(ge=0)
    startMs: int = Field(ge=0)
    endMs: int
    transcript: str = Field(min_length=1)
    speaker: str | None = None


class _VoiceResponse(BaseModel):
    audioDurationMs: int = Field(ge=0)
    turns: list[_VoiceTurn]


def parse_transcribe_response(payload: Any, lang_hint: str | None = None) -> list[AudioTurn]:
    try:
        response = _VoiceResponse.model_validate(payload)
        return [
            AudioTurn(
                turn_id=f"turn-{turn.turnId}", start_ms=turn.startMs, end_ms=turn.endMs,
                transcript=turn.transcript, speaker=turn.speaker, lang_hint=lang_hint,
            )
            for turn in response.turns
        ]
    except ValidationError as exc:
        raise ProviderError("voice", f"malformed transcription: {exc}") from exc
