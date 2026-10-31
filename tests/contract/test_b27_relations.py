"""Batch 27 contract: the relation checks on claim amounts (SPEC §2, "Relation checks (batch 27)"), from the 31 Oct
relation audit's ten traps (evidence/audits/relation-provenance/). Every transcript here is invented.
Written by the CEO; Muse must not edit it."""

import json
from decimal import Decimal

import pytest

from anamnesis.providers.claims import parse_claims_json
from anamnesis.schema import AudioTurn
from anamnesis.schema import DiscrepancyType as D
from tests.contract.test_b19_brief import AUDIO, PHOTO, RC, intake, mg, reading, st


def turns(*texts):
    return [AudioTurn(turn_id=f"turn-{i}", start_ms=4000 * i, end_ms=4000 * i + 3500, transcript=text)
            for i, text in enumerate(texts)]


def claim(name, *, intake_amount=None, strength=None, units=None, per_day=None, status="active", inn=None,
          turn_ids=("turn-0",)):
    return {"name_text": name, "inn": inn, "strength": strength, "intake_amount": intake_amount,
            "regimen": {"units_per_intake": units, "intakes_per_day": per_day, "as_needed": None},
            "status": status, "turn_ids": list(turn_ids)}


def amt(label, value, unit="mg"):
    return {"inn": label, "amount": str(value), "unit": unit}


def per_tablet(*parts):
    return {"ingredients": list(parts), "per": "tablet", "release": "unknown"}


def parse(texts, *claims):
    texts = texts if isinstance(texts, tuple) else (texts,)
    return parse_claims_json(json.dumps({"claims": list(claims)}, ensure_ascii=False), turns(*texts))


def intake_of(texts, *claims, index=0):
    """The intake amount the checks keep for one claim, or None."""
    kept = parse(texts, *claims)[index].intake_amount
    return None if kept is None else kept.amount


def strengths_of(texts, *claims, index=0):
    kept = parse(texts, *claims)[index].strength
    return None if kept is None else [part.amount for part in kept.ingredients]


# --- the audit's ten traps: the careful listener's reply is kept, the wrong one is not ----------------------------

TRAPS = {
    "A negated": ("I take Concor ten milligrams in the morning, not five.", "10", "5"),
    "B past": ("I used to take Concor ten milligrams. Now I take five milligrams once a day.", "5", "10"),
    "H negated, Arabic": ("باخد كونكور عشرة مجم الصبح، مش خمسة.", "10", "5"),
}


@pytest.mark.parametrize("case", TRAPS)
def test_a_trap_keeps_the_right_amount_and_drops_the_wrong_one(case):
    said, right, wrong = TRAPS[case]
    name = "كونكور" if case.startswith("H") else "Concor"
    assert intake_of(said, claim(name, intake_amount=amt("bisoprolol", right))) == Decimal(right)
    assert intake_of(said, claim(name, intake_amount=amt("bisoprolol", wrong))) is None


def test_c_another_medicines_amount_in_the_same_turn_is_not_concors():
    said = "I take Concor every morning and Panadol five hundred milligrams when I need it."
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 500))) is None
    both = [claim("Concor"), claim("Panadol", intake_amount=amt("paracetamol", 500))]
    assert intake_of(said, *both, index=1) == Decimal(500)


def test_d_a_tablet_count_is_never_milligrams_and_stays_a_count():
    said = "I take two Panadol tablets when I have a headache."
    assert intake_of(said, claim("Panadol", intake_amount=amt("paracetamol", 2))) is None
    kept = parse(said, claim("Panadol", units="2"))[0]
    assert kept.regimen is not None and kept.regimen.units_per_intake == Decimal(2)


def test_e_a_combination_said_whole_keeps_both_parts():
    said = "I take Augmentin, eight hundred seventy-five and one hundred twenty-five milligrams, twice a day."
    strength = per_tablet(amt("amoxicillin", 875), amt("clavulanic acid", 125))
    assert strengths_of(said, claim("Augmentin", strength=strength)) == [Decimal(875), Decimal(125)]


def test_f_another_medicines_amount_in_another_cited_turn_is_not_concors():
    said = ("I take Concor.", "And Panadol, five hundred milligrams.")
    wrong = claim("Concor", intake_amount=amt("bisoprolol", 500), turn_ids=("turn-0", "turn-1"))
    assert intake_of(said, wrong) is None


def test_g_a_stopped_medicine_keeps_its_past_amount():
    said = "I used to take Concor ten milligrams, I stopped it last month."
    kept = claim("Concor", intake_amount=amt("bisoprolol", 10), status="discontinued")
    assert intake_of(said, kept) == Decimal(10)


def test_i_micrograms_ground_micrograms_not_milligrams():
    said = "I take Concor five micrograms every morning."
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 5, "mcg"))) == Decimal(5)
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 5))) is None


def test_j_a_split_daily_total_is_not_one_intake():
    said = "I take Concor ten milligrams a day, five in the morning and five at night."
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 5), per_day="2")) == Decimal(5)
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 10))) is None


# --- the false matches no longer reach the brief -------------------------------------------------------------------

CONCOR_5 = ("Concor 5 mg\nBisoprolol fumarate", st(mg("bisoprolol", 5)))
FALSE_MATCHES = {
    "A": ("I take Concor ten milligrams in the morning, not five.", "Concor", amt("bisoprolol", 5)),
    "H": ("باخد كونكور عشرة مجم الصبح، مش خمسة.", "كونكور", amt("bisoprolol", 5)),
    "I": ("I take Concor five micrograms every morning.", "Concor", amt("bisoprolol", 5)),
}


@pytest.mark.parametrize("case", FALSE_MATCHES)
def test_a_wrong_reply_that_was_a_false_match_now_fails_safe(case):
    said, name, wrong = FALSE_MATCHES[case]
    claims = parse(said, claim(name, intake_amount=wrong))
    label, strength = CONCOR_5
    report = intake(AUDIO[0], [(PHOTO, "image/png")], turns=turns(said), claims=claims,
                    by_sha={RC.image_sha256: [RC]}, reads={RC.region_id: [reading(label=label, strength=strength)] * 4})
    types = {finding.type for finding in report.findings}
    assert D.MATCH not in types
    assert D.INSUFFICIENT_INFORMATION in types


# --- 1. negation ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("said", [
    "I never miss my Concor five milligrams.",
    "No, I take Concor five milligrams.",
    "I'm not sure of the time, I take Concor five milligrams.",
])
def test_a_negation_further_away_or_in_another_clause_keeps_the_amount(said):
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 5))) == Decimal(5)


@pytest.mark.parametrize("said, dropped, kept", [
    ("With Concor I don't take ten milligrams, I take five.", "10", "5"),
    ("tomo Concor diez miligramos, no cinco miligramos", "5", "10"),
    ("Ich nehme Concor zehn Milligramm, nicht fünf Milligramm.", "5", "10"),
])
def test_a_negated_amount_is_dropped_in_each_language(said, dropped, kept):
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", dropped))) is None
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", kept))) == Decimal(kept)


def test_a_negated_strength_is_dropped_and_takes_the_intake_with_it():
    said = "I take Concor five milligrams, the five milligram tablets, not the ten."
    kept = parse(said, claim("Concor", strength=per_tablet(amt("bisoprolol", 10)),
                             intake_amount=amt("bisoprolol", 5)))[0]
    assert kept.strength is None and kept.intake_amount is None
    assert strengths_of(said, claim("Concor", strength=per_tablet(amt("bisoprolol", 5)))) == [Decimal(5)]


# --- 2. units -------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("said", [
    "باخد كونكور عشرة مليجرام الصبح",
    "باخد كونكور عشرة ملليجرام الصبح",
    "باخد كونكور عشرة ملي جرام الصبح",
    "باخد كونكور ١٠ مجم الصبح",
])
def test_arabic_milligram_words_ground_milligrams(said):
    assert intake_of(said, claim("كونكور", intake_amount=amt("bisoprolol", 10))) == Decimal(10)
    assert intake_of(said, claim("كونكور", intake_amount=amt("bisoprolol", 10, "mcg"))) is None


@pytest.mark.parametrize("said, name, value, unit, wrong", [
    ("I take Eltroxin fifty micrograms every morning.", "Eltroxin", "50", "mcg", "mg"),
    ("Farxiga ein Gramm", "Farxiga", "1", "g", "mg"),
])
def test_units_hold_for_a_medicine_outside_the_catalogue(said, name, value, unit, wrong):
    assert intake_of(said, claim(name, intake_amount=amt(name, value, unit))) == Decimal(value)
    assert intake_of(said, claim(name, intake_amount=amt(name, value, wrong))) is None


def test_mili_alone_leaves_the_unit_open():
    said = "باخد كونكور خمسة ملي"
    assert intake_of(said, claim("كونكور", intake_amount=amt("bisoprolol", 5))) == Decimal(5)
    assert intake_of(said, claim("كونكور", intake_amount=amt("bisoprolol", 5, "ml"))) == Decimal(5)


def test_a_gram_grounds_grams_only():
    said = "tomo Gelocatil de un gramo cuando tengo dolor"
    assert intake_of(said, claim("Gelocatil", intake_amount=amt("paracetamol", 1, "g"))) == Decimal(1)
    assert intake_of(said, claim("Gelocatil", intake_amount=amt("paracetamol", 1))) is None


def test_a_strength_said_with_its_unit_before_the_tablet_word_is_kept():
    said = "I have كونكور, the 10 ملليجرام tablets, حباية واحدة one time a day."
    kept = claim("كونكور", strength=per_tablet(amt("bisoprolol", 10)))
    assert strengths_of(said, kept) == [Decimal(10)]


# --- 3. counts ------------------------------------------------------------------------------------------------------

def test_an_amount_beside_a_count_keeps_the_amount_and_drops_the_count():
    said = "I take Panadol five hundred milligrams, two tablets at a time."
    assert intake_of(said, claim("Panadol", intake_amount=amt("paracetamol", 500), units="2")) == Decimal(500)
    assert intake_of(said, claim("Panadol", intake_amount=amt("paracetamol", 2))) is None


def test_a_count_after_the_pill_word_is_a_count():
    said = "باخد بنادول حباية واحدة لما اتعب"
    assert intake_of(said, claim("بنادول", intake_amount=amt("paracetamol", 1))) is None


@pytest.mark.parametrize("said", ["tomo medio comprimido de Panadol de quinientos miligramos",
                                  "Ich nehme eine halbe Tablette Panadol fünfhundert Milligramm"])
def test_a_half_tablet_is_a_count_and_the_amount_stays(said):
    assert intake_of(said, claim("Panadol", intake_amount=amt("paracetamol", 500))) == Decimal(500)
    assert intake_of(said, claim("Panadol", intake_amount=amt("paracetamol", "0.5"))) is None


# --- 4. another medicine's ---------------------------------------------------------------------------------------------

HERO = "I take Concor 10 milligrams every morning and BelocZok 50 milligrams twice a day"


def test_two_medicines_in_one_turn_each_keep_their_own_amount():
    both = [claim("Concor", intake_amount=amt("bisoprolol", 10)),
            claim("BelocZok", intake_amount=amt("metoprolol", 50), per_day="2")]
    assert intake_of(HERO, *both, index=0) == Decimal(10)
    assert intake_of(HERO, *both, index=1) == Decimal(50)
    swapped = [claim("Concor", intake_amount=amt("bisoprolol", 50)), both[1]]
    assert intake_of(HERO, *swapped, index=0) is None


def test_two_medicines_in_one_arabic_turn_each_keep_their_own_amount():
    said = "انا باخد كونكور خمسة ملي جرام مرة في اليوم وباخد بيلوك زوك خمسين ملي جرام مرتين في اليوم"
    both = [claim("كونكور", intake_amount=amt("bisoprolol", 5)),
            claim("بيلوك زوك", intake_amount=amt("metoprolol", 50))]
    assert intake_of(said, *both, index=0) == Decimal(5)
    assert intake_of(said, *both, index=1) == Decimal(50)
    assert intake_of(said, claim("كونكور", intake_amount=amt("bisoprolol", 50)), both[1]) is None


def test_an_amount_before_of_and_another_name_is_that_medicines():
    said = "I take five hundred milligrams of Panadol and Concor ten milligrams."
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 10))) == Decimal(10)
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 500))) is None
    assert intake_of(said, claim("Panadol", intake_amount=amt("paracetamol", 500))) == Decimal(500)


def test_a_name_from_another_claim_counts_even_outside_the_catalogue():
    said = "I take Concor and Zyloric three hundred milligrams."
    both = [claim("Concor", intake_amount=amt("bisoprolol", 300)),
            claim("Zyloric", intake_amount=amt("allopurinol", 300))]
    assert intake_of(said, *both, index=0) is None
    assert intake_of(said, *both, index=1) == Decimal(300)


def test_the_claims_own_ingredient_is_never_another_medicine():
    said = "I take Amoxil, that's amoxicillin, five hundred milligrams."
    kept = claim("Amoxil", intake_amount=amt("amoxicillin", 500), inn="amoxicillin")
    assert intake_of(said, kept) == Decimal(500)


def test_an_amount_label_alone_doesnt_make_a_name_the_claims_own():
    said = "I take Amoxil, that's amoxicillin, five hundred milligrams."
    assert intake_of(said, claim("Amoxil", intake_amount=amt("amoxicillin", 500))) is None
    wrong = claim("Concor", intake_amount=amt("paracetamol", 500))
    assert intake_of("I take Concor and paracetamol five hundred milligrams.", wrong) is None


def test_the_longer_name_wins():
    said = "I take Panadol Extra five hundred milligrams."
    assert intake_of(said, claim("Panadol Extra", intake_amount=amt("paracetamol", 500))) == Decimal(500)
    assert intake_of(said, claim("Panadol", intake_amount=amt("paracetamol", 500))) is None


# --- 5. past --------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("said", [
    "I used to take Concor ten milligrams but now I take five milligrams",
    "كنت باخد كونكور عشرة، دلوقتي باخد خمسة",
    "antes tomaba Concor diez miligramos, ahora tomo cinco miligramos",
])
def test_a_past_amount_is_not_the_current_one(said):
    name = "كونكور" if "كونكور" in said else "Concor"
    assert intake_of(said, claim(name, intake_amount=amt("bisoprolol", 5))) == Decimal(5)
    assert intake_of(said, claim(name, intake_amount=amt("bisoprolol", 10))) is None


def test_before_a_meal_is_not_the_past():
    said = "I take Concor five milligrams before breakfast."
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 5))) == Decimal(5)


# --- 6. a split daily total -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("said, value", [
    ("I take Concor ten milligrams a day.", "10"),
    ("I take Concor ten milligrams a day and Norvasc five milligrams at night.", "10"),
    ("I take Zyloric two hundred milligrams a day.", "200"),
    ("I take Concor ten milligrams twice a day, five in the morning.", "10"),
    ("باخد كونكور عشرة ملي جرام في اليوم", "10"),
])
def test_a_daily_amount_that_isnt_split_is_kept(said, value):
    name = "كونكور" if "كونكور" in said else ("Zyloric" if "Zyloric" in said else "Concor")
    assert intake_of(said, claim(name, intake_amount=amt("bisoprolol", value), per_day="1")) == Decimal(value)


def test_an_arabic_split_daily_total_is_not_one_intake():
    said = "باخد كونكور عشرة ملي جرام في اليوم، خمسة الصبح وخمسة بالليل"
    assert intake_of(said, claim("كونكور", intake_amount=amt("bisoprolol", 10))) is None
    assert intake_of(said, claim("كونكور", intake_amount=amt("bisoprolol", 5), per_day="2")) == Decimal(5)


# --- what doesn't change ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("said, name, field, value", [
    ("I take Concor five milligrams once a day.", "Concor", "intake", "5"),
    ("I take Panadol five hundred milligrams two tablets at a time", "Panadol", "intake", "500"),
    ("I take Glucophage 500 milligrams twice a day.", "Glucophage", "intake", "500"),
    ("I take BelocZok 100 milligrams once a day.", "BelocZok", "intake", "100"),
    ("tomo Bisoprolol dos coma cinco miligramos por la mañana", "Bisoprolol", "intake", "2.5"),
    ("Ich nehme Metoprolol fünfzig Milligramm zweimal täglich.", "Metoprolol", "intake", "50"),
    ("Ich nehme morgens eine halbe Tablette BelocZok hundert Milligramm", "BelocZok", "intake", "100"),
    ("I take Augmentin, 875 and 125 milligrams, twice a day.", "Augmentin", "strength", "875/125"),
])
def test_the_staged_cases_keep_their_amounts(said, name, field, value):
    if field == "intake":
        assert intake_of(said, claim(name, intake_amount=amt(name, value))) == Decimal(value)
    else:
        parts = [amt("amoxicillin", 875), amt("clavulanic acid", 125)]
        assert strengths_of(said, claim(name, strength=per_tablet(*parts))) == [Decimal(875), Decimal(125)]


def test_the_checks_never_ground_what_the_value_check_drops():
    said = "tomo Concor a las 8 de la mañana"
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 8))) is None


def test_an_unstated_amount_is_still_dropped_with_the_other():
    said = "I take Concor five milligrams."
    kept = parse(said, claim("Concor", intake_amount=amt("bisoprolol", 5),
                             strength=per_tablet(amt("bisoprolol", 10))))[0]
    assert kept.intake_amount is None and kept.strength is None


# --- round 3, from the Opus supervisor's review (31 Oct) -------------------------------------------------------

def test_ten_a_day_without_a_unit_is_a_daily_total():
    said = "I take Concor 10 a day, 5 in the morning and 5 at night."
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 10))) is None
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 5), per_day="2")) == Decimal(5)
    assert intake_of("I take Concor ten a day.", claim("Concor", intake_amount=amt("bisoprolol", 10),
                                                       per_day="1")) == Decimal(10)


def test_mili_alone_is_the_amounts_unit_word():
    split = "باخد كونكور عشرة ملي في اليوم، خمسة الصبح وخمسة بالليل"
    assert intake_of(split, claim("كونكور", intake_amount=amt("bisoprolol", 10))) is None
    assert intake_of(split, claim("كونكور", intake_amount=amt("bisoprolol", 5), per_day="2")) == Decimal(5)
    of_panadol = "باخد كونكور وخمسمية ملي من البنادول"
    assert intake_of(of_panadol, claim("كونكور", intake_amount=amt("bisoprolol", 500))) is None
    assert intake_of(of_panadol, claim("بنادول", intake_amount=amt("paracetamol", 500))) == Decimal(500)
    pill = "باخد حباية كونكور خمسة ملي"
    assert intake_of(pill, claim("كونكور", intake_amount=amt("bisoprolol", 5))) == Decimal(5)


def test_an_arabic_thousands_mark_leaves_no_stray_digit():
    # The value check states nothing for a thousands mark (as before); the relation checks must not read its
    # first digit as a mention of its own.
    assert intake_of("باخد كونكور مش واحد، ١٬٠٠٠", claim("كونكور", intake_amount=amt("bisoprolol", 1))) is None


@pytest.mark.parametrize("said, name, dropped, kept", [
    ("tomaba para la tensión Concor diez miligramos ahora tomo cinco miligramos", "Concor", "10", "5"),
    ("With Concor I used to take sort of ten milligrams but now I take five milligrams", "Concor", "10", "5"),
])
def test_ordinary_words_dont_pass_for_a_medicines_name(said, name, dropped, kept):
    assert intake_of(said, claim(name, intake_amount=amt("bisoprolol", dropped))) is None
    assert intake_of(said, claim(name, intake_amount=amt("bisoprolol", kept))) == Decimal(kept)


def test_acid_doesnt_block_a_split_daily_total():
    said = ("I take Zyloric for uric acid three hundred milligrams a day one hundred fifty in the morning "
            "and one hundred fifty at night")
    assert intake_of(said, claim("Zyloric", intake_amount=amt("allopurinol", 300))) is None
    assert intake_of(said, claim("Zyloric", intake_amount=amt("allopurinol", 150), per_day="2")) == Decimal(150)


def test_a_brand_slip_still_blocks_a_splitter():
    said = "I take Flolipid forty milligrams a day and Zyrtectec twenty"
    both = [claim("Flolipid", intake_amount=amt("simvastatin", 40), per_day="1"),
            claim("Zyrtec", intake_amount=amt("cetirizine", 20))]
    assert intake_of(said, *both, index=0) == Decimal(40)


@pytest.mark.parametrize("said, name", [
    ("With Concor I'm not sure five milligrams", "Concor"),
    ("With Concor I don't know five milligrams", "Concor"),
    ("باخد كونكور مش عارف خمسة تقريبا", "كونكور"),
    ("tomo Concor no sé cinco miligramos", "Concor"),
])
def test_not_sure_negates_the_knowing_not_the_amount(said, name):
    assert intake_of(said, claim(name, intake_amount=amt("bisoprolol", 5))) == Decimal(5)


def test_a_negation_right_before_the_amount_still_drops_it():
    assert intake_of("With Concor not five milligrams", claim("Concor", intake_amount=amt("bisoprolol", 5))) is None


def test_an_of_form_naming_the_claim_wins_over_the_walk_back():
    said = "I take Panadol. Five milligrams of Concor."
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 5))) == Decimal(5)
    assert intake_of(said, claim("Panadol", intake_amount=amt("paracetamol", 5))) is None
