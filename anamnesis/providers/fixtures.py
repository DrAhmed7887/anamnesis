"""Offline provider implementations backed by replay fixtures."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from anamnesis.providers.base import ProviderError, ProviderTrace
from anamnesis.providers.sam import parse_sam_output
from anamnesis.providers.spark import LabelReading, parse_label_json
from anamnesis.providers.voice import parse_transcribe_response
from anamnesis.schema import AudioTurn, ImageRegion


class VoiceTranscriber(Protocol):
    def transcribe(
        self, audio_sha256: str, lang_hint: str | None = None,
    ) -> tuple[list[AudioTurn], ProviderTrace]: ...


class ImageSegmenter(Protocol):
    def segment(self, image_sha256: str, concept: str) -> tuple[list[ImageRegion], ProviderTrace]: ...


class LabelReader(Protocol):
    def read(self, region: ImageRegion) -> tuple[LabelReading, ProviderTrace]: ...


def _trace(model_id: str, *parts: str) -> ProviderTrace:
    digest = hashlib.sha256(json.dumps(parts).encode("utf-8")).hexdigest()[:20]
    return ProviderTrace(
        call_id=f"fixture-{digest}", model_id=f"fixture:{model_id}",
        latency_ms=0, input_tokens=0, output_tokens=0, cost_usd=Decimal(0),
    )


def _read(path: Path, provider: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ProviderError(provider, f"missing fixture: {path}") from exc


class FixtureTranscriber:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def transcribe(
        self, audio_sha256: str, lang_hint: str | None = None,
    ) -> tuple[list[AudioTurn], ProviderTrace]:
        text = _read(self.root / "voice" / f"{audio_sha256}.json", "voice")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError("voice", f"malformed fixture JSON: {exc}") from exc
        return parse_transcribe_response(payload, lang_hint), _trace(
            "muse-voice-transcribe-1.0", audio_sha256, lang_hint or "",
        )


class FixtureSegmenter:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def segment(self, image_sha256: str, concept: str) -> tuple[list[ImageRegion], ProviderTrace]:
        text = _read(self.root / "sam" / f"{image_sha256}.txt", "sam")
        return parse_sam_output(text, image_sha256), _trace("sam-3.1", image_sha256, concept)


class FixtureLabelReader:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def read(self, region: ImageRegion) -> tuple[LabelReading, ProviderTrace]:
        text = _read(self.root / "label" / f"{region.region_id}.json", "spark")
        return parse_label_json(text, region.region_id), _trace("muse-spark-1.3", region.region_id)
