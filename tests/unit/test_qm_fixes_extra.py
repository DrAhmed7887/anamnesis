"""Focused checks for the batch 19.1 quality-manager fixes (SPEC §2, §3, §7)."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

import anamnesis.schema.templates as templates
from anamnesis.brief_html import _photos_html, _strength_html
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.guardrails import AdviceLeak, assert_no_advice
from anamnesis.core.overlap import OverlapKind, cross_medication
from anamnesis.core.reconcile import reconcile_all, reconcile_pair
from anamnesis.providers.numbers import parse_amount_text
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import (
    IngredientAmount,
    PackObservation,
    PatientClaim,
    Strength,
)
from anamnesis.schema.templates import SCOPE_LINES, TEMPLATES

CAT = load_catalogue()


def mg(inn, amount, **kw):
    return IngredientAmount(inn=inn, amount=Decimal(str(amount)), unit="mg", **kw)


def st(*parts, release="unknown"):
    return Strength(ingredients=list(parts), per="tablet", release=release)


def claim(cid, name, **kw):
    return PatientClaim(claim_id=cid, name_text=name, status="active",
                        audio_evidence=[f"turn-{cid}"], **kw)


def test_arabic_decimal_sign_follows_the_dot_rules():
    assert parse_amount_text("12٫34") == Decimal("12.34")
    assert parse_amount_text("12٫000") is None  # thousands-like, as with a dot


@pytest.mark.parametrize("text", ["1٬0", "١٬٢", "٫"])
def test_arabic_thousands_sign_never_parses(text):
    assert parse_amount_text(text) is None


@pytest.mark.parametrize("text", ["للضاعف", "الخذ", "يَجِب", "double the dose"])
def test_advice_words_caught_with_clitics_marks_and_english(text):
    with pytest.raises(AdviceLeak):
        assert_no_advice(text)


@pytest.mark.parametrize("text", ["الكونكور", "صيدلية النور", "جرعة يومية", "Vancomycin"])
def test_nearby_names_still_pass(text):
    assert_no_advice(text)


BELOC = PackObservation(observation_id="o0", label_text="Beloc-Zok 100 mg", readability="readable",
                        strength=st(mg("metoprolol succinate", 100), release="modified"),
                        visual_evidence=["r-0"])


def test_another_clitic_feminine_release_word_counts_as_said():
    stated = claim("c1", "ميتوبرولول بالممتدة", strength=st(mg("metoprolol", 100), release="modified"))
    assert reconcile_pair(stated, BELOC, CAT).type is D.MATCH


def test_a_near_matching_word_does_not_count_as_said():
    # "ممتاز" (excellent) is not a release word, so the agreeing release falls back to unknown.
    stated = claim("c1", "ميتوبرولول ممتاز", strength=st(mg("metoprolol", 100), release="modified"))
    assert reconcile_pair(stated, BELOC, CAT).type is D.INSUFFICIENT_INFORMATION


def test_salt_only_mismatch_carries_the_new_note():
    said = claim("c1", "Metoprolol", strength=st(mg("metoprolol tartrate", 100)))
    finding = reconcile_pair(said, BELOC, CAT)
    assert finding.type is D.FORMULATION_MISMATCH
    assert finding.clinician_note == "Reported and pack formulations differ (salt or release form)."
    assert TEMPLATES[D.FORMULATION_MISMATCH] == finding.clinician_note


def test_scope_lines_have_the_across_medicines_line_fourth():
    assert len(SCOPE_LINES) == 4
    assert SCOPE_LINES[3] == ("Checks across medicines cover shared ingredients and one curated class "
                              "(beta-blockers); interactions were not assessed.")


def test_conflicted_claim_is_skipped_while_clean_claims_still_pair():
    two = claim("c1", "Concor Beloc-Zok", strength=st(mg("bisoprolol", 5)))
    found = cross_medication([two, claim("c2", "Concor"), claim("c3", "Beloc-Zok")], CAT)
    assert [(o.kind, o.key, o.claim_ids) for o in found] == [
        (OverlapKind.SAME_CLASS, "beta-blockers", ("c2", "c3"))]


def test_strength_row_shows_each_salt_after_its_inn():
    assert (
        _strength_html(st(mg("metoprolol tartrate", 100)))
        == 'metoprolol tartrate <bdi dir="ltr">100 mg</bdi> per tablet'
    )


def test_saltless_strength_row_is_unchanged():
    assert _strength_html(st(mg("bisoprolol", 5))) == 'bisoprolol <bdi dir="ltr">5 mg</bdi> per tablet'


def test_a_hostile_salt_is_escaped():
    html = _strength_html(st(mg("metoprolol", 100, salt="<tartrate>")))
    assert "<tartrate>" not in html and "&lt;tartrate&gt;" in html


def test_region_without_photo_is_refused():
    stray = SimpleNamespace(region_id="nope-9", image_sha256="f" * 64)
    report = SimpleNamespace(regions=[stray], observations=[])
    with pytest.raises(ValueError):
        _photos_html(report, [])


def test_pairing_docstring_names_same_brand_first_and_no_field_evidence():
    assert "same brand first" in reconcile_all.__doc__
    assert not hasattr(templates, "FIELD_EVIDENCE")
