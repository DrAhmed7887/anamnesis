"""SAM 3.1 text output parser for source-pixel boxes."""

import re

from pydantic import ValidationError

from anamnesis.providers.base import ProviderError
from anamnesis.schema import ImageRegion

_RECORD = re.compile(
    r"(?P<id>\d+)<\|box;x1=(?P<x1>\d+);y1=(?P<y1>\d+);"
    r"x2=(?P<x2>\d+);y2=(?P<y2>\d+);w=(?P<w>\d+);h=(?P<h>\d+)"
    r"(?:;c=(?P<c>(?:\d+(?:\.\d*)?|\.\d+)))?\|>"
    # Mask payloads are base85, whose alphabet includes "|" and ">": the payload ends only where
    # the next record starts or the text ends.
    # Live sam-3.1 output also puts a confidence on the mask (`;c=…`) - seen 27 Oct 2026, not in the docs.
    r"<\|mask;x=\d+;y=\d+(?:;c=[\d.]+)?;data=\d+,\d+,[~!].*?\|>(?=,\d+<\|box;|$)",
    re.DOTALL,
)


def parse_sam_output(text: str, image_sha256: str) -> list[ImageRegion]:
    text = text.rstrip()  # live output ends with a newline
    if text == "":
        return []
    if not isinstance(text, str) or not text.startswith("<0f>"):
        raise ProviderError("sam", "malformed SAM output")
    regions: list[ImageRegion] = []
    offset = len("<0f>")
    try:
        while offset < len(text):
            match = _RECORD.match(text, offset)
            if match is None:
                raise ValueError("malformed SAM record")
            data = match.groupdict()
            object_id = int(data["id"])
            if any(region.object_id == object_id for region in regions):
                raise ValueError("duplicate SAM object id")
            regions.append(ImageRegion(
                region_id=f"{image_sha256[:12]}-{object_id}", image_sha256=image_sha256,
                object_id=object_id, x1=int(data["x1"]), y1=int(data["y1"]),
                x2=int(data["x2"]), y2=int(data["y2"]),
                frame_w=int(data["w"]), frame_h=int(data["h"]),
                confidence=float(data["c"]) if data["c"] is not None else None,
            ))
            offset = match.end()
            if offset < len(text):
                if text[offset] != "," or offset == len(text) - 1:
                    raise ValueError("malformed SAM separator")
                offset += 1
        if not regions:
            raise ValueError("missing SAM record")
    except (ValueError, ValidationError) as exc:
        raise ProviderError("sam", f"malformed SAM output: {exc}") from exc
    return regions


def top_regions(regions: list[ImageRegion], k: int = 3) -> list[ImageRegion]:
    if k < 0:
        raise ValueError("k cannot be negative")
    return sorted(regions, key=lambda region: (
        region.confidence is None,
        -(region.confidence or 0),
        region.object_id,
    ))[:k]
