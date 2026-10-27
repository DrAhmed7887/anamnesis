"""Batch 15.5 contract: phone photos keep their provenance. Written by the reviewer; do not edit.

Live, 27 Oct (evidence/live/2026-10-27/zoom_before/): SAM applies a photo's EXIF orientation and Spark does not, so on
a portrait phone photo 2 of 3 labels were read from the wrong pack, and the crop-zoom refuses (90°) or mis-crops (180°)
any rotated photo. SPEC §4 step 0: every photo is prepared (upright pixels, no metadata) before a model sees it, and a
region is read only from the photo it was found on. QM M3 round 2 #1: nothing is logged after `budget_exhausted`.
"""

import hashlib
import io
from decimal import Decimal

import pytest
from PIL import Image, ImageOps

from anamnesis.agent import AgentAction, prepare_image, run_intake
from anamnesis.core.catalogue import load_catalogue
from anamnesis.providers import ProviderTrace
from anamnesis.providers.spark import LabelReading
from anamnesis.schema import ImageRegion

CAT = load_catalogue()
RED, BLUE, GREY = (220, 20, 20), (20, 40, 220), (128, 128, 128)
W, H = 160, 120  # displayed (upright) size of every test photo
# EXIF orientation -> how a viewer turns the stored pixels upright, and the inverse a phone applied when storing them
SHOW = {2: Image.Transpose.FLIP_LEFT_RIGHT, 3: Image.Transpose.ROTATE_180, 4: Image.Transpose.FLIP_TOP_BOTTOM,
        5: Image.Transpose.TRANSPOSE, 6: Image.Transpose.ROTATE_270, 7: Image.Transpose.TRANSVERSE,
        8: Image.Transpose.ROTATE_90}
STORE = {**SHOW, 6: Image.Transpose.ROTATE_90, 8: Image.Transpose.ROTATE_270}


def upright():
    """What the patient saw: a red pack top-left, a blue pack bottom-right, on a grey table."""
    img = Image.new("RGB", (W, H), GREY)
    img.paste(RED, (10, 10, 60, 50))
    img.paste(BLUE, (100, 70, 150, 110))
    return img


def phone_jpeg(orientation, gps=True):
    """The bytes a phone writes: stored pixels plus the EXIF orientation that shows them upright."""
    stored = upright() if orientation == 1 else upright().transpose(STORE[orientation])
    exif = Image.Exif()
    exif[0x0112] = orientation  # Orientation
    exif[0x010F] = "Staged"  # Make
    if gps:
        exif.get_ifd(0x8825).update({1: "N", 2: (0.0, 0.0, 0.0), 3: "E", 4: (0.0, 0.0, 0.0)})
    buf = io.BytesIO()
    stored.save(buf, "JPEG", quality=95, exif=exif)
    return buf.getvalue()


def png(img=None, **save):
    buf = io.BytesIO()
    (img or upright()).save(buf, "PNG", **save)
    return buf.getvalue()


def mean(img, box=None):
    return img.convert("RGB").crop(box or (0, 0, img.width, img.height)).resize((1, 1)).getpixel((0, 0))


def near(colour, target, tol=40):
    return all(abs(a - b) <= tol for a, b in zip(colour, target, strict=True))


def test_the_staged_phone_photos_are_what_a_viewer_sees():  # guards the fixtures themselves
    for orientation in range(1, 9):
        shown = ImageOps.exif_transpose(Image.open(io.BytesIO(phone_jpeg(orientation))))
        assert shown.size == (W, H) and near(mean(shown, (15, 15, 55, 45)), RED)


# --- preparation --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("orientation", [3, 6, 8, 2, 4, 5, 7])
def test_prepare_turns_every_exif_orientation_upright(orientation):
    data, mime = prepare_image(phone_jpeg(orientation), "image/jpeg")
    img = Image.open(io.BytesIO(data))
    assert (img.format, mime, img.size) == ("JPEG", "image/jpeg", (W, H))
    assert near(mean(img, (15, 15, 55, 45)), RED) and near(mean(img, (105, 75, 145, 105)), BLUE)


@pytest.mark.parametrize("orientation", [1, 6])
def test_prepare_drops_all_metadata(orientation):
    data, _ = prepare_image(phone_jpeg(orientation), "image/jpeg")
    img = Image.open(io.BytesIO(data))
    assert not img.getexif() and "exif" not in img.info and "xmp" not in img.info  # no GPS, camera or orientation


def test_a_rotated_png_becomes_an_upright_png():
    exif = Image.Exif()
    exif[0x0112] = 6
    data, mime = prepare_image(png(upright().transpose(STORE[6]), exif=exif), "image/png")
    img = Image.open(io.BytesIO(data))
    assert (img.format, mime, img.size) == ("PNG", "image/png", (W, H)) and not img.getexif()
    assert mean(img, (15, 15, 55, 45)) == RED  # lossless


def test_an_upright_photo_without_metadata_is_returned_byte_for_byte():
    clean = io.BytesIO()
    upright().save(clean, "JPEG", quality=90)
    for data, mime in [(png(), "image/png"), (clean.getvalue(), "image/jpeg")]:
        assert prepare_image(data, mime) == (data, mime)


def test_preparation_is_deterministic_and_idempotent():
    raw = phone_jpeg(6)
    once = prepare_image(raw, "image/jpeg")
    assert once[0] != raw
    assert prepare_image(raw, "image/jpeg") == once
    assert prepare_image(*once) == once


def test_undecodable_bytes_are_refused():
    with pytest.raises(ValueError):
        prepare_image(b"HEIC or junk", "image/jpeg")


# --- the loop: every model sees the prepared pixels, and a region is read only from its own photo ----------------

def trace(cid):
    return ProviderTrace(call_id=cid, model_id="fixture:test", latency_ms=1, input_tokens=0, output_tokens=0,
                         cost_usd=Decimal("0.001"))


class UprightSegmenter:
    """Like SAM: boxes are in the displayed frame of the bytes it receives. Object 0 sits on the red pack."""

    def __init__(self, boxes=((10, 10, 59, 49),)):
        self.boxes, self.seen = boxes, []

    def segment(self, image, concept, *, mime):
        self.seen.append((image, mime))
        shown = ImageOps.exif_transpose(Image.open(io.BytesIO(image)))
        sha = hashlib.sha256(image).hexdigest()
        return [ImageRegion(region_id=f"{sha[:12]}-{i}", image_sha256=sha, object_id=i, x1=x1, y1=y1, x2=x2, y2=y2,
                            frame_w=shown.width, frame_h=shown.height, confidence=0.9 - i / 10)
                for i, (x1, y1, x2, y2) in enumerate(self.boxes)], trace(f"sam-{len(self.seen)}")


class PixelReader:
    """Unreadable at full frame; on a crop it reports the colour of the pack it was actually shown."""

    def __init__(self):
        self.calls = []

    def read(self, image, region, *, mime, cropped=False):
        self.calls.append((image, mime, cropped))
        if not cropped:
            return LabelReading(region_id=region.region_id, readability="unreadable"), trace("read")
        label = "Concor 5 mg" if near(mean(Image.open(io.BytesIO(image))), RED, 60) else "another pack"
        return LabelReading(region_id=region.region_id, label_text=label, readability="readable"), trace("zoom")


def intake(images, segmenter, reader, **kw):
    return run_intake(None, images, transcriber=None, extractor=None, segmenter=segmenter, reader=reader,
                      catalogue=CAT, **kw)


@pytest.mark.parametrize("orientation", [3, 6, 8])
def test_a_rotated_phone_photo_is_read_from_the_pixels_of_its_region(orientation):
    seg, reader = UprightSegmenter(), PixelReader()
    report = intake([(phone_jpeg(orientation), "image/jpeg")], seg, reader)
    [(sent, mime)] = seg.seen
    prepared = Image.open(io.BytesIO(sent))
    assert prepared.size == (W, H) and not prepared.getexif() and mime == "image/jpeg"  # SAM: upright, no metadata
    assert [(img, m) for img, m, cropped in reader.calls if not cropped] == [(sent, mime)]  # Spark: the same bytes
    assert report.regions[0].image_sha256 == hashlib.sha256(sent).hexdigest()
    [obs] = report.observations
    assert obs.label_text == "Concor 5 mg"  # the zoom crop under the red pack's region showed the red pack


def test_raw_and_prepared_photos_give_the_same_intake():
    raw = phone_jpeg(6)
    a = intake([(raw, "image/jpeg")], UprightSegmenter(), PixelReader())
    b = intake([prepare_image(raw, "image/jpeg")], UprightSegmenter(), PixelReader())
    assert a.intake_id == b.intake_id and a.regions == b.regions and a.observations == b.observations


def test_a_photo_that_cannot_be_decoded_is_never_sent_to_a_model():
    seg, reader = UprightSegmenter(), PixelReader()
    report = intake([(b"HEIC or junk", "image/heic"), (png(), "image/png")], seg, reader)
    assert [m for _, m in seg.seen] == ["image/png"]  # only the decodable photo reached SAM
    assert report.steps[0].action is AgentAction.SEGMENT
    assert report.steps[0].outcome == "error: image cannot be decoded" and report.steps[0].call_ids == []


@pytest.mark.parametrize("change", [{"frame_w": H, "frame_h": W}, {"image_sha256": "0" * 64}])
def test_a_region_that_does_not_match_its_photo_is_never_read(change):
    class Stale(UprightSegmenter):
        def segment(self, image, concept, *, mime):
            regions, t = super().segment(image, concept, mime=mime)
            return [regions[0].model_copy(update=change)], t

    reader = PixelReader()
    report = intake([(png(), "image/png")], Stale(), reader)
    assert reader.calls == [] and report.observations == []
    assert [s.outcome for s in report.steps if s.action is AgentAction.READ] == ["error: region does not match the photo"]


# --- QM M3 round 2 #1: budget_exhausted is the last step, whatever fails afterwards --------------------------------

def test_nothing_is_logged_after_budget_exhausted_not_even_a_failed_crop(monkeypatch):
    def broken(image, region, margin=0.10):
        raise ValueError("crop failed")

    monkeypatch.setattr("anamnesis.agent.loop.crop_region", broken)
    three = ((10, 10, 59, 49), (100, 70, 149, 109), (70, 10, 90, 30))

    control = intake([(png(), "image/png")], UprightSegmenter(three), PixelReader())
    assert "error: crop failed" in [s.outcome for s in control.steps if s.action is AgentAction.ZOOM_READ]

    report = intake([(png(), "image/png")], UprightSegmenter(three), PixelReader(), max_provider_calls=3)
    actions = [s.action for s in report.steps]
    assert actions.count(AgentAction.BUDGET_EXHAUSTED) == 1 and actions[-1] is AgentAction.BUDGET_EXHAUSTED
