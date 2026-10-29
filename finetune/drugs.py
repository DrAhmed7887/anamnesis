"""The fine-tune's drug vocabulary (plan.md, amended 29 Oct): the catalogue's 9 entries with their brands,
aliases and INNs, plus the 60 common medicines of evidence/data/rxnorm_drugs.json, 10 of them held out."""

import json
import random
import re
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

from anamnesis.core.catalogue import load_catalogue, normalise
from anamnesis.providers.numbers import parse_amount_text
from finetune.common import ROOT

RXNORM_FILE = ROOT / "evidence" / "data" / "rxnorm_drugs.json"
# r2's Spanish vocabulary (plan.md, amended 29 Oct): scripts/drugs_v2.py's brands from AEMPS CIMA.
DRUGS_V2_FILE = ROOT / "evidence" / "data" / "drugs_v2.json"
HELD_OUT_COUNT = 10
SPAIN_HELD_SHARE = 5  # one new Spanish brand in five is held out of r2's training, for test_spain
# U11's real note names ibuprofen, so it stays a training drug: test_real then measures speech-to-text noise
# on drugs the model has seen, and test_shift alone measures unseen drugs.
REAL_SLICE_INNS = ("ibuprofen",)

# Brand rule. RxNorm's brand strings are uncurated (store brands, "Zantac Reformulated Aug 2022"), so a brand
# is kept only if a patient would plausibly say it:
# - one or two words, each of ASCII letters only: no digits (so no years), no hyphens or other marks;
# - its first word (split at spaces and hyphens) is not a store or labeler mark from STORE_MARKS;
# - it doesn't contain its own ingredient's name ("Bayer Aspirin"): saying it would be saying the ingredient,
#   and the claim's inn field would become ambiguous.
# A name written in capitals is put in title case ("MILLIPRED" is said "Millipred").
STORE_MARKS = ("wal", "aller", "mapap", "equate", "cvs", "kirkland", "walgreens", "sunmark", "topcare",
               "goodsense", "leader")


@dataclass(frozen=True)
class Strength:
    """A marketed oral strength from RxNorm, in mg, and the solid forms it is sold in."""

    mg: Decimal
    forms: tuple[str, ...]  # "tablet", "capsule"


@dataclass(frozen=True)
class Medicine:
    key: str  # "catalogue:Concor" or "rxnorm:amlodipine"
    source: str
    inns: tuple[str, ...]
    rxcui: str | None
    brands: tuple[str, ...]  # Latin script
    aliases: tuple[str, ...]  # Arabic script, catalogue entries only
    ingredient_names: tuple[str, ...]  # what a patient may say for a single ingredient; () for combinations
    strengths: tuple[Strength, ...]


def usable_brand(name: str, ingredient_names: tuple[str, ...]) -> str | None:
    """The brand as a patient would say it, or None when the brand rule above leaves it out."""
    words = name.split()
    first = re.split(r"[\s-]+", name.strip())[0].casefold()
    if first in STORE_MARKS or not 1 <= len(words) <= 2:
        return None
    if not all(word.isascii() and word.isalpha() for word in words):
        return None
    if any(f" {ingredient.casefold()} " in f" {name.casefold()} " for ingredient in ingredient_names):
        return None
    return name.title() if name.isupper() else name


def usable_strengths(record: dict[str, Any]) -> tuple[Strength, ...]:
    """Only strengths RxNorm lists for the medicine: MG amounts sold as a tablet or capsule. MG/ML strengths
    are left out (a patient states a liquid as a volume, not as its concentration), and so is any value the
    product's number rules can't write (3.125: a dot and three digits reads as a thousands mark)."""
    kept = []
    for strength in record["oral_strengths"]:
        if strength["unit"] != "MG":
            continue
        forms = tuple(
            form for form in ("tablet", "capsule")
            if any(form in dose_form.casefold() for dose_form in strength["dose_forms"])
        )
        value = parse_amount_text(strength["value"])
        if forms and value is not None and value == Decimal(strength["value"]):
            kept.append(Strength(Decimal(strength["value"]), forms))
    return tuple(kept)


def _rxnorm_records() -> list[dict[str, Any]]:
    data = json.loads(RXNORM_FILE.read_text(encoding="utf-8"))
    records = data["drugs"]
    if len(records) != 60 or any(record["status"] != "mapped" for record in records):
        raise ValueError(f"{RXNORM_FILE} should hold 60 mapped medicines")
    return records


def _ingredient_names(record: dict[str, Any]) -> tuple[str, ...]:
    """The INN, and RxNorm's name when it differs (acetaminophen, aspirin, alendronate)."""
    inn, rxnorm_name = record["inn"], record["rxnorm_name"]
    return (inn,) if rxnorm_name == inn else (inn, rxnorm_name)


def load_medicines() -> list[Medicine]:
    """Catalogue entries first (catalogue order), then RxNorm's 60 (file order)."""
    records = _rxnorm_records()
    by_inn = {record["inn"]: record for record in records}
    medicines = []
    for entry in load_catalogue().entries:
        inns = tuple(sorted(entry.inns))
        record = by_inn.get(inns[0]) if len(inns) == 1 else None
        medicines.append(Medicine(
            key=f"catalogue:{entry.brand}",
            source="catalogue",
            inns=inns,
            rxcui=record["rxcui"] if record else None,
            brands=(entry.brand,),
            aliases=entry.aliases,
            ingredient_names=_ingredient_names(record) if record else (inns if len(inns) == 1 else ()),
            # A combination's strengths aren't in the RxNorm file (it keeps single ingredients), so a
            # combination is only ever mentioned without an amount.
            strengths=usable_strengths(record) if record else (),
        ))
    for record in records:
        names = _ingredient_names(record)
        brands = (usable_brand(brand["name"], names) for brand in record["brands"])
        medicines.append(Medicine(
            key=f"rxnorm:{record['inn']}",
            source="rxnorm",
            inns=(record["inn"],),
            rxcui=record["rxcui"],
            brands=tuple(brand for brand in brands if brand),
            aliases=(),
            ingredient_names=names,
            strengths=usable_strengths(record),
        ))
    return medicines


def _v2_records() -> dict[str, dict[str, Any]]:
    """The Spanish vocabulary of scripts/drugs_v2.py (AEMPS CIMA), by INN, mapped medicines only."""
    data = json.loads(DRUGS_V2_FILE.read_text(encoding="utf-8"))
    return {record["inn"]: record for record in data["drugs"] if record["status"] == "mapped"}


def spanish_strengths(record: dict[str, Any]) -> tuple[Strength, ...]:
    """The strengths CIMA's product names print, by the same number rule as usable_strengths."""
    forms = tuple(form for form in ("tablet", "capsule") if form in record.get("forms", ()))
    kept = []
    for text in record["strengths_mg"]:
        value = parse_amount_text(text)
        if forms and value is not None and value == Decimal(text):
            kept.append(Strength(Decimal(text), forms))
    return tuple(kept)


def _merged(us: tuple[Strength, ...], spain: tuple[Strength, ...]) -> tuple[Strength, ...]:
    """Both markets' strengths, each amount once, its forms joined; US order first."""
    forms: dict[Decimal, list[str]] = {}
    for strength in (*us, *spain):
        forms.setdefault(strength.mg, [])
        forms[strength.mg] += [form for form in strength.forms if form not in forms[strength.mg]]
    return tuple(Strength(mg, tuple(found)) for mg, found in forms.items())


def spain_split(medicines: list[Medicine], held: tuple[str, ...], seed: int) -> tuple[dict, dict]:
    """The Spanish brands of the training RxNorm medicines: (trained, held out for test_spain), by INN.
    Only brands that are new names count (a global brand such as Diovan is already a US name). One in
    SPAIN_HELD_SHARE of them is held out, drawn with the seed; no held name may name anything else."""
    records = _v2_records()
    known = {normalise(name) for medicine in medicines for name in all_names(medicine)}
    new = sorted(
        (medicine.inns[0], brand["name"])
        for medicine in medicines
        if medicine.source == "rxnorm" and medicine.key not in held and medicine.inns[0] in records
        for brand in records[medicine.inns[0]]["brands"]
        if normalise(brand["name"]) not in known
    )
    chosen = set(random.Random(seed).sample(new, len(new) // SPAIN_HELD_SHARE))
    trained: dict[str, tuple[str, ...]] = {}
    held_out: dict[str, tuple[str, ...]] = {}
    for inn, brand in new:
        target = held_out if (inn, brand) in chosen else trained
        target[inn] = (*target.get(inn, ()), brand)
    taken = {normalise(name) for names in trained.values() for name in names} | known
    clashes = sorted(name for names in held_out.values() for name in names if normalise(name) in taken)
    if clashes:
        raise ValueError(f"held-out Spanish brands also name a training medicine: {clashes}")
    return trained, held_out


def load_medicines_v2(spanish: dict[str, tuple[str, ...]]) -> list[Medicine]:
    """load_medicines() with each RxNorm medicine's trained Spanish brands and Spain's strengths added."""
    records = _v2_records()
    return [
        replace(medicine, brands=(*medicine.brands, *spanish.get(medicine.inns[0], ())),
                strengths=_merged(medicine.strengths, spanish_strengths(records[medicine.inns[0]])))
        if medicine.source == "rxnorm" and medicine.inns[0] in records else medicine
        for medicine in load_medicines()
    ]


def spain_medicines(held_out: dict[str, tuple[str, ...]], medicines: list[Medicine]) -> list[Medicine]:
    """test_spain's pool: each INN with held-out Spanish brands, said by those brands only (no ingredient
    names, so every mention says a name the model never saw), with Spain's strengths, else the US ones."""
    records = _v2_records()
    us = {medicine.inns[0]: medicine for medicine in medicines if medicine.source == "rxnorm"}
    return [
        Medicine(key=f"cima:{inn}", source="cima", inns=(inn,), rxcui=us[inn].rxcui, brands=brands,
                 aliases=(), ingredient_names=(),
                 strengths=spanish_strengths(records[inn]) or us[inn].strengths)
        for inn, brands in sorted(held_out.items())
    ]


def dropped_brands() -> list[str]:
    """RxNorm brand strings the brand rule leaves out, for the record."""
    dropped = []
    for record in _rxnorm_records():
        for brand in record["brands"]:
            if usable_brand(brand["name"], _ingredient_names(record)) is None:
                dropped.append(brand["name"])
    return dropped


def all_names(medicine: Medicine) -> tuple[str, ...]:
    return medicine.brands + medicine.aliases + medicine.ingredient_names


def held_out_keys(medicines: list[Medicine], seed: int) -> tuple[str, ...]:
    """Ten RxNorm medicines drawn with the seed. Eligible: a marketed strength to say, no INN shared with a
    catalogue entry (holding one of those out would take a catalogue brand with it), and not in the real
    slice.
    Fails if any of their names is also a name of a training medicine."""
    catalogue_inns = {inn for item in medicines if item.source == "catalogue" for inn in item.inns}
    eligible = sorted(
        medicine.key for medicine in medicines
        if medicine.source == "rxnorm" and medicine.strengths
        and medicine.inns[0] not in catalogue_inns and medicine.inns[0] not in REAL_SLICE_INNS
    )
    chosen = tuple(sorted(random.Random(seed).sample(eligible, HELD_OUT_COUNT)))
    held = {normalise(name) for item in medicines if item.key in chosen for name in all_names(item)}
    kept = {normalise(name) for item in medicines if item.key not in chosen for name in all_names(item)}
    if held & kept:
        raise ValueError(f"held-out names also name a training medicine: {sorted(held & kept)}")
    return chosen
