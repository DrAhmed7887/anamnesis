"""Batch 24.2: a side whose own name and ingredient disagree shows no catalogue codes (SPEC §7, batch 24.2). The
batch 24.1 supervisor found a claim named "Concor" with the stated ingredient "atorvastatin" showing bisoprolol's
codes next to the patient's atorvastatin. Codes say which medicine a name is, so when the side contradicts its own
name, the brief shows none: no code rather than a code the patient's own words dispute."""

from pathlib import Path

from anamnesis.brief import render_brief
from anamnesis.core.catalogue import load_catalogue
from anamnesis.schema import AudioTurn
from tests.contract.test_b19_brief import PHOTO, RC, Page, claim, intake, mg, reading, st

CAT = load_catalogue()
VOICE = (b"wav", "audio/wav")
WHO = "WHO Collaborating Centre for Drug Statistics Methodology"
ROOT = Path(__file__).resolve().parents[2]


def brief(claims, read, transcript):
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=3000, transcript=transcript)]
    report = intake(VOICE[0], [(PHOTO, "image/png")], turns=turns, claims=claims, by_sha={RC.image_sha256: [RC]},
                    reads={RC.region_id: [read, read]})  # a second reading for a zoom
    html = render_brief(report, [(PHOTO, "image/png")], VOICE, CAT)
    page = Page(html).root
    boxes = {finding.finding_id: page.by_id(f"finding:{finding.finding_id}") for finding in report.findings}
    return html, report, boxes


def claim_box_text(report, boxes, claim_id="c1"):
    return " ".join(boxes[f.finding_id].text() for f in report.findings if f.claim_id == claim_id)


def test_a_claim_whose_stated_ingredient_disagrees_with_its_name_shows_no_codes():
    said = claim("c1", "Concor", ["turn-0"], intake=mg("atorvastatin", 20)).model_copy(update={"inn": "atorvastatin"})
    html, report, boxes = brief([said], reading(None, None, readability="unreadable"),
                                "Concor, the atorvastatin one, 20 mg")
    assert "ATC " not in claim_box_text(report, boxes) and WHO not in html


def test_a_claim_whose_strength_disagrees_with_its_name_shows_no_codes():
    said = claim("c1", "Concor", ["turn-0"], strength=st(mg("atorvastatin", 20)))
    html, report, boxes = brief([said], reading(None, None, readability="unreadable"), "Concor atorvastatin 20 mg")
    assert "ATC " not in claim_box_text(report, boxes) and WHO not in html


def test_a_claim_whose_ingredient_agrees_keeps_its_codes():
    said = claim("c1", "Concor", ["turn-0"], intake=mg("bisoprolol", 5)).model_copy(update={"inn": "bisoprolol"})
    html, report, boxes = brief([said], reading(None, None, readability="unreadable"), "Concor, bisoprolol, 5 mg")
    assert "ATC C07AB07 · RxNorm 19484" in claim_box_text(report, boxes) and html.count(WHO) == 1


def test_a_pack_whose_reading_disagrees_with_its_label_shows_no_codes():
    html, report, boxes = brief([], reading("Concor 5 mg", st(mg("atorvastatin", 20))), "Nothing else to add.")
    assert all("ATC " not in box.text() for box in boxes.values()) and WHO not in html


def test_a_pack_whose_reading_agrees_keeps_its_codes():
    html, report, boxes = brief([], reading("Concor 5 mg", st(mg("bisoprolol", 5))), "Nothing else to add.")
    assert any("ATC C07AB07" in box.text() for box in boxes.values()) and html.count(WHO) == 1
