"""Batch 25: the brief's look changes, and only its look (SPEC §7, "The look", batch 25). The brief is the product's
main screen, and it read like a plain document, so its one <style> element is redesigned. The page also gains one
viewport tag: without it a phone lays the page out 980 px wide and shrinks it, so the narrow-screen rule never
applied. Nothing else may change: the same report gives the same page outside the style and that tag, word for word
and tag for tag, with the same script. The style loads nothing, adds no words, hides nothing, and keeps every photo
box clickable across its whole area.

The hashes are of five briefs rendered on main at 63002d3, before the batch, each with the content of its <style>
element removed. A later batch that changes the brief on purpose updates them in its own contract."""

import hashlib
import re

import pytest

from anamnesis.brief import render_brief
from anamnesis.review import approve, new_review, request_photo
from anamnesis.schema import AudioTurn
from tests.contract import test_b19_brief as b19
from tests.contract import test_b20_review as b20

STYLE = re.compile(r"<style>(.*?)</style>", re.S)
VIEWPORT = '<meta name="viewport" content="width=device-width, initial-scale=1">'

EXPECTED = {
    "answered": "122ee055a85b6346d31ef312321895cd9d5ffbce01ed7a54e61abbb1089eea0d",
    "approved": "22f240cb6309852f0fd1729368e66625b7c3998ecb0266e6ddcab83f0ff1b2ee",
    "arabic": "5538447b3cc8440cd83c3852649508af9ab6ea6bf7f9a304878f4b477dfb07a2",
    "requested": "314b01e439953123f20d7ef30b377c9c0e45dff9696d9a3fa207bf93a396ba31",
    "showcase": "40ccbf192541066fbf2f1a12dca16b44a2d4f7f40a65bc5d5c68cc1d5a0e27b4",
}
OLD_STYLE = "d3a0f6361cc00f7b3df58ad3b7915959502ad6ef48d0fcddf4cd88ec4b1050d3"  # the style before batch 25


def requested():
    report = b20.first_intake()
    return report, request_photo(request_photo(new_review(report), report, "o1"), report, "c2")


def arabic():
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=5000, transcript="باخد كونكور ٥ مجم مرة في اليوم")]
    said = b19.claim("c1", "كونكور", ["turn-0"], intake=b19.mg("bisoprolol", 5), per_day=1)
    read = b19.reading("Concor 5 mg\nBisoprolol fumarate", b19.st(b19.mg("bisoprolol fumarate", 5)))
    report = b19.intake(b19.AUDIO[0], [(b19.PHOTO, "image/png")], turns=turns, claims=[said],
                        by_sha={b19.RC.image_sha256: [b19.RC]}, reads={b19.RC.region_id: [read]})
    return render_brief(report, [(b19.PHOTO, "image/png")], b19.AUDIO, b19.CAT)


def page(name):
    """One brief per state of the page: every section filled, a photo requested, a photo answered, an approved
    review, and Arabic speech."""
    if name == "showcase":
        return b19.showcase()[1]
    if name == "arabic":
        return arabic()
    report, review = requested()
    if name == "requested":
        return render_brief(report, b20.IMAGES, b20.AUDIO, b20.CAT, review=review)
    if name == "answered":
        after, answered, _, _ = b20.answer(report, review, "r1")
        return render_brief(after, b20.IMAGES + [(b20.PHOTO2, "image/png")], b20.AUDIO, b20.CAT, review=answered)
    return render_brief(report, b20.IMAGES, b20.AUDIO, b20.CAT, review=approve(new_review(report), report))


def style_of(html):
    found = STYLE.findall(html)
    assert len(found) == 1, "the page has exactly one <style> element"
    return found[0]


def flat(style):
    return re.sub(r"\s", "", style).lower()


def test_the_style_is_new():
    assert hashlib.sha256(style_of(page("showcase")).encode()).hexdigest() != OLD_STYLE


def test_the_page_is_laid_out_at_the_screens_width():
    html = page("showcase")
    assert html.count(VIEWPORT) == 1 and f'<head><meta charset="utf-8">{VIEWPORT}<title>' in html


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_the_page_outside_its_style_is_unchanged(name):
    html = page(name)
    style_of(html)
    outside = STYLE.sub("<style></style>", html).replace(VIEWPORT, "", 1)
    assert hashlib.sha256(outside.encode()).hexdigest() == EXPECTED[name]


def test_the_style_loads_nothing():
    style = flat(style_of(page("showcase")))
    assert "url(" not in style and "@import" not in style and "@font-face" not in style


def test_the_style_adds_no_words():
    """Words from CSS would change what the brief tells a clinician while the page itself stays the same."""
    values = re.findall(r"(?<![\w-])content\s*:\s*([^;}]*)", style_of(page("showcase")))
    assert all(value.strip() in ('""', "''", "none") for value in values)


def test_the_style_hides_nothing():
    """Whole declarations only: font-size:0.875rem and background-color:transparent hide nothing (batch 25 builder)."""
    style = flat(style_of(page("showcase")))
    for trick in ("display:none", "visibility:hidden", "visibility:collapse", "opacity"):
        assert trick not in style, trick
    assert not re.search(r"font-size:0(?![.\d])", style), "font-size:0"
    assert not re.search(r"(?<![\w-])color:transparent", style), "color:transparent"


def test_a_photo_box_stays_clickable_across_its_whole_area():
    """A transparent fill takes clicks inside the box; fill:none would leave only its outline clickable."""
    style = flat(style_of(page("showcase")))
    assert "fill:transparent" in style and "fill:none" not in style and "pointer-events:none" not in style
