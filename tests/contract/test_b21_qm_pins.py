"""Batch 21 contract, part 1, written before the real media arrive: the quality manager's M4 round-2 items and the
supervisor's batch 19.1 pins (evidence/grills/m4-muse-brief/effect.md, evidence/batches/19.1/supervisor.md). Written by
the CEO; Muse must not edit it. Part 2 comes from the real photos and voice notes.

SPEC §2: ASCII, Arabic-Indic and extended Arabic-Indic digits are the only digits, for parse_amount_text and
stated_amounts alike, and the Arabic thousands sign joins a run like a comma (QM M4 code round 2 #2).
SPEC §3: the formulation question asks about the salt or the release form (#4).
SPEC §7: a salt named only in the free text shows on both sides (#1); the Ingredient rows are escaped and marked
dir="auto" (supervisor 19.1 round 2, #1 and #2).
"""

import json
from decimal import Decimal
from itertools import pairwise

import pytest

from anamnesis.brief import render_brief
from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.numbers import parse_amount_text
from anamnesis.providers.stated import stated_amounts
from anamnesis.schema import AudioTurn
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.templates import FIELD_INN, PATIENT_QUESTIONS, QUESTION_FOR
from tests.contract.test_b19_brief import CAT, PHOTO, RC, Page, claim, intake, mg, reading, st
from tests.contract.test_b20_stated_amounts import amount
from tests.contract.test_b20_stated_amounts import claim as raw_claim

FORMULATION_QUESTION = "What salt or release form is shown on your medicine pack?"
VOICE = (b"wav", "audio/wav")


def brief_of(said, read, transcript):
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=3000, transcript=transcript)]
    report = intake(VOICE[0], [(PHOTO, "image/png")], turns=turns, claims=[said], by_sha={RC.image_sha256: [RC]},
                    reads={RC.region_id: [read]})
    [finding] = report.findings
    page = Page(render_brief(report, [(PHOTO, "image/png")], VOICE, CAT)).root
    return finding, page, page.by_id(f"finding:{finding.finding_id}")


# --- SPEC §2: three digit sets, wherever numbers are read ----------------------------------------------------

@pytest.mark.parametrize("text,value", [
    ("۵", "5"), ("۱۰۰", "100"), ("۲٫۵", "2.5"), ("۰٫۱۲۵", "0.125"),   # extended Arabic-Indic, U+06F0–U+06F9
    ("٥", "5"), ("٢٫٥", "2.5"), ("2,5", "2.5"), ("100", "100"),
])
def test_the_three_digit_sets_parse(text, value):
    assert parse_amount_text(text) == Decimal(value)


@pytest.mark.parametrize("text", ["５", "２.５", "५", "৫", "۱٬۰۰۰", "۱٫۰۰۰"])
def test_other_digits_and_ambiguous_numbers_do_not_parse(text):
    assert parse_amount_text(text) is None


@pytest.mark.parametrize("text,value", [
    ("كونكور ۵ ملغ", "5"), ("۲٫۵ ملي", "2.5"), ("Concor ۱۰ mg", "10"), ("۵۰ مجم", "50"),
])
def test_extended_arabic_indic_digits_are_stated(text, value):
    assert Decimal(value) in stated_amounts(text)


@pytest.mark.parametrize("text", ["５ mg", "५ mg", "١٬٠٠٠ ملغ", "۱٬۰۰۰ ملغ", "٢٬٥ ملغ"])
def test_other_digits_and_the_thousands_sign_state_nothing(text):
    assert stated_amounts(text) == frozenset()


def test_a_dose_said_in_extended_arabic_indic_digits_is_kept():
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=3000, transcript="كونكور ۵ ملغ مرة في اليوم")]
    reply = raw_claim("كونكور", intake_amount=amount("5"))
    [found] = parse_claims_json(json.dumps({"claims": [reply]}), turns)
    assert found.intake_amount is not None and found.intake_amount.amount == Decimal("5")


# --- SPEC §3: the formulation question names both causes -----------------------------------------------------

def test_the_formulation_question_asks_about_the_salt_or_the_release_form():
    assert QUESTION_FOR[D.FORMULATION_MISMATCH] == "formulation"
    assert PATIENT_QUESTIONS["formulation"] == FORMULATION_QUESTION


def test_a_salt_only_mismatch_asks_the_salt_or_release_question():
    said = claim("c1", "Metoprolol tartrate", ["turn-0"], strength=st(mg("metoprolol", 100)))
    read = reading("Metoprolol succinate 100 mg", st(mg("metoprolol", 100)))
    finding, _, node = brief_of(said, read, "Metoprolol tartrate 100 mg.")
    assert finding.type is D.FORMULATION_MISMATCH and finding.patient_question_id == "formulation"
    assert FORMULATION_QUESTION in node.text()


# --- SPEC §7: the brief shows every salt, and its Ingredient rows are escaped and marked dir="auto" ---------

def test_a_salt_named_only_in_the_free_text_shows_on_both_sides():
    said = claim("c1", "Metoprolol tartrate", ["turn-0"], strength=st(mg("metoprolol", 100)))
    read = reading("Metoprolol succinate 100 mg", st(mg("metoprolol", 100)))
    finding, _, node = brief_of(said, read, "Metoprolol tartrate 100 mg.")
    assert finding.type is D.FORMULATION_MISMATCH
    patient = node.find_all(data_side="patient")[0].text()
    pack = node.find_all(data_side="pack")[0].text()
    assert "tartrate" in patient and "succinate" not in patient
    assert "succinate" in pack and "tartrate" not in pack


HOSTILE = 'metoprolol <x data-side="pack">tartrate</x> & "co"'


def field_rows(node):
    """(label, dd) for every dt/dd pair under node, in page order."""
    cells = [n for n in node.walk() if n.tag in ("dt", "dd")]
    return [(dt.text(), dd) for dt, dd in pairwise(cells) if dt.tag == "dt" and dd.tag == "dd"]


def test_the_ingredient_rows_are_escaped_and_marked_dir_auto():
    said = claim("c1", "Metoprolol", ["turn-0"], strength=st(mg("metoprolol", 100)))
    said = said.model_copy(update={"inn": HOSTILE})
    read = reading("Beloc-Zok 100 mg", st(mg("metoprolol", 100), release="modified"))
    read = read.model_copy(update={"inn": HOSTILE})
    _, page, node = brief_of(said, read, "Metoprolol 100.")
    assert page.find_all("x") == []
    for side in ("patient", "pack"):
        [box] = node.find_all(data_side=side)
        rows = [dd for label, dd in field_rows(box) if label == FIELD_INN]
        assert len(rows) == 1, side
        assert rows[0].attrs.get("dir") == "auto", side
        assert rows[0].text() == HOSTILE, side
