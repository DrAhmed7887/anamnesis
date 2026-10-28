"""Batch 21 contract, part 2: fixes found while staging the real-media cases (evidence/batches/21/manifest.md).
Written by the CEO; Muse must not edit it.

SPEC §2: a second hundreds group joined by "and" or "و" starts a new number, so "eight hundred seventy-five and
one hundred twenty-five" states 875 and 125, never 87625 (found while writing case U2).
SPEC §7: every amount on the two sides is isolated left to right, so an Arabic row reads "50 mg", not "mg 50"
(found by the judge-facing session in the 27 Oct Arabic brief).

From the first live runs on 28 Oct (evidence/batches/21/live-before.md):
SPEC §2: the claim prompt asks for digits. Batch 20's wording made Spark copy number words ("amount": "five"), so every
dose spoken in words was dropped. The label prompt asks for all printed text, digits and the English INN.
SPEC §2 aliases: the French, Spanish, German and Latin forms of the catalogue's ingredients resolve (U2, U8).
SPEC §3 pairing: a claim with only an intake amount pairs with the pack of that strength first (U5 paired "Norvasc
5 mg" with the 10 mg box).
"""

import json
from decimal import Decimal

import pytest

from anamnesis.core.reconcile import reconcile_all
from anamnesis.providers.claims import _SYSTEM_PROMPT as CLAIM_PROMPT
from anamnesis.providers.claims import parse_claims_json
from anamnesis.providers.meta import _SYSTEM_PROMPT as LABEL_PROMPT
from anamnesis.providers.stated import stated_amounts
from anamnesis.schema import AudioTurn, PackObservation
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.medication import canonical_inn, salt_of
from anamnesis.schema.templates import FIELD_INTAKE, FIELD_STRENGTH
from tests.contract.test_b19_brief import CAT, claim, mg, reading, st
from tests.contract.test_b20_stated_amounts import amount
from tests.contract.test_b20_stated_amounts import claim as raw_claim
from tests.contract.test_b21_qm_pins import brief_of, field_rows

# --- SPEC §2: a second hundreds group starts a new number ---------------------------------------------------

@pytest.mark.parametrize("text,values,absent", [
    ("eight hundred seventy-five and one hundred twenty-five milligrams", {"875", "125"}, "87625"),
    ("five hundred and two hundred", {"500", "200"}, "50200"),
    ("تمنمية خمسة وسبعين ومية خمسة وعشرين", {"875", "125"}, "87525"),
    ("خمسمية ومية", {"500", "100"}, "50000"),
])
def test_a_second_hundreds_group_starts_a_new_number(text, values, absent):
    found = stated_amounts(text)
    assert {Decimal(v) for v in values} <= found
    assert Decimal(absent) not in found


@pytest.mark.parametrize("text,value", [
    ("two hundred and fifty", "250"),
    ("one hundred and twenty-five", "125"),
    ("eight hundred and seventy-five", "875"),
    ("two thousand five hundred and fifty", "2550"),
    ("ميتين وخمسين", "250"),
    ("مية وخمسين", "150"),
    ("ألف وخمسمية", "1500"),
])
def test_one_number_with_its_hundreds_stays_one_number(text, value):
    assert Decimal(value) in stated_amounts(text)


def test_a_combination_strength_said_in_words_is_kept():
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=6000, transcript=(
        "I take Augmentin, eight hundred seventy-five and one hundred twenty-five milligrams, twice a day."))]
    strength = {"ingredients": [amount("875", inn="amoxicillin"), amount("125", inn="clavulanic acid")],
                "per": "tablet", "release": "unknown"}
    [found] = parse_claims_json(json.dumps({"claims": [raw_claim("Augmentin", strength=strength)]}), turns)
    assert found.strength is not None
    assert [part.amount for part in found.strength.ingredients] == [Decimal("875"), Decimal("125")]


# --- SPEC §7: amounts are isolated left to right ---------------------------------------------------------

def ltr_amounts(box, label):
    [dd] = [dd for name, dd in field_rows(box) if name == label]
    return [b.text() for b in dd.find_all("bdi") if b.attrs.get("dir") == "ltr"]


def test_an_arabic_row_keeps_each_amount_left_to_right():
    said = claim("c1", "بيلوك زوك", ["turn-0"], intake=mg("بيلوك زوك", 50), per_day=2)
    read = reading("Beloc-Zok 100 mg", st(mg("metoprolol succinate", 100), release="modified"))
    _, _, node = brief_of(said, read, "بيلوك زوك خمسين ملي مرتين في اليوم")
    [patient] = node.find_all(data_side="patient")
    [pack] = node.find_all(data_side="pack")
    assert ltr_amounts(patient, FIELD_INTAKE) == ["50 mg"]
    assert ltr_amounts(pack, FIELD_STRENGTH) == ["100 mg"]


def test_each_ingredient_of_a_combination_is_isolated():
    said = claim("c1", "Augmentin", ["turn-0"],
                 strength=st(mg("amoxicillin", 875), mg("clavulanic acid", 125)))
    read = reading("Augmentin 875 mg/125 mg", st(mg("amoxicillin", 875), mg("clavulanic acid", 125)))
    _, _, node = brief_of(said, read, "Augmentin 875 and 125 mg.")
    for side in ("patient", "pack"):
        [box] = node.find_all(data_side=side)
        assert ltr_amounts(box, FIELD_STRENGTH) == ["875 mg", "125 mg"], side


# --- SPEC §2: the prompts (live, 28 Oct) -----------------------------------------------------------------

def test_the_claim_prompt_asks_for_amounts_as_digits():
    assert "Write each amount with the number and unit the patient said" not in CLAIM_PROMPT
    assert "as digits, even when the patient said it in words" in CLAIM_PROMPT
    assert "never convert units" in CLAIM_PROMPT


def test_the_label_prompt_asks_for_all_printed_text_digits_and_the_english_inn():
    assert "including every amount you report" in LABEL_PROMPT
    assert "as digits" in LABEL_PROMPT and "never convert units" in LABEL_PROMPT
    assert "English INN" in LABEL_PROMPT


# --- SPEC §2: ingredient names as packs print them ---------------------------------------------------------

@pytest.mark.parametrize("name,inn,salt", [
    ("amoxicilline", "amoxicillin", None), ("amoxicilina", "amoxicillin", None),
    ("amoxicillinum", "amoxicillin", None),
    ("acide clavulanique", "clavulanic acid", None), ("ácido clavulánico", "clavulanic acid", None),
    ("Clavulansäure", "clavulanic acid", None), ("acidum clavulanicum", "clavulanic acid", None),
    ("paracétamol", "paracetamol", None), ("paracetamolum", "paracetamol", None),
    ("métoprolol", "metoprolol", None), ("metoprololum", "metoprolol", None),
    ("metoprololi succinas", "metoprolol", "succinate"), ("Metoprololsuccinat", "metoprolol", "succinate"),
    ("metoprololi tartras", "metoprolol", "tartrate"), ("Metoprololtartrat", "metoprolol", "tartrate"),
    ("bisoprololum", "bisoprolol", None), ("bisoprololi fumaras", "bisoprolol", "fumarate"),
    ("Bisoprololfumarat", "bisoprolol", "fumarate"),
    ("amlodipino", "amlodipine", None), ("amlodipinum", "amlodipine", None),
    ("amlodipini besilas", "amlodipine", "besilate"), ("Amlodipinbesilat", "amlodipine", "besilate"),
    ("metformina", "metformin", None), ("metformine", "metformin", None), ("metforminum", "metformin", None),
    ("metformini hydrochloridum", "metformin", "hydrochloride"), ("Metforminhydrochlorid", "metformin", "hydrochloride"),
    ("atorvastatina", "atorvastatin", None), ("atorvastatine", "atorvastatin", None),
    ("atorvastatinum", "atorvastatin", None), ("atorvastatinum calcicum", "atorvastatin", "calcium"),
    ("caféine", "caffeine", None), ("cafeína", "caffeine", None), ("Coffein", "caffeine", None),
    ("coffeinum", "caffeine", None),
])
def test_foreign_and_latin_ingredient_names_resolve(name, inn, salt):
    assert canonical_inn(name) == inn
    assert salt_of(name) == salt


def test_a_pack_read_in_french_pairs_with_its_claim():
    said = claim("c1", "Augmentin", ["turn-0"], strength=st(mg("amoxicillin", 875), mg("clavulanic acid", 125)))
    read = reading("Augmentin 875 mg/125 mg comprimés pelliculés",
                   st(mg("amoxicilline", 875), mg("acide clavulanique", 125)))
    finding, _, _ = brief_of(said, read, "Augmentin 875 and 125 mg.")
    assert finding.type is D.MATCH


# --- SPEC §3: an intake amount pairs with the pack of that strength (live U5) -------------------------------

def pack(oid, amount):
    return PackObservation(observation_id=oid, label_text=f"Norvasc {amount} mg Tablets", inn="amlodipine",
                           strength=st(mg("amlodipine", amount), release="immediate"), readability="readable",
                           visual_evidence=[f"r{oid}"])


@pytest.mark.parametrize("order", [("o0", "o1"), ("o1", "o0")])
def test_an_intake_amount_pairs_with_the_pack_of_that_strength(order):
    said = claim("c1", "Norvasc", ["turn-0"], intake=mg("Norvasc", 5), per_day=1)
    packs = {"o0": pack("o0", 10), "o1": pack("o1", 5)}
    findings = reconcile_all([said], [packs[oid] for oid in order], CAT)
    by_pair = {(f.claim_id, f.observation_id): f.type for f in findings}
    assert by_pair[("c1", "o1")] is D.MATCH
    assert by_pair[(None, "o0")] is D.MISSING_MODALITY


# --- round 2 (supervisor 21) -------------------------------------------------------------------------------
# #1, #2: the new hundreds group takes as its multiplier only a final plain worth 1-9 just before it; none when the
# hundred word carries its own و. #3: a one-word Arabic hundred (ميتين, تلتمية ... تسعمية) after a hundreds part
# also starts a new number. None of these may state a value the patient never said.

@pytest.mark.parametrize("text,values,absent", [
    ("eight hundred seventy-five one hundred twenty-five milligrams", {"875", "125"}, "876"),
    ("five hundred one hundred twenty-five", {"500", "125"}, "501"),
    ("three hundred three hundred", {"300"}, "303"),
    ("خمسمية وتلات مية", {"500", "300"}, "503"),
    ("ميتين وخمسين وخمسة مية", {"250", "500"}, "255"),
    ("خمسمية وميتين", {"500", "200"}, "700"),
    ("خمسمية وتلتمية", {"500", "300"}, "800"),
    ("تمنمية خمسة وسبعين وتلتمية خمسة وعشرين", {"875", "325"}, "1200"),
])
def test_round_2_a_second_hundreds_group_states_nothing_unsaid(text, values, absent):
    found = stated_amounts(text)
    assert {Decimal(v) for v in values} <= found
    assert Decimal(absent) not in found


@pytest.mark.parametrize("text,value", [
    ("ألف وميتين", "1200"), ("ألف وخمسمية", "1500"), ("one hundred one", "101"), ("twelve hundred", "1200"),
])
def test_round_2_one_number_with_a_thousand_or_units_stays_one(text, value):
    assert Decimal(value) in stated_amounts(text)


# #6: a digit run next to a digit of another set states nothing.
@pytest.mark.parametrize("text", ["١5 mg".replace("١", "１"), "5５ mg", "५5 mg"])
def test_round_2_a_run_touching_a_foreign_digit_states_nothing(text):
    assert Decimal("5") not in stated_amounts(text)


# #7: accented alias keys match decomposed input too.
def test_round_2_decomposed_accents_still_resolve():
    import unicodedata
    assert canonical_inn(unicodedata.normalize("NFD", "ácido clavulánico")) == "clavulanic acid"
    assert canonical_inn(unicodedata.normalize("NFD", "Paracétamol")) == "paracetamol"


# #4: the advice sentences of both prompts are pinned.
def test_round_2_both_prompts_keep_their_advice_sentences():
    assert "Give no advice. Use unreadable or partial rather than guessing." in LABEL_PROMPT
    assert "Give no medical advice. Only report what the patient said." in CLAIM_PROMPT


# --- round 3 (supervisor 21, round 2) ----------------------------------------------------------------------
# #1: a plain worth 1000 or more (ألفين) closes the thousands part like a thousand word. #2: after the filler "a"
# ("and a hundred") nothing moves. #3: a digit run is atomic, so a decimal touching a foreign digit states nothing.

@pytest.mark.parametrize("text,values,absent", [
    ("ألفين وخمسمية", {"2500"}, None),
    ("ألفين و ميتين", {"2200"}, None),
    ("ألفين ومية", {"2100"}, "200000"),
    ("ألفين وخمسمية وخمسين", {"2550"}, "550"),
    ("eight hundred seventy-five and a hundred twenty-five", {"875", "125"}, "870"),
    ("eight hundred seventy-five and a hundred twenty-five", {"875", "125"}, "525"),
    ("one hundred twenty-five and a hundred", {"125", "100"}, "120"),
])
def test_round_3_thousands_words_and_the_filler_a_state_only_what_was_said(text, values, absent):
    found = stated_amounts(text)
    assert {Decimal(v) for v in values} <= found
    if absent:
        assert Decimal(absent) not in found


@pytest.mark.parametrize("text", ["1.5５ mg", "2,5５ mg", "٢٫٥५"])
def test_round_3_a_decimal_touching_a_foreign_digit_states_nothing(text):
    assert stated_amounts(text) == frozenset()


@pytest.mark.parametrize("text,values", [("I take 5.", {"5"}), ("Augmentin 875 mg/125 mg", {"875", "125"})])
def test_round_3_plain_digit_runs_are_unchanged(text, values):
    assert {Decimal(v) for v in values} <= stated_amounts(text)
