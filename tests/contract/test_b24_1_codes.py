"""Batch 24.1: ATC and RxNorm codes in the catalogue and the brief, Emconcor, Sortis and Nolotil, and no SNOMED CT
in the product (SPEC §3 "Catalogue resolution", §7 "Catalogue codes"). The codes are those of
evidence/data/drugs_v2.json (AEMPS CIMA and NLM RxNav, read 29 Oct)."""

import json
from pathlib import Path

import pytest

from anamnesis.brief import render_brief
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all
from anamnesis.schema import AudioTurn, PackObservation, Release
from anamnesis.schema import DiscrepancyType as D
from tests.contract.test_b19_brief import (
    PHOTO,
    RC,
    Page,
    claim,
    intake,
    mg,
    reading,
    st,
)

ROOT = Path(__file__).resolve().parents[2]
CAT = load_catalogue()
VOICE = (b"wav", "audio/wav")
WHO = "WHO Collaborating Centre for Drug Statistics Methodology"


def entry(name):
    found = CAT.resolve(name)
    assert found is not None, name
    return found


# --- SPEC §3: the codes and the new entries --------------------------------------------------------------------

@pytest.mark.parametrize(("name", "atc", "rxcui"), [
    ("Concor", "C07AB07", ("19484",)),
    ("Panadol Extra", "N02BE51", ("161", "1886")),
    ("Augmentin", "J01CR02", ("723", "48203")),
    ("Emconcor", "C07AB07", ("19484",)),   # bisoprolol's codes
    ("Sortis", "C10AA05", ("83367",)),     # atorvastatin's codes
    ("Nolotil", "N02BB02", ("3523",)),     # CIMA 47633; RxNorm "dipyrone", metamizole's US name
])
def test_an_entry_carries_its_codes(name, atc, rxcui):
    found = entry(name)
    assert (found.atc, found.rxcui) == (atc, rxcui)


def test_the_first_nine_entries_carry_drugs_v2s_codes():
    data = json.loads((ROOT / "evidence/data/drugs_v2.json").read_text(encoding="utf-8"))
    for row in data["catalogue"]:
        found = entry(row["brand"])
        assert (found.atc, found.rxcui) == (row["atc"]["code"], tuple(row["rxcui"])), row["brand"]


@pytest.mark.parametrize(("name", "inn", "splittable", "countries"), [
    ("Emconcor 5 mg", "bisoprolol", True, ("ES",)),
    ("Sortis 40 mg", "atorvastatin", False, ("DE",)),
    ("Nolotil 575 mg", "metamizole", False, ("ES",)),
])
def test_the_new_entries(name, inn, splittable, countries):
    found = entry(name)
    assert found.inns == frozenset({inn})
    assert (found.release, found.splittable, found.countries) == (Release.IMMEDIATE, splittable, countries)


def test_no_snomed_ct_in_the_catalogue():
    text = (ROOT / "anamnesis/core/catalogue.yaml").read_text(encoding="utf-8").casefold()
    assert "snomed" not in text and "vtm" not in text and "[SNOMED CT id removed]" not in text


def test_the_live_cases_s1_and_g3_resolve_after_this_batch():
    s1 = claim("c1", "Emconcor", intake=mg("Emconcor", 5), per_day=1)
    [found] = reconcile_all([s1], [], CAT)
    assert found.type is D.MISSING_MODALITY
    g3 = claim("c1", "Sortis", intake=mg("Sortis", 40))
    pack = PackObservation(observation_id="o1", label_text="Sortis 40 mg", readability="readable",
                           visual_evidence=["r_o1"], strength=st(mg("atorvastatin", 40)))
    [found] = reconcile_all([g3], [pack], CAT)
    assert found.type is D.MATCH


# --- SPEC §7: the codes in the brief ---------------------------------------------------------------------------

def brief(said, read, transcript):
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=3000, transcript=transcript)]
    report = intake(VOICE[0], [(PHOTO, "image/png")], turns=turns, claims=[said], by_sha={RC.image_sha256: [RC]},
                    reads={RC.region_id: [read, read]})  # a second reading for a zoom
    html = render_brief(report, [(PHOTO, "image/png")], VOICE, CAT)
    page = Page(html).root
    boxes = [page.by_id(f"finding:{finding.finding_id}") for finding in report.findings]
    return html, page, boxes


def test_a_resolved_medicine_shows_its_codes_once_with_the_reference():
    html, page, [box] = brief(claim("c1", "Concor", ["turn-0"], intake=mg("bisoprolol", 5)),
                              reading("Concor 5 mg", st(mg("bisoprolol", 5))), "Concor 5 mg every morning")
    assert "ATC C07AB07" in box.text() and "RxNorm 19484" in box.text()
    assert html.count(WHO) == 1 and "RxNav" in page.text()  # NLM asks apps not to use its name (NOTICE)


def test_a_combination_lists_each_rxcui():
    _, _, [box] = brief(claim("c1", "Panadol Extra", ["turn-0"]),
                        reading("Panadol Extra", st(mg("paracetamol", 500), mg("caffeine", 65))),
                        "Panadol Extra")
    assert "ATC N02BE51" in box.text() and "RxNorm 161, 1886" in box.text()


def test_a_claim_without_a_readable_pack_still_shows_its_codes():
    _, _, boxes = brief(claim("c1", "Nolotil", ["turn-0"], intake=mg("Nolotil", 575)),
                        reading(None, None, readability="unreadable"), "Nolotil 575 mg")
    assert "ATC N02BB02 · RxNorm 3523" in " ".join(box.text() for box in boxes)


def test_no_code_and_no_reference_for_an_unknown_name():
    html, _, boxes = brief(claim("c1", "Zorvex", ["turn-0"], intake=mg("Zorvex", 5)),
                           reading(None, None, readability="unreadable"), "Zorvex 5 mg")
    assert "ATC " not in " ".join(box.text() for box in boxes) and WHO not in html


def test_no_snomed_ct_in_the_brief():
    html, _, _ = brief(claim("c1", "Concor", ["turn-0"], intake=mg("bisoprolol", 5)),
                       reading("Concor 5 mg", st(mg("bisoprolol", 5))), "Concor 5 mg")
    assert "[SNOMED CT id removed]" not in html and "snomed" not in html.casefold()


def test_the_notice_credits_the_three_sources():
    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    assert WHO in notice and "National Library of Medicine" in notice and "AEMPS" in notice
