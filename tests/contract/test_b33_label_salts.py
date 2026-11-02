"""Batch 33 contract: a salt said inside a longer ingredient label (SPEC.md §3, "Decision order", rule 6, the bullet
"A salt said inside a longer label (batch 33)"). Written by the CEO; do not edit. Before this batch, every label in
SUCCINATE_LABELS was reconciled as `match` against a tartrate pack, because only an exact alias was read."""

from decimal import Decimal

import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all, reconcile_pair
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import DoseRegimen, IngredientAmount, PackObservation, PatientClaim, Strength

CAT = load_catalogue()


def amt(inn, mg, salt=None):
    """An ingredient as the product builds one: a model reply has no salt key, so the validator reads the name."""
    fields = {"inn": inn, "amount": Decimal(str(mg)), "unit": "mg"}
    if salt:
        fields["salt"] = salt
    return IngredientAmount.model_validate(fields)


def pack(label, mg, moiety="metoprolol", salt=None, part=None):
    strength = Strength(ingredients=[amt(part or moiety, mg, salt)], per="tablet", release="immediate")
    return PackObservation(observation_id="o1", label_text=label, strength=strength, readability="readable",
                           country=None, visual_evidence=["r1"])


def intake(label, mg, name="Metoprolol"):
    return PatientClaim(claim_id="c1", name_text=name, inn=None, strength=None, intake_amount=amt(label, mg),
                        regimen=DoseRegimen(units_per_intake=None, intakes_per_day=Decimal(1), as_needed=None),
                        status="active", audio_evidence=["t1"])


def stated(label, mg, name="Metoprolol"):
    strength = Strength(ingredients=[amt(label, mg)], per="tablet", release="immediate")
    return PatientClaim(claim_id="c1", name_text=name, inn=None, strength=strength, intake_amount=None,
                        regimen=None, status="active", audio_evidence=["t1"])


def kind(claim, observation):
    return reconcile_pair(claim, observation, CAT).type


TARTRATE = pack("Metoprolol tartrate 100 mg", 100, salt="tartrate")
SUCCINATE_LABELS = ["tomo metoprolol succinate", "tomometoprolol succinate", "Tomometoprolol Succinate",
                    "TOMO METOPROLOL SUCCINATE", "metoprolol, succinate", "metoprolol (as succinate)",
                    "metoprolol succinate retard", "metoprolol succinate 100 mg"]


# --- a salt inside a longer label is read ------------------------------------------------------------------------

@pytest.mark.parametrize("label", SUCCINATE_LABELS)
def test_a_salt_inside_an_intake_label_is_read(label):
    assert kind(intake(label, 100), TARTRATE) is D.FORMULATION_MISMATCH


@pytest.mark.parametrize("label", SUCCINATE_LABELS)
def test_a_salt_inside_a_strength_label_is_read(label):
    assert kind(stated(label, 100), TARTRATE) is D.FORMULATION_MISMATCH


def test_the_exact_label_disagrees_as_before():
    assert kind(intake("metoprolol succinate", 100), TARTRATE) is D.FORMULATION_MISMATCH
    assert kind(stated("metoprolol succinate", 100), TARTRATE) is D.FORMULATION_MISMATCH


@pytest.mark.parametrize("label", ["tomo amlodipine maleate", "amlodipine maleate 5 mg", "Amlodipine, maleate"])
def test_another_curated_salt_inside_a_label(label):
    besilate = pack("Amlodipine besilate 5 mg", 5, moiety="amlodipine", salt="besilate")
    assert kind(intake(label, 5, name="Amlodipine"), besilate) is D.FORMULATION_MISMATCH


def test_an_arabic_brand_label_with_a_salt_of_its_moiety():
    besilate = pack("Amlodipine besilate 5 mg", 5, moiety="amlodipine", salt="besilate")
    assert kind(intake("نورفاسك maleate", 5, name="نورفاسك"), besilate) is D.FORMULATION_MISMATCH


def test_a_salt_in_a_packs_strength_label_is_read():
    observed = pack("Metoprolol 100 mg", 100, part="metoprolol tartrate USP")
    assert kind(stated("metoprolol", 100, name="Metoprolol succinate"), observed) is D.FORMULATION_MISMATCH
    assert kind(stated("metoprolol", 100, name="Metoprolol tartrate"), observed) is D.MATCH


# --- the pack's own salt, or no salt, changes nothing ------------------------------------------------------------

@pytest.mark.parametrize("label", ["tomo metoprolol tartrate", "metoprolol, tartrate", "metoprolol tartrate 100 mg"])
def test_the_packs_own_salt_inside_a_label_still_matches(label):
    assert kind(intake(label, 100), TARTRATE) is D.MATCH
    assert kind(stated(label, 100), TARTRATE) is D.MATCH


@pytest.mark.parametrize("label", ["tomo metoprolol", "tomometoprolol", "metoprolol 100 mg", "Metoprolol"])
def test_a_label_without_a_salt_changes_nothing(label):
    assert kind(intake(label, 100), TARTRATE) is D.MATCH
    assert kind(stated(label, 100), TARTRATE) is D.MATCH


def test_one_longer_alias_gives_one_salt():
    calcium = pack("Atorvastatin calcium 20 mg", 20, moiety="atorvastatin", salt="calcium")
    trihydrate = pack("Atorvastatin calcium trihydrate 20 mg", 20, moiety="atorvastatin", salt="calcium trihydrate")
    assert kind(stated("atorvastatin calcium 20 mg", 20, name="Atorvastatin"), calcium) is D.MATCH
    assert kind(stated("atorvastatin calcium trihydrate 20 mg", 20, name="Atorvastatin"), trihydrate) is D.MATCH


def test_a_combination_keeps_its_salts_apart():
    def augmentin():
        return Strength(ingredients=[amt("amoxicillin trihydrate", 875), amt("potassium clavulanate", 125)],
                        per="tablet", release="unknown")
    claim = PatientClaim(claim_id="c1", name_text="Augmentin", inn=None, strength=augmentin(), intake_amount=None,
                         regimen=None, status="active", audio_evidence=["t1"])
    observed = PackObservation(observation_id="o1", label_text="Augmentin 875 mg/125 mg", strength=augmentin(),
                               readability="readable", country=None, visual_evidence=["r1"])
    assert kind(claim, observed) is D.MATCH


# --- the label's salt counts wherever the shared path counts -----------------------------------------------------

def test_two_salts_on_one_side_abstain():
    assert kind(intake("tomo metoprolol succinate", 100, name="Metoprolol tartrate"), TARTRATE) \
        is D.INSUFFICIENT_INFORMATION
    assert kind(stated("metoprolol succinate 100 mg", 100, name="Metoprolol tartrate"), TARTRATE) \
        is D.INSUFFICIENT_INFORMATION


def test_a_pack_reading_that_names_two_salts_abstains():
    observed = pack("Metoprolol tartrate 100 mg", 100, part="metoprolol succinate 100 mg")
    assert kind(intake("metoprolol", 100), observed) is D.INSUFFICIENT_INFORMATION


@pytest.mark.parametrize("claim_of", [intake, stated])
def test_a_label_salt_counts_in_the_strength_rule_as_an_exact_one_does(claim_of):
    succinate = pack("Metoprolol succinate 47.5 mg", 47.5, salt="succinate")
    exact = kind(claim_of("metoprolol succinate", 50), succinate)
    assert exact is not D.MATCH
    for label in ("tomo metoprolol succinate", "tomometoprolol succinate", "metoprolol succinate 50 mg"):
        assert kind(claim_of(label, 50), succinate) is exact, label
    for label in ("metoprolol", "tomo metoprolol"):
        assert kind(claim_of(label, 50), succinate) is D.MATCH, label


# --- nothing else changes ----------------------------------------------------------------------------------------

def test_the_packs_salt_basis_lookup_still_reads_only_its_exact_name():
    observed = pack("Metoprolol 47.5 mg", 47.5, part="metoprolol succinate retard")
    assert kind(intake("metoprolol", 50), observed) is not D.MATCH


def test_the_scalar_inn_is_read_as_before():
    claim = PatientClaim(claim_id="c1", name_text="Metoprolol", inn="tomo metoprolol succinate",
                         strength=Strength(ingredients=[amt("metoprolol", 100)], per="tablet", release="immediate"),
                         intake_amount=None, regimen=None, status="active", audio_evidence=["t1"])
    assert kind(claim, TARTRATE) is D.INSUFFICIENT_INFORMATION


def test_the_label_stays_as_written():
    claims = [intake("tomometoprolol succinate", 100)]
    reconcile_all(claims, [TARTRATE], CAT)
    assert claims[0].intake_amount.inn == "tomometoprolol succinate"
