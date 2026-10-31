"""Batch 27.1 contract: two fail-safe gaps the Opus supervisor found in batch 27's round 3 (SPEC §2, "Relation checks
(batch 27)", rules 1 and 3). Written by the CEO; Muse must not edit it."""

from decimal import Decimal

import pytest

from tests.contract.test_b27_relations import amt, claim, intake_of, parse


@pytest.mark.parametrize("said, name", [
    ("I take Concor ten a day for five years.", "Concor"),
    ("I take Concor ten milligrams a day for five years.", "Concor"),
    ("باخد كونكور عشرة ملي في اليوم من خمس سنين", "كونكور"),
    ("tomo Concor diez miligramos al día desde hace cinco años", "Concor"),
])
def test_a_duration_doesnt_split_a_daily_amount(said, name):
    kept = claim(name, intake_amount=amt("bisoprolol", 10), per_day="1")
    assert intake_of(said, kept) == Decimal(10)


@pytest.mark.parametrize("said", [
    "I take Concor five milligrams for two weeks.",
    "باخد كونكور خمسة ملي جرام بقالي اسبوعين",
])
def test_a_duration_is_never_an_amount(said):
    name = "كونكور" if "كونكور" in said else "Concor"
    assert intake_of(said, claim(name, intake_amount=amt("bisoprolol", 5))) == Decimal(5)
    if name == "Concor":
        assert intake_of(said, claim(name, intake_amount=amt("bisoprolol", 2))) is None


def test_ten_a_day_is_still_a_daily_amount_not_a_duration():
    said = "I take Concor ten a day."
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 10), per_day="1")) == Decimal(10)
    split = "I take Concor 10 a day, 5 in the morning and 5 at night."
    assert intake_of(split, claim("Concor", intake_amount=amt("bisoprolol", 10))) is None


def test_ich_weiss_nicht_negates_the_knowing_not_the_amount():
    said = "Ich nehme Concor ich weiß nicht fünf Milligramm"
    assert intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 5))) == Decimal(5)
    assert intake_of("Ich nehme Concor nicht fünf Milligramm",
                     claim("Concor", intake_amount=amt("bisoprolol", 5))) is None


# The live probe of 31 Oct, 12:40: on trap J the tuned Glimmer wrote a 10 mg intake and five tablets per intake.
# Rule 6 dropped the 10, but the five stayed and gave a false strength_mismatch.
def test_a_dropped_amount_takes_an_unbacked_tablet_count_with_it():
    said = "I take Concor ten milligrams a day, five in the morning and five at night."
    kept = intake_of(said, claim("Concor", intake_amount=amt("bisoprolol", 10), units="5"))
    assert kept is None
    regimen = parse(said, claim("Concor", intake_amount=amt("bisoprolol", 10), units="5"))[0].regimen
    assert regimen is None or regimen.units_per_intake is None


def test_a_tablet_count_said_as_a_count_stays():
    said = "I take two Panadol tablets when I have a headache."
    regimen = parse(said, claim("Panadol", intake_amount=amt("paracetamol", 2), units="2"))[0].regimen
    assert regimen is not None and regimen.units_per_intake == Decimal(2)


def test_units_stay_when_nothing_was_dropped():
    said = "I take Concor five milligrams, one in the morning."
    regimen = parse(said, claim("Concor", intake_amount=amt("bisoprolol", 5), units="1"))[0].regimen
    assert regimen is not None and regimen.units_per_intake == Decimal(1)
