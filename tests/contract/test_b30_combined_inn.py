"""Batch 30 contract: an `inn` string that names several ingredients ("amoxicillin/clavulanic acid") is read as
that set (SPEC §3, "Identity of one side", batch 30), from U2's three live runs on 31 Oct. Written by the CEO;
Muse must not edit it."""

from decimal import Decimal

import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import claim_identity_conflict, pack_identity_conflict, reconcile_all
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import (
    DoseRegimen,
    IngredientAmount,
    PackObservation,
    PatientClaim,
    Strength,
)

CAT = load_catalogue()
LABEL = ("Augmentin® 875 mg/125 mg\ncomprimés pelliculés\nAmoxicilline/acide clavulanique\n20 comprimés pelliculés\n"
         "gsk")


def part(inn, amount):
    return IngredientAmount(inn=inn, amount=Decimal(amount), unit="mg")


def strength(*parts, release="unknown"):
    return Strength(ingredients=list(parts), per="tablet", release=release)


AUGMENTIN = strength(part("amoxicillin", 875), part("clavulanic acid", 125))
CLAIM = PatientClaim(claim_id="c1", name_text="Augmentin", strength=AUGMENTIN,
                     regimen=DoseRegimen(intakes_per_day=Decimal(2)), status="active", audio_evidence=["turn-0"])


def pack(inn, pack_strength=None, label=LABEL):
    return PackObservation(observation_id="o0", label_text=label, inn=inn, readability="readable",
                           strength=pack_strength if pack_strength is not None else strength(
                               part("amoxicillin", 875), part("clavulanic acid", 125), release="immediate"),
                           visual_evidence=["r-0"])


def finding(claim, observation):
    (only,) = [f for f in reconcile_all([claim], [observation], CAT) if f.claim_id == claim.claim_id]
    return only.type


def test_u2_live_pair_now_matches():
    assert finding(CLAIM, pack("amoxicillin/clavulanic acid")) is D.MATCH


@pytest.mark.parametrize("inn", ["amoxicillin/clavulanic acid", "amoxicillin / clavulanic acid",
                                 "amoxicillin + clavulanic acid", "amoxicillin and clavulanic acid",
                                 "amoxicillin, clavulanic acid", "amoxicillin & clavulanic acid",
                                 "clavulanic acid/amoxicillin"])
def test_a_combined_inn_names_its_set(inn):
    assert not pack_identity_conflict(pack(inn), CAT)
    assert finding(CLAIM, pack(inn)) is D.MATCH


@pytest.mark.parametrize("inn", ["amoxicillin/sulbactam", "amoxicillin/clavulanic acid/caffeine"])
def test_a_combined_inn_that_differs_from_the_strength_is_a_conflict(inn):
    assert pack_identity_conflict(pack(inn), CAT)
    assert finding(CLAIM, pack(inn)) is D.INSUFFICIENT_INFORMATION


def test_a_combined_inn_against_a_one_ingredient_strength_is_a_conflict():
    one = strength(part("amoxicillin", 875), release="immediate")
    assert pack_identity_conflict(pack("amoxicillin/clavulanic acid", one), CAT)


def test_a_combined_inn_without_a_strength_is_the_sides_identity():
    observation = PackObservation(observation_id="o0", label_text="Augmentin", inn="amoxicillin/clavulanic acid",
                                  readability="readable", strength=None, visual_evidence=["r-0"])
    assert not pack_identity_conflict(observation, CAT)


def test_a_single_inn_is_unchanged():
    one = strength(part("bisoprolol", 5), release="immediate")
    assert not pack_identity_conflict(pack("bisoprolol", one, label="Concor 5 mg"), CAT)
    assert pack_identity_conflict(pack("paracetamol", one, label="Concor 5 mg"), CAT)


def test_the_claim_side_reads_a_combined_inn_too():
    claim = CLAIM.model_copy(update={"inn": "amoxicillin and clavulanic acid"})
    assert not claim_identity_conflict(claim, CAT)
    wrong = CLAIM.model_copy(update={"inn": "amoxicillin and sulbactam"})
    assert claim_identity_conflict(wrong, CAT)


# --- round 2, from the fresh Muse audit and the Opus supervisor (31 Oct) --------------------------------------

def _claim(inn=None, claim_strength=AUGMENTIN):
    return CLAIM.model_copy(update={"inn": inn, "strength": claim_strength})


@pytest.mark.parametrize("claim_inn, claim_strength, pack_inn, pack_strength, want", [
    ("amoxicillin sodium", AUGMENTIN, "amoxicillin trihydrate/potassium clavulanate", None, D.FORMULATION_MISMATCH),
    ("amoxicillin sodium/clavulanic acid", AUGMENTIN, None,
     strength(part("amoxicillin trihydrate", 875), part("clavulanic acid", 125), release="immediate"),
     D.FORMULATION_MISMATCH),
    (None, AUGMENTIN, "amoxicillin trihydrate/amoxicillin sodium/clavulanic acid", None, D.INSUFFICIENT_INFORMATION),
])
def test_salts_named_inside_a_combined_inn_count(claim_inn, claim_strength, pack_inn, pack_strength, want):
    observation = pack(pack_inn, pack_strength) if pack_inn else pack(None, pack_strength)
    assert finding(_claim(claim_inn, claim_strength), observation) is want


def test_a_stray_separator_leaves_one_ingredient():
    one = strength(part("amoxicillin", 875), release="immediate")
    assert not pack_identity_conflict(pack("amoxicillin/", one, label="Amoxicillin 875 mg"), CAT)


def test_arabic_wa_splits_only_as_a_spaced_word():
    assert finding(CLAIM, pack("amoxicillin و clavulanic acid")) is D.MATCH
    assert pack_identity_conflict(pack("amoxicillin وclavulanic acid"), CAT)  # attached: a known limit, fails safe


def test_a_comma_inside_one_ingredients_name_doesnt_split():
    dcba = strength(part("2,4-dichlorobenzyl alcohol", "1.2"), release="immediate")
    assert not pack_identity_conflict(pack("2,4-dichlorobenzyl alcohol", dcba, label="Strepsils"), CAT)


def test_a_long_run_of_spaces_stays_fast():
    import time
    start = time.monotonic()
    pack_identity_conflict(pack("amoxicillin" + " " * 30000 + "x"), CAT)
    assert time.monotonic() - start < 1.0
