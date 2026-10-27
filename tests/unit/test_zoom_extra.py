"""Batch 15.5 gaps the contract leaves: MPO, metadata of every kind, exhaustion guards, published regions."""

import io

from PIL import Image, PngImagePlugin

from anamnesis.agent import AgentAction, prepare_image
from tests.contract.test_b15_5_zoom import (
    RED,
    STORE,
    H,
    PixelReader,
    UprightSegmenter,
    W,
    intake,
    mean,
    near,
    png,
    upright,
)


def _exif(orientation=1):
    exif = Image.Exif()
    exif[0x0112] = orientation
    return exif


def _jpeg(**save):
    buf = io.BytesIO()
    upright().save(buf, "JPEG", quality=90, **save)
    return buf.getvalue()


def _bare(data):
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


def test_an_mpo_with_orientation_is_re_encoded_as_an_upright_jpeg_without_exif():
    buf = io.BytesIO()
    stored = upright().transpose(STORE[6])
    stored.save(buf, "MPO", save_all=True, append_images=[stored.copy()], exif=_exif(6))
    assert Image.open(io.BytesIO(buf.getvalue())).format == "MPO"
    data, mime = prepare_image(buf.getvalue(), "image/jpeg")
    img = _bare(data)
    assert (img.format, mime, img.size) == ("JPEG", "image/jpeg", (W, H)) and not img.getexif()
    assert near(mean(img, (15, 15, 55, 45)), RED)
    assert prepare_image(data, mime) == (data, mime)


def test_a_jpeg_comment_is_removed():
    marked = _jpeg(comment=b"Location=39.47,-0.37")
    assert b"39.47" in marked
    data, mime = prepare_image(marked, "image/jpeg")
    assert (mime, b"39.47" in data, _bare(data).info.get("comment")) == ("image/jpeg", False, None)
    assert prepare_image(data, mime) == (data, mime)


def test_a_crafted_app_segment_that_starts_with_ff_is_not_clean():
    clean = _jpeg()
    for marker, payload in ((0xE1, b"\xffLocation 39.47"), (0xE9, b"\xffGPS 39.47,-0.37")):
        segment = bytes([0xFF, marker]) + (len(payload) + 2).to_bytes(2, "big") + payload
        crafted = clean[:2] + segment + clean[2:]  # right after SOI
        assert b"39.47" in crafted
        data, mime = prepare_image(crafted, "image/jpeg")
        assert (mime, b"39.47" in data, data != crafted) == ("image/jpeg", False, True)


def test_a_two_frame_png_is_flattened_to_its_first_frame():
    first, second = Image.new("RGB", (8, 8), RED), Image.new("RGB", (8, 8), (20, 40, 220))
    buf = io.BytesIO()
    first.save(buf, "PNG", save_all=True, append_images=[second])
    assert getattr(_bare(buf.getvalue()), "n_frames", 1) == 2
    data, mime = prepare_image(buf.getvalue(), "image/png")
    img = _bare(data)
    assert data != buf.getvalue() and mime == "image/png"
    assert getattr(img, "n_frames", 1) == 1 and img.convert("RGB").getpixel((0, 0)) == RED


def test_a_jpeg_icc_profile_is_removed():
    icc = b"\x00" * 128
    data, mime = prepare_image(_jpeg(icc_profile=icc), "image/jpeg")
    img = _bare(data)
    assert mime == "image/jpeg" and "icc_profile" not in img.info and img.format == "JPEG"


def test_a_png_text_chunk_is_removed():
    info = PngImagePlugin.PngInfo()
    info.add_text("Location", "39.47,-0.37")
    marked = png(pnginfo=info)
    assert b"39.47" in marked
    data, mime = prepare_image(marked, "image/png")
    assert (mime, b"39.47" in data, _bare(data).text) == ("image/png", False, {})
    assert prepare_image(data, mime) == (data, mime)


def test_a_clean_webp_becomes_a_png():
    buf = io.BytesIO()
    upright().save(buf, "WEBP", lossless=True)
    data, mime = prepare_image(buf.getvalue(), "image/webp")
    img = _bare(data)
    assert (img.format, mime, img.size) == ("PNG", "image/png", (W, H))
    assert mean(img, (15, 15, 55, 45)) == RED


# --- exhaustion guards ---

def test_an_undecodable_photo_after_exhaustion_adds_no_step():
    report = intake([(png(), "image/png"), (b"junk", "image/jpeg")], UprightSegmenter(), PixelReader(),
                    max_provider_calls=1)
    assert report.steps[-1].action is AgentAction.BUDGET_EXHAUSTED
    assert "error: image cannot be decoded" not in [s.outcome for s in report.steps]


class _ThirdIsStale(UprightSegmenter):
    def segment(self, image, concept, *, mime):
        regions, t = super().segment(image, concept, mime=mime)
        return [*regions[:2], regions[2].model_copy(update={"frame_w": H, "frame_h": W})], t


def test_a_mismatched_region_is_logged_before_the_budget_runs_out():
    three = ((10, 10, 59, 49), (100, 70, 149, 109), (70, 10, 90, 30))
    report = intake([(png(), "image/png")], _ThirdIsStale(three), PixelReader(), max_provider_calls=2)
    actions = [s.action for s in report.steps]
    assert actions[-1] is AgentAction.BUDGET_EXHAUSTED
    mismatch = [s.outcome for s in report.steps].index("error: region does not match the photo")
    assert mismatch < actions.index(AgentAction.BUDGET_EXHAUSTED)


def test_a_stale_region_is_never_published():
    stale = _ThirdIsStale(((10, 10, 59, 49), (100, 70, 149, 109), (70, 10, 90, 30)))
    report = intake([(png(), "image/png")], stale, PixelReader())
    assert len(report.regions) == 2 and all((r.frame_w, r.frame_h) == (W, H) for r in report.regions)
    assert [s.outcome for s in report.steps if s.outcome.startswith("error: region")] == [
        "error: region does not match the photo"]
