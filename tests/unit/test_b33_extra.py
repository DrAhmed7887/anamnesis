"""Extra offline checks for batch 33: a salt inside a longer ingredient label is read."""

from decimal import Decimal

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import _nominal_pack_amount, _side_salts, reconcile_pair
from anamnesis.schema import (
    INN_ALIASES,
    SALT_BASIS_EQUIVALENTS,
    IngredientAmount,
    PackObservation,
    PatientClaim,
    Strength,
)
from anamnesis.schema import DiscrepancyType as D

CAT = load_catalogue()

SALTED = {alias: target for alias, target in INN_ALIASES.items() if target[1]}
"""Curated aliases that carry a salt: every one must read inside a longer label."""

MOIETY_SALTS: dict[str, set[str]] = {}
for _moiety, _salt in SALTED.values():
    MOIETY_SALTS.setdefault(_moiety, set()).add(_salt)

SINGLE_MOIETIES = {inn for entry in CAT.entries if len(entry.inns) == 1 for inn in entry.inns}
"""Moieties with a single-ingredient entry: longer labels still resolve to them."""


def _strength(label: str, mg: object = 100) -> Strength:
    return Strength(
        ingredients=[IngredientAmount(inn=label, amount=Decimal(str(mg)), unit="mg")],
        per="tablet",
        release="immediate",
    )


def _claim_with_strength(label: str, mg: object, name: str) -> PatientClaim:
    return PatientClaim(
        claim_id="c1",
        name_text=name,
        inn=None,
        strength=_strength(label, mg),
        intake_amount=None,
        regimen=None,
        status="active",
        audio_evidence=["t1"],
    )


def _pack_with_strength(label_text: str, part: str, mg: object) -> PackObservation:
    return PackObservation(
        observation_id="o1",
        label_text=label_text,
        inn=None,
        strength=_strength(part, mg),
        readability="readable",
        country=None,
        visual_evidence=["r1"],
    )


def test_every_salted_alias_reads_inside_a_longer_strength_label():
    assert SALTED
    for alias, (moiety, salt) in SALTED.items():
        found = _side_salts(_strength(f"{alias} 100 mg"), None, None, moiety, CAT)
        assert found.get(moiety) == frozenset({salt}), alias


def test_every_salted_alias_reads_inside_a_longer_intake_label():
    assert SALTED
    for alias, (moiety, salt) in SALTED.items():
        intake = IngredientAmount(inn=f"{alias} 100 mg", amount=Decimal(100), unit="mg")
        found = _side_salts(None, intake, None, moiety, CAT)
        assert found.get(moiety) == frozenset({salt}), alias


def test_a_loose_salt_word_counts_when_the_label_names_its_moiety():
    pairs = {(moiety, salt) for moiety, salt in SALTED.values()}
    assert pairs
    for moiety, salt in pairs:
        found = _side_salts(_strength(f"{moiety} (as {salt})"), None, None, moiety, CAT)
        assert found.get(moiety) == frozenset({salt}), (moiety, salt)


def test_a_brand_plus_salt_word_in_a_label_counts():
    count = 0
    for entry in CAT.entries:
        if len(entry.inns) != 1:
            continue
        (moiety,) = entry.inns
        for salt in MOIETY_SALTS.get(moiety, ()):
            count += 1
            found = _side_salts(_strength(f"{entry.brand} {salt}"), None, None, moiety, CAT)
            assert found.get(moiety) == frozenset({salt}), (entry.brand, salt)
    assert count


def test_a_label_without_a_salt_adds_nothing():
    moieties = {moiety for moiety, _ in SALTED.values()}
    assert moieties
    for moiety in moieties:
        assert _side_salts(_strength(f"{moiety} 100 mg"), None, None, moiety, CAT) == {}
        intake = IngredientAmount(inn=f"{moiety} 100 mg", amount=Decimal(100), unit="mg")
        assert _side_salts(None, intake, None, moiety, CAT) == {}


def test_the_scalar_inn_keeps_its_exact_reading():
    assert SALTED
    for alias, (moiety, _salt) in SALTED.items():
        found = _side_salts(None, None, f"tomo {alias}", moiety, CAT)
        assert found == {}, alias


def test_a_pack_longer_label_mismatches_an_exact_claim_salt():
    checked = 0
    for moiety, salts in MOIETY_SALTS.items():
        if moiety not in SINGLE_MOIETIES or len(salts) < 2:
            continue
        by_salt: dict[str, str] = {}
        for alias, (target, salt) in SALTED.items():
            if target == moiety and salt not in by_salt:
                by_salt[salt] = alias
        ordered = sorted(by_salt)
        for first, second in zip(ordered, ordered[1:], strict=False):
            checked += 1
            claim = _claim_with_strength(by_salt[first], 100, moiety)
            pack = _pack_with_strength(f"{moiety} 100 mg", f"{by_salt[second]} 100 mg", 100)
            assert reconcile_pair(claim, pack, CAT).type is D.FORMULATION_MISMATCH, (first, second)
            same = _pack_with_strength(f"{moiety} 100 mg", f"{by_salt[first]} 100 mg", 100)
            assert reconcile_pair(claim, same, CAT).type is D.MATCH, first
    assert checked


def test_the_nominal_lookup_ignores_a_longer_pack_label():
    assert SALT_BASIS_EQUIVALENTS
    for (inn, salt, amount), nominal in SALT_BASIS_EQUIVALENTS.items():
        claim = _claim_with_strength(inn, nominal, inn)
        exact = IngredientAmount(inn=f"{inn} {salt}", amount=amount, unit="mg")
        longer = IngredientAmount(inn=f"{inn} {salt} retard", amount=amount, unit="mg")
        assert _nominal_pack_amount(claim, exact, CAT) == nominal
        assert _nominal_pack_amount(claim, longer, CAT) is None
