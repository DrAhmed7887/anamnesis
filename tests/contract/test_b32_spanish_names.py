"""Batch 32 contract: Spanish speech in catalogue resolution (SPEC.md §3, "Catalogue resolution", the bullet
"Spanish speech (batch 32)"). Written by the CEO; do not edit. The heard names and the two packs are the ones of the
Spanish hero's fourth set (1 Nov), where Voice Transcribe wrote "Tomobisoprolol", "Tomovisoprolol" and "visoprolol"."""

import re
from decimal import Decimal

import pytest

from anamnesis.core.catalogue import load_catalogue, normalise
from anamnesis.core.overlap import OverlapKind, cross_medication
from anamnesis.core.reconcile import reconcile_all, reconcile_pair
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema import DoseRegimen, IngredientAmount, PackObservation, PatientClaim, Strength
from anamnesis.schema.medication import INN_ALIASES

CAT = load_catalogue()
TOMAR = ("tomo", "toma", "tomas", "tomamos", "toman")


def inns(text):
    entry = CAT.resolve(text)
    return entry.inns if entry is not None else None


BISOPROLOL = frozenset({"bisoprolol"})
METOPROLOL = frozenset({"metoprolol"})


# --- b and v -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["visoprolol", "Visoprolol", "VISOPROLOL", "visoprolol 10 mg", "Tomo visoprolol",
                                  "bisoprolol", "Toma bisoprolol"])
def test_b_and_v_match_each_other(text):
    assert inns(text) == BISOPROLOL


def test_b_and_v_match_each_other_in_a_brand():
    assert inns("Veloc-Zok") == METOPROLOL
    assert inns("Beloc-Zok") == METOPROLOL


# --- one attached form of "tomar" --------------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["Tomobisoprolol", "tomobisoprolol", "Tomovisoprolol", "Tomabisoprolol",
                                  "tomasbisoprolol", "tomamosbisoprolol", "tomanvisoprolol",
                                  "Tomobisoprolol diez miligramos cada mañana", "TOMOVISOPROLOL"])
def test_one_attached_form_of_tomar_is_accepted(text):
    assert inns(text) == BISOPROLOL


def test_an_attached_form_before_a_brand():
    assert inns("Tomoemconcor") == BISOPROLOL
    assert inns("Tomaveloc-Zok") == METOPROLOL


@pytest.mark.parametrize("text", ["tomo", "Toma", "tomatobisoprolol", "atomobisoprolol", "tomotomobisoprolol",
                                  "tomobisoprololx", "xbisoprolol", "tomobisoprolol5", "tomsbisoprolol",
                                  "tomovisoprololes",
                                  # round 2 (the supervisor's #3): only b and v fold, and only the five forms attach
                                  "pisoprolol", "wisoprolol", "Peloc-Zok", "Norpasc", "tomóbisoprolol",
                                  "tomebisoprolol", "tomababisoprolol"])
def test_nothing_else_is_attached(text):
    assert CAT.resolve(text) is None


def test_the_attached_form_is_inside_the_match():
    for text in ("Tomobisoprolol", "tomovisoprolol", "visoprolol", "Tomoemconcor"):
        assert CAT.covers(text), text
    assert CAT.mentions_moiety("Tomovisoprolol", "bisoprolol")
    assert CAT.mentions_moiety("visoprolol", "bisoprolol")


# --- nothing else changes ----------------------------------------------------------------------------------------

def test_two_products_still_resolve_to_none():
    assert CAT.resolve("Tomovisoprolol y metoprolol") is None


@pytest.mark.parametrize("text", ["Tomoxyzzol", "vyzzol", "Xyzzol 20 mg", ""])
def test_an_unknown_name_stays_unknown(text):
    assert CAT.resolve(text) is None


def test_arabic_names_resolve_as_before():
    arabic = [(alias, entry.inns) for entry in CAT.entries for alias in entry.aliases
              if re.search(r"[؀-ۿ]", alias)]
    assert arabic
    for alias, expected in arabic:
        assert inns(alias) == expected, alias


# --- the catalogue keeps the rule safe ---------------------------------------------------------------------------

def _latin_names(entry):
    names = [entry.brand, *entry.aliases]
    if len(entry.inns) == 1:
        (moiety,) = entry.inns
        names += [moiety, *(alias for alias, (target, _) in INN_ALIASES.items() if target == moiety)]
    return [normalise(name) for name in names if not re.search(r"[؀-ۿ]", name)]


def test_no_two_products_share_a_name_once_v_is_written_b():
    seen = {}
    for entry in CAT.entries:
        for name in _latin_names(entry):
            assert seen.setdefault(name.replace("v", "b"), entry.inns) == entry.inns, name


def test_no_catalogue_name_starts_with_a_form_of_tomar():
    for entry in CAT.entries:
        for name in _latin_names(entry):
            assert not name.startswith(TOMAR), name


# --- the fourth set's claims, end to end -------------------------------------------------------------------------

def amt(inn, mg):
    return IngredientAmount(inn=inn, amount=Decimal(str(mg)), unit="mg")


def heard(cid, name, inn, label, mg, per_day, status="active"):
    return PatientClaim(claim_id=cid, name_text=name, inn=inn, strength=None, intake_amount=amt(label, mg),
                        regimen=DoseRegimen(units_per_intake=None, intakes_per_day=Decimal(per_day), as_needed=None),
                        status=status, audio_evidence=["turn-0"])


PACKS = [
    PackObservation(observation_id="o0", label_text="Emconcor® Cor 5 mg comprimidos recubiertos con película Fumarato "
                    "de bisoprolol Vía oral 28 comprimidos recubiertos con película MERCK 869750.2 TLD",
                    strength=Strength(ingredients=[amt("bisoprolol", 5)], per="tablet", release="immediate"),
                    readability="readable", country=None, visual_evidence=["ee726f8b6a51-0"]),
    PackObservation(observation_id="o1", label_text="Lopresor® 100 mg\ncomprimidos recubiertos\ncon película\n"
                    "Metoprolol, tartrato\n40 Comprimidos",
                    strength=Strength(ingredients=[amt("metoprolol", 100)], per="tablet", release="immediate"),
                    readability="readable", country=None, visual_evidence=["020d7e5597e7-0"]),
]

# (name_text, inn, intake label, status) as the fourth set's runs returned the bisoprolol claim
HEARD = [("Tomobisoprolol", None, "tomobisoprolol", "active"),           # r01, r09
         ("Tomovisoprolol", "tomovisoprolol", "tomovisoprolol", "active"),  # r02
         ("visoprolol", "visoprolol", "visoprolol", "active"),            # r03
         ("Tomovisoprolol", "tomovisoprolol", "tomovisoprolol", "unknown"),  # r05
         ("Tomovisoprolol", None, "tomovisoprolol", "unknown"),            # r06
         ("Tomovisoprolol", "Tomovisoprolol", "tomovisoprolol", "active"),  # r07
         ("Tomobisoprolol", "Tomobisoprolol", "tomobisoprolol", "active")]  # r10


@pytest.mark.parametrize("name,inn,label,status", HEARD)
def test_the_fourth_sets_claims_pair_with_their_boxes(name, inn, label, status):
    claims = [heard("c1", name, inn, label, 10, 1, status),
              heard("c2", "metoprolol", "metoprolol", "metoprolol", 100, 2, status)]
    found = {(f.type, f.claim_id, f.observation_id) for f in reconcile_all(claims, PACKS, CAT)}
    assert found == {(D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH, "c1", "o0"), (D.MATCH, "c2", "o1")}
    overlaps = cross_medication(claims, CAT)
    assert [(o.kind, o.claim_ids) for o in overlaps] == [(OverlapKind.SAME_CLASS, ("c1", "c2"))]


def test_the_claim_keeps_the_name_as_heard():
    claims = [heard("c1", "Tomovisoprolol", "tomovisoprolol", "tomovisoprolol", 10, 1)]
    reconcile_all(claims, PACKS, CAT)
    assert claims[0].name_text == "Tomovisoprolol"



# --- round 2: a name that carries a salt is matched only as written (the supervisor's #1) --------------------------

# the salt-bearing aliases the catalogue lists: those of its single-ingredient entries
SALTED = list(dict.fromkeys(alias for entry in CAT.entries if len(entry.inns) == 1
                            for alias, (target, salt) in INN_ALIASES.items() if salt and target in entry.inns))


def test_a_name_with_a_salt_is_matched_only_as_written():
    assert SALTED
    for alias in SALTED:
        name = normalise(alias)
        assert CAT.covers(name), alias
        swapped = name.translate(str.maketrans("bv", "vb"))
        if swapped != name:
            assert not CAT.covers(swapped), swapped
        assert not CAT.covers("tomo" + name), "tomo" + name


def salted(inn, mg, salt=None):
    return Strength(ingredients=[IngredientAmount(inn=inn, salt=salt, amount=Decimal(str(mg)), unit="mg")],
                    per="tablet", release="immediate")


def pair(name, inn, moiety, mg, label, salt):
    claim = PatientClaim(claim_id="c1", name_text=name, inn=inn, strength=salted(moiety, mg), intake_amount=None,
                         regimen=None, status="active", audio_evidence=["t"])
    pack = PackObservation(observation_id="o1", label_text=label, strength=salted(moiety, mg, salt),
                           readability="readable", country=None, visual_evidence=["r"])
    return reconcile_pair(claim, pack, CAT).type


@pytest.mark.parametrize("name,inn,moiety,mg,label,salt", [
    ("Metoprolol", "tomometoprolol succinate", "metoprolol", 100, "Metoprolol tartrate 100 mg", "tartrate"),
    ("amlodipine vesilate", "amlodipine vesilate", "amlodipine", 5, "Amlodipine maleate 5 mg", "maleate"),
    ("Bisoprolol", "visoprolol hemifumarate", "bisoprolol", 5, "Bisoprolol fumarate 5 mg", "fumarate"),
    ("Atorvastatin", "atorbastatin calcium", "atorvastatin", 20, "Atorvastatin calcium trihydrate 20 mg",
     "calcium trihydrate"),
])
def test_a_misspelled_salt_never_becomes_a_match(name, inn, moiety, mg, label, salt):
    assert pair(name, inn, moiety, mg, label, salt) is D.INSUFFICIENT_INFORMATION


def test_a_salt_spelled_as_written_still_disagrees():
    assert pair("Metoprolol", "metoprolol succinate", "metoprolol", 100, "Metoprolol tartrate 100 mg",
                "tartrate") is D.FORMULATION_MISMATCH
