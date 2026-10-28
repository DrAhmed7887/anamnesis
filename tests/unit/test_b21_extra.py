"""Focused checks for the batch 21 real-media fixes (SPEC 2, 3, 7)."""

from decimal import Decimal

from anamnesis.brief_html import _ingredient_html
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all
from anamnesis.providers.claims import _SYSTEM_PROMPT as CLAIM_PROMPT
from anamnesis.providers.meta import _SYSTEM_PROMPT as LABEL_PROMPT
from anamnesis.providers.numbers import parse_amount_text
from anamnesis.providers.stated import _hundred_cut, stated_amounts
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import IngredientAmount, PackObservation, PatientClaim, Strength
from anamnesis.schema.medication import canonical_inn, salt_of
from anamnesis.schema.templates import PATIENT_QUESTIONS

CAT = load_catalogue()

# Confusable digit glyphs below use codepoints, not literals: Arabic-Indic
# 0 is 1632, extended 0 is 1776, the decimal sign is 1643, thousands 1644.


def test_extended_digits_parse_and_foreign_digits_do_not():
    assert parse_amount_text(chr(1781)) == Decimal(5)
    assert parse_amount_text(chr(65297)) is None
    assert parse_amount_text(chr(2411)) is None


def test_extended_decimal_parses_and_thousands_stays_ambiguous():
    assert parse_amount_text(chr(1778) + chr(1643) + chr(1781)) == Decimal("2.5")
    assert parse_amount_text(chr(1777) + chr(1643) + chr(1776) * 3) is None


def test_extended_digits_are_stated_and_thousands_states_nothing():
    assert Decimal(10) in stated_amounts("Concor " + chr(1777) + chr(1776) + " mg")
    assert stated_amounts(chr(1633) + chr(1644) + chr(1632) * 3) == frozenset()


def test_the_formulation_question_names_the_salt_or_the_release():
    assert PATIENT_QUESTIONS["formulation"] == "What salt or release form is shown on your medicine pack?"


def test_a_second_hundreds_group_starts_a_new_number():
    found = stated_amounts("five hundred and two hundred")
    assert Decimal(500) in found and Decimal(200) in found
    assert Decimal(50200) not in found


def test_one_hundreds_group_stays_one_number():
    assert Decimal(250) in stated_amounts("two hundred and fifty")


def test_an_ingredient_amount_is_isolated_left_to_right():
    part = IngredientAmount(inn="bisoprolol", amount=Decimal(5), unit="mg")
    assert _ingredient_html(part) == 'bisoprolol <bdi dir="ltr">5 mg</bdi>'


def test_the_prompts_ask_for_digits_and_full_label_text():
    assert "as digits, even when the patient said it in words" in CLAIM_PROMPT
    assert "including every amount you report" in LABEL_PROMPT
    assert "English INN" in LABEL_PROMPT


def test_plain_foreign_aliases_resolve():
    assert canonical_inn("amoxicilline") == "amoxicillin"
    assert salt_of("metoprololi succinas") == "succinate"


def _pack(oid, amount):
    strength = Strength(
        ingredients=[IngredientAmount(inn="amlodipine", amount=Decimal(amount), unit="mg")],
        per="tablet",
        release="immediate",
    )
    return PackObservation(
        observation_id=oid,
        label_text="Norvasc " + str(amount) + " mg Tablets",
        inn="amlodipine",
        strength=strength,
        readability="readable",
        visual_evidence=["r" + oid],
    )


def test_an_intake_only_claim_pairs_with_its_strength_first():
    said = PatientClaim(
        claim_id="c1",
        name_text="Norvasc",
        intake_amount=IngredientAmount(inn="Norvasc", amount=Decimal(5), unit="mg"),
        status="active",
        audio_evidence=["turn-0"],
    )
    for order in (("o0", "o1"), ("o1", "o0")):
        packs = {"o0": _pack("o0", 10), "o1": _pack("o1", 5)}
        findings = reconcile_all([said], [packs[oid] for oid in order], CAT)
        by_pair = {(f.claim_id, f.observation_id): f.type for f in findings}
        assert by_pair[("c1", "o1")] is D.MATCH
        assert by_pair[(None, "o0")] is D.MISSING_MODALITY


def test_hundred_cut_moves_a_final_units_word():
    words = [("plain", 8), ("hundred", 100), ("plain", 70), ("plain", 5), ("plain", 1)]
    assert _hundred_cut(words, "hundred") == len(words) - 1
    assert _hundred_cut([("plain", 500), ("plain", 3)], "مية") == 1


def test_hundred_cut_moves_nothing_with_waw_or_without_units():
    words = [("plain", 800), ("plain", 5), ("plain", 70)]
    assert _hundred_cut(words, "وميه") == len(words)
    assert _hundred_cut([("plain", 500), ("plain", 20)], "hundred") == 2
    assert _hundred_cut([("plain", 500)], "مية") == 1
    assert _hundred_cut([("plain", 5), ("hundred", 100)], "hundred") == 2
    assert _hundred_cut([], "hundred") == 0


def test_alfain_closes_the_thousands_part():
    assert Decimal(2500) in stated_amounts("ألفين وخمسمية")
    assert Decimal(2200) in stated_amounts("ألفين و ميتين")
    found = stated_amounts("ألفين ومية")
    assert Decimal(2100) in found
    assert Decimal(200000) not in found
    found = stated_amounts("ألفين وخمسمية وخمسين")
    assert Decimal(2550) in found
    assert Decimal(550) not in found


def test_nothing_moves_after_the_filler_a():
    found = stated_amounts("eight hundred seventy-five and a hundred twenty-five")
    assert Decimal(875) in found and Decimal(125) in found
    assert Decimal(870) not in found and Decimal(525) not in found
    found = stated_amounts("one hundred twenty-five and a hundred")
    assert Decimal(125) in found and Decimal(100) in found
    assert Decimal(120) not in found
