"""Batch 34 contract: Spanish salt names (SPEC.md §3, "Decision order", rule 6, the bullet "Spanish salt names
(batch 34)"). Written by the CEO; do not edit. The Spanish names are those of Spain's medicines registry (AEMPS CIMA,
its list of active substances, read on 2 Nov); the two box texts are the registry images the Spanish hero ran on.
Before this batch, a Spanish salt name was read as no salt at all, so each pair below that disagrees was a `match`."""

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


def pack(label, mg, moiety="metoprolol", salt=None, part=None, oid="o1"):
    strength = Strength(ingredients=[amt(part or moiety, mg, salt)], per="tablet", release="immediate")
    return PackObservation(observation_id=oid, label_text=label, strength=strength, readability="readable",
                           country=None, visual_evidence=["r1"])


def intake(label, mg, name="Metoprolol", per_day=1, cid="c1"):
    return PatientClaim(claim_id=cid, name_text=name, inn=None, strength=None, intake_amount=amt(label, mg),
                        regimen=DoseRegimen(units_per_intake=None, intakes_per_day=Decimal(per_day), as_needed=None),
                        status="active", audio_evidence=["t1"])


def stated(label, mg, name="Metoprolol"):
    strength = Strength(ingredients=[amt(label, mg)], per="tablet", release="immediate")
    return PatientClaim(claim_id="c1", name_text=name, inn=None, strength=strength, intake_amount=None,
                        regimen=None, status="active", audio_evidence=["t1"])


def kind(claim, observation):
    return reconcile_pair(claim, observation, CAT).type


TARTRATE = pack("Metoprolol tartrate 100 mg", 100, salt="tartrate")
SUCCINATE = pack("Metoprolol succinate 47.5 mg", 47.5, salt="succinate")
# the registry images' printed text, as the Spanish hero's label reader returned it
LOPRESOR = pack("Lopresor® 100 mg\ncomprimidos recubiertos\ncon película\nMetoprolol, tartrato\n40 Comprimidos", 100)
EMCONCOR = pack("Emconcor® Cor 5 mg comprimidos recubiertos con película Fumarato de bisoprolol Vía oral 28 "
                "comprimidos recubiertos con película MERCK 869750.2 TLD", 5, moiety="bisoprolol", oid="o0")
SPANISH_SUCCINATE = ["metoprolol succinato", "succinato de metoprolol", "Metoprolol, succinato",
                     "Tomometoprolol succinato", "METOPROLOL SUCCINATO", "metoprolol succinato 100 mg"]


def amlodipine(salt):
    return pack(f"Amlodipine {salt} 5 mg", 5, moiety="amlodipine", salt=salt)


def atorvastatin(salt):
    return pack(f"Atorvastatin {salt} 20 mg", 20, moiety="atorvastatin", salt=salt)


# --- a Spanish salt name is read wherever a salt is read --------------------------------------------------------

@pytest.mark.parametrize("label", SPANISH_SUCCINATE)
def test_a_spanish_salt_in_an_intake_label(label):
    assert kind(intake(label, 100), TARTRATE) is D.FORMULATION_MISMATCH


@pytest.mark.parametrize("label", SPANISH_SUCCINATE)
def test_a_spanish_salt_in_a_strength_label(label):
    assert kind(stated(label, 100), TARTRATE) is D.FORMULATION_MISMATCH


@pytest.mark.parametrize("name", ["Metoprolol succinato", "Succinato de metoprolol"])
def test_a_spanish_salt_in_the_claims_name(name):
    assert kind(stated("metoprolol", 100, name=name), TARTRATE) is D.FORMULATION_MISMATCH


def test_the_lopresor_box_names_tartrate():
    assert kind(stated("metoprolol", 100, name="Metoprolol succinate"), LOPRESOR) is D.FORMULATION_MISMATCH
    assert kind(intake("metoprolol succinato", 100), LOPRESOR) is D.FORMULATION_MISMATCH
    assert kind(intake("metoprolol tartrato", 100), LOPRESOR) is D.MATCH
    assert kind(intake("metoprolol tartrate", 100), LOPRESOR) is D.MATCH


def test_a_spanish_salt_in_a_packs_strength_label():
    observed = pack("Metoprolol 100 mg", 100, part="metoprolol tartrato")
    assert kind(stated("metoprolol", 100, name="Metoprolol succinate"), observed) is D.FORMULATION_MISMATCH
    assert kind(stated("metoprolol", 100, name="Metoprolol tartrate"), observed) is D.MATCH


@pytest.mark.parametrize("label,observed,expected", [
    ("besilato de amlodipino", "maleate", D.FORMULATION_MISMATCH),
    ("amlodipino besilato", "maleate", D.FORMULATION_MISMATCH),
    ("Amlodipino maleato", "besilate", D.FORMULATION_MISMATCH),
    ("amlodipino besilato", "besilate", D.MATCH),
    ("maleato de amlodipino", "maleate", D.MATCH),
])
def test_amlodipines_two_salts_in_spanish(label, observed, expected):
    assert kind(intake(label, 5, name="Amlodipino"), amlodipine(observed)) is expected


@pytest.mark.parametrize("label", ["metformina hidrocloruro", "hidrocloruro de metformina", "METFORMINA HIDROCLORURO"])
def test_hydrochloride_in_spanish_is_hydrochloride(label):
    observed = pack("Metformin hydrochloride 850 mg", 850, moiety="metformin", salt="hydrochloride")
    assert kind(intake(label, 850, name="Metformina"), observed) is D.MATCH


@pytest.mark.parametrize("label", ["atorvastatina cálcica", "atorvastatina calcica", "ATORVASTATINA CALCICA 20 mg"])
def test_calcium_in_spanish_with_or_without_its_accent(label):
    assert kind(stated(label, 20, name="Atorvastatina"), atorvastatin("calcium")) is D.MATCH


@pytest.mark.parametrize("label", ["atorvastatina cálcica trihidrato", "Atorvastatina calcica trihidrato 20 mg"])
def test_one_longer_spanish_salt_gives_one_salt(label):
    assert kind(stated(label, 20, name="Atorvastatina"), atorvastatin("calcium trihydrate")) is D.MATCH


BISOPROLOL = {salt: pack(f"Bisoprolol {salt} 5 mg", 5, moiety="bisoprolol", salt=salt)
              for salt in ("fumarate", "hemifumarate")}


@pytest.mark.parametrize("spanish,english,name,observed", [
    ("metoprolol tartrato", "metoprolol tartrate", "Metoprolol", SUCCINATE),
    ("bisoprolol fumarato", "bisoprolol fumarate", "Bisoprolol", BISOPROLOL["hemifumarate"]),
    ("bisoprolol hemifumarato", "bisoprolol hemifumarate", "Bisoprolol", BISOPROLOL["fumarate"]),
    ("amlodipino besilato", "amlodipine besilate", "Amlodipino", amlodipine("maleate")),
    ("amlodipino maleato", "amlodipine maleate", "Amlodipino", amlodipine("besilate")),
    ("metformina hidrocloruro", "metformin hydrochloride", "Metformina",
     pack("Metformin hydrochloride 850 mg", 850, moiety="metformin", salt="hydrochloride")),
    ("atorvastatina cálcica", "atorvastatin calcium", "Atorvastatina", atorvastatin("calcium trihydrate")),
    ("atorvastatina calcica", "atorvastatin calcium", "Atorvastatina", atorvastatin("calcium trihydrate")),
    ("atorvastatina cálcica trihidrato", "atorvastatin calcium trihydrate", "Atorvastatina", atorvastatin("calcium")),
    ("atorvastatina calcica trihidrato", "atorvastatin calcium trihydrate", "Atorvastatina", atorvastatin("calcium")),
])
def test_each_spanish_name_reads_as_its_english_name(spanish, english, name, observed):
    mg = observed.strength.ingredients[0].amount
    assert kind(intake(spanish, mg, name=name), observed) is kind(intake(english, mg, name=name), observed)


# --- one salt in two languages is one salt; two salts abstain ---------------------------------------------------

def test_a_spanish_and_an_english_name_of_one_salt_are_one_salt():
    assert kind(intake("metoprolol succinato", 47.5, name="Metoprolol succinate"), SUCCINATE) is D.MATCH
    assert kind(intake("metoprolol succinate (succinato)", 100), TARTRATE) is D.FORMULATION_MISMATCH
    assert kind(intake("metoprolol tartrate", 100, name="Metoprolol, tartrato"), TARTRATE) is D.MATCH


def test_two_salts_on_one_side_abstain():
    assert kind(intake("metoprolol succinate", 100, name="Metoprolol tartrato"), TARTRATE) \
        is D.INSUFFICIENT_INFORMATION
    assert kind(intake("metoprolol", 100), pack("Metoprolol, tartrato 100 mg", 100, part="metoprolol succinate")) \
        is D.INSUFFICIENT_INFORMATION


# --- the Spanish hero's findings stay ----------------------------------------------------------------------------

@pytest.mark.parametrize("heard", ["bisoprolol", "Tomovisoprolol"])
def test_the_spanish_heros_findings_stay(heard):
    claims = [intake(heard, 10, name=heard, cid="c1"), intake("metoprolol", 100, name="metoprolol", per_day=2, cid="c2")]
    found = {(f.type, f.claim_id, f.observation_id) for f in reconcile_all(claims, [EMCONCOR, LOPRESOR], CAT)}
    assert found == {(D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH, "c1", "o0"), (D.MATCH, "c2", "o1")}


# --- rule 7: a Spanish label salt counts as an English one does --------------------------------------------------

@pytest.mark.parametrize("claim_of", [intake, stated])
def test_a_spanish_label_salt_counts_in_the_strength_rule_as_an_english_one_does(claim_of):
    english = kind(claim_of("metoprolol succinate", 50), SUCCINATE)
    assert english is not D.MATCH
    for label in ("metoprolol succinato", "succinato de metoprolol"):
        assert kind(claim_of(label, 50), SUCCINATE) is english, label
    assert kind(claim_of("metoprolol", 50), SUCCINATE) is D.MATCH
    assert kind(claim_of("metoprolol succinato", 47.5), SUCCINATE) is D.MATCH


# --- only the listed words, only beside their moiety, and nothing else changes -----------------------------------

def test_a_spanish_salt_word_counts_only_beside_its_moiety_or_brand():
    assert kind(intake("tomo tartrato", 47.5), SUCCINATE) is D.INSUFFICIENT_INFORMATION


def test_calcio_the_noun_is_not_a_salt():
    assert kind(intake("atorvastatina con calcio", 20, name="Atorvastatina"), atorvastatin("calcium trihydrate")) \
        is D.MATCH


def test_the_scalar_inn_is_read_as_before():
    claim = PatientClaim(claim_id="c1", name_text="Metoprolol", inn="metoprolol succinato",
                         strength=Strength(ingredients=[amt("metoprolol", 100)], per="tablet", release="immediate"),
                         intake_amount=None, regimen=None, status="active", audio_evidence=["t1"])
    assert kind(claim, TARTRATE) is D.INSUFFICIENT_INFORMATION


@pytest.mark.parametrize("text", ["metoprolol succinato", "succinato de metoprolol", "Metoprolol, tartrato",
                                  "Fumarato de bisoprolol", "amlodipino besilato"])
def test_name_matching_is_unchanged(text):
    assert not CAT.covers(text)
