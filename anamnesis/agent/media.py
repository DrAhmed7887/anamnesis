"""Photo preparation: upright pixels and no metadata, before any model sees the photo (SPEC §4 step 0)."""

import io

from PIL import Image, ImageOps, UnidentifiedImageError

_JPEG = {"JPEG", "MPO"}  # an MPO (Ultra HDR, gain map) is a JPEG whose extra frames we drop
_XMP_KEYS = ("xmp", "XML:com.adobe.xmp")
_PNG_MODES = {"1", "L", "LA", "I", "I;16", "P", "RGB", "RGBA"}
_BENIGN_APP = {"APP0": b"JFIF\0", "APP14": b"Adobe"}  # structure, not metadata


def _clean_jpeg(img: Image.Image) -> bool:
    """A plain single-frame JPEG with no EXIF, XMP, ICC, IPTC or comment segments."""
    return (img.format == "JPEG" and not img.info.get("comment") and not img.getexif()
            and all(marker in _BENIGN_APP and data.startswith(_BENIGN_APP[marker])
                    for marker, data in img.applist))


def _clean_png(img: Image.Image) -> bool:
    """A still PNG with no text chunks, EXIF, ICC profile or XMP."""
    return (img.format == "PNG" and getattr(img, "n_frames", 1) == 1 and not getattr(img, "text", None)
            and not img.getexif() and not any(key in img.info for key in ("exif", "icc_profile", *_XMP_KEYS)))


def _encode(img: Image.Image, jpeg: bool) -> tuple[bytes, str]:
    out = io.BytesIO()
    if jpeg:
        img.save(out, format="JPEG", quality=95, subsampling=0)
        return out.getvalue(), "image/jpeg"
    img.save(out, format="PNG")
    return out.getvalue(), "image/png"


def prepare_image(data: bytes, mime: str) -> tuple[bytes, str]:
    """Upright, metadata-free photo (unchanged bytes if it already is). ValueError if undecodable."""
    try:
        with Image.open(io.BytesIO(data)) as source:
            source.load()
            if _clean_jpeg(source) or _clean_png(source):
                return data, mime
            jpeg = source.format in _JPEG
            upright = ImageOps.exif_transpose(source)
            clean = upright.copy()  # primary frame only
            clean.info = {k: v for k, v in upright.info.items() if k == "transparency"}  # drops the rest
            if not jpeg and clean.mode not in _PNG_MODES:
                clean = clean.convert("RGB")
            return _encode(clean, jpeg)
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
        raise ValueError("image cannot be decoded") from exc
