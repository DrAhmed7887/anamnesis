"""Crop-zoom in source pixels: the crop is only ever cut from the photo the region came from."""

import hashlib
import io

from PIL import Image, UnidentifiedImageError

from anamnesis.schema import ImageRegion


def crop_region(image: bytes, region: ImageRegion, margin: float = 0.10) -> bytes:
    """PNG crop of the region plus a margin, clamped to the frame; refuses any other photo."""
    if hashlib.sha256(image).hexdigest() != region.image_sha256:
        raise ValueError("image does not match the region's source hash")
    try:
        with Image.open(io.BytesIO(image)) as source:
            if source.size != (region.frame_w, region.frame_h):
                raise ValueError("image size does not match the region's frame")
            pad_x = int((region.x2 - region.x1 + 1) * margin / 2)
            pad_y = int((region.y2 - region.y1 + 1) * margin / 2)
            box = (
                max(0, region.x1 - pad_x), max(0, region.y1 - pad_y),
                min(region.frame_w, region.x2 + 1 + pad_x), min(region.frame_h, region.y2 + 1 + pad_y),
            )
            out = io.BytesIO()
            source.convert("RGB").crop(box).save(out, format="PNG")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("image cannot be decoded") from exc
    return out.getvalue()
