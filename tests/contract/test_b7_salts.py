"""Batch 7 contract: curated salt-to-moiety mapping, salt kept as its own field. Written by the reviewer; do not edit.

Live Spark returns INNs with the salt ("bisoprolol fumarate"). The catalogue uses the active moiety, so on
27 Oct the reconciler paired nothing (evidence/decisions.md). Aliases are curated per moiety, never stripped
generically: an unknown suffix stays a different ingredient (safe: it surfaces instead of matching).
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all, reconcile_pair
from anamnesis.providers.spark import LabelReading
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import IngredientAmount, PackObservation, PatientClaim, Strength, canonical_inn, salt_of

LIVE = Path(__file__).parents[1] / "fixtures" / "spark_labels_live_2026-10-27.json"


@pytest.fixture(scope="module")
def cat():
    return load_catalogue()


@pytest.mark.parametrize("name,moiety,salt", [
    ("Metoprolol succinate", "metoprolol", "succinate"),
    ("metoprolol tartrate", "metoprolol", "tartrate"),
    ("Bisoprolol fumarate", "bisoprolol", "fumarate"),
    ("bisoprolol hemifumarate", "bisoprolol", "hemifumarate"),
    ("Amlodipine besylate", "amlodipine", "besilate"),       # US spelling -> INN spelling
    ("amlodipine besilate", "amlodipine", "besilate"),
    ("Metformin HCl", "metformin", "hydrochloride"),
    ("metformin hydrochloride", "metformin", "hydrochloride"),
    ("Atorvastatin calcium trihydrate", "atorvastatin", "calcium trihydrate"),
    ("amoxicillin trihydrate", "amoxicillin", "trihydrate"),
    ("Potassium clavulanate", "clavulanic acid", "potassium"),
    ("Clavulanic acid (as potassium clavulanate)", "clavulanic acid", "potassium"),
    ("Acetaminophen", "paracetamol", None),
    ("bisoprolol", "bisoprolol", None),
])
def test_curated_aliases_map_to_moiety_and_salt(name, moiety, salt):
    assert canonical_inn(name) == moiety
    assert salt_of(name) == salt


@pytest.mark.parametrize("name", ["bisoprolol sulfide", "metoprolol extra", "succinate"])
def test_unknown_suffixes_are_not_stripped(name):
    assert canonical_inn(name) == name.casefold()
    assert salt_of(name) is None


def test_ingredient_amount_splits_salt_into_its_own_field():
    a = IngredientAmount(inn="Metoprolol succinate", amount=Decimal(100), unit="mg")
    assert (a.inn, a.salt) == ("metoprolol", "succinate")
    assert IngredientAmount.model_validate_json(a.model_dump_json()) == a
    plain = IngredientAmount(inn="metoprolol", amount=Decimal(100), unit="mg")
    assert plain.salt is None
    explicit = IngredientAmount(inn="metoprolol", salt="tartrate", amount=Decimal(50), unit="mg")
    assert explicit.salt == "tartrate"


def test_salt_and_plain_forms_of_one_moiety_are_duplicates():
    with pytest.raises(ValueError):
        Strength(ingredients=[IngredientAmount(inn="metoprolol succinate", amount=Decimal(100), unit="mg"),
                              IngredientAmount(inn="metoprolol", amount=Decimal(50), unit="mg")], per="tablet")


def mg(inn, a):
    return IngredientAmount(inn=inn, amount=Decimal(str(a)), unit="mg")


def test_salt_names_on_the_pack_pair_with_plain_claims(cat):
    pack = PackObservation(observation_id="o1", label_text="Concor 5 mg Bisoprolol fumarate", inn="Bisoprolol fumarate",
                           strength=Strength(ingredients=[mg("Bisoprolol fumarate", 5)], per="tablet", release="immediate"),
                           readability="readable", visual_evidence=["r1"])
    claim = PatientClaim(claim_id="c1", name_text="Concor", strength=Strength(ingredients=[mg("bisoprolol", 5)], per="tablet"),
                         status="active", audio_evidence=["t1"])
    assert reconcile_pair(claim, pack, cat).type is D.MATCH


def test_different_known_salts_are_a_formulation_mismatch(cat):
    # Metoprolol succinate and tartrate are not interchangeable mg for mg.
    pack = PackObservation(observation_id="o1", label_text="Beloc-Zok 100 mg",
                           strength=Strength(ingredients=[mg("metoprolol succinate", 100)], per="tablet", release="modified"),
                           readability="readable", visual_evidence=["r1"])
    claim = PatientClaim(claim_id="c1", name_text="metoprolol tartrate",
                         strength=Strength(ingredients=[mg("metoprolol tartrate", 100)], per="tablet", release="modified"),
                         status="active", audio_evidence=["t1"])
    assert reconcile_pair(claim, pack, cat).type is D.FORMULATION_MISMATCH


def test_the_live_readings_from_27_oct_now_pair(cat):
    packs = []
    for i, item in enumerate(json.loads(LIVE.read_text(encoding="utf-8"))):
        r = LabelReading.model_validate(item["reading"])
        packs.append(PackObservation(observation_id=f"o{i}", label_text=r.label_text, inn=r.inn, strength=r.strength,
                                     readability=r.readability, country=r.country, visual_evidence=[r.region_id]))
    claims = [  # the English voice note: "Concor five milligrams once a day ... metoprolol fifty milligrams twice a day"
        PatientClaim(claim_id="c1", name_text="Concor", strength=Strength(ingredients=[mg("bisoprolol", 5)], per="tablet"),
                     status="active", audio_evidence=["turn-0"]),
        PatientClaim(claim_id="c2", name_text="metoprolol", intake_amount=mg("metoprolol", 50), status="active",
                     audio_evidence=["turn-0"]),
    ]
    found = {(f.claim_id, f.observation_id): f.type for f in reconcile_all(claims, packs, cat)}
    assert found == {("c1", "o1"): D.MATCH, ("c2", "o0"): D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH}
