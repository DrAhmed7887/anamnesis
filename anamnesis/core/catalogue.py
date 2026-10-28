"""Small synthetic catalogue for deterministic name resolution."""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from anamnesis.schema.medication import INN_ALIASES, Release, canonical_inn


def normalise(text: str) -> str:
    """Casefold, strip Arabic marks and punctuation, split scripts: the one matching form."""
    text = text.casefold().replace("®", "").replace("™", "")
    text = re.sub(r"[\u0640\u064b-\u065f\u0670]", "", text)
    text = text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"}))
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"))
    text = re.sub(r"(?<=[\u0600-\u06ff])(?=[a-z])|(?<=[a-z])(?=[\u0600-\u06ff])", " ", text)
    text = re.sub(r"[^\w\s]|_", " ", text)
    return " ".join(text.split())


ARABIC_CLITICS = r"(?:وال|بال|فال|لل|ال|و|ف|ب|ل)?"
"""Attached Arabic clitics accepted before a matched word (SPEC §2, §3)."""


@dataclass(frozen=True)
class CatalogueEntry:
    brand: str
    inns: frozenset[str]
    countries: tuple[str, ...]
    synthetic: bool
    release: Release
    splittable: bool | None
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Catalogue:
    entries: tuple[CatalogueEntry, ...]

    def resolve(self, text: str, country: str | None = None) -> CatalogueEntry | None:
        """Resolve one product name, preferring country only among equivalent names."""
        matches = self._matches(text)
        if not matches:
            return None
        maximal = [
            match
            for match in matches
            if not any(
                other[0] <= match[0]
                and match[1] <= other[1]
                and other[1] - other[0] > match[1] - match[0]
                for other in matches
            )
        ]
        brands = [match for match in maximal if match[3]]
        if brands:
            brand_products = {(entry.brand, entry.inns) for _, _, entry, _ in brands}
            if len(brand_products) != 1:
                return None
            brand_inns = brands[0][2].inns
            remaining = [
                match
                for match in maximal
                if match[3] or not any(match[2].inns <= brand[2].inns for brand in brands)
            ]
            if any(entry.inns != brand_inns for _, _, entry, _ in remaining):
                return None
            entries = [entry for _, _, entry, _ in brands]
        else:
            inn_sets = {entry.inns for _, _, entry, _ in maximal}
            if len(inn_sets) != 1:
                return None
            entries = [entry for _, _, entry, _ in maximal]
        entries = list(dict.fromkeys(entries))
        country_code = country.upper() if country else None
        entries.sort(
            key=lambda entry: (
                country_code is None or country_code not in {c.upper() for c in entry.countries},
                entry.brand.casefold(),
                entry.countries,
            )
        )
        return entries[0]

    def is_ambiguous(self, text: str) -> bool:
        """True when the text matches entries but names 2+ different products."""
        return bool(self._matches(text)) and self.resolve(text) is None

    def matches_brand(self, text: str) -> bool:
        """True when the text matches a catalogue brand or alias name."""
        return any(brand for _, _, _, brand in self._matches(text))

    def mentions_moiety(self, text: str, moiety: str) -> bool:
        """True when the text names the moiety, or a brand whose only INN is that moiety, as whole words."""
        if f" {normalise(moiety)} " in f" {normalise(text)} ":
            return True
        return any(entry.inns == frozenset({moiety}) for _, _, entry, _ in self._matches(text))

    def _matches(self, text: str) -> list[tuple[int, int, CatalogueEntry, bool]]:
        normalised = normalise(text)
        matches = []
        for entry in self.entries:
            names = [(entry.brand, True)]
            names.extend((alias, True) for alias in entry.aliases)
            if len(entry.inns) == 1:
                (moiety,) = entry.inns
                aliases = [alias for alias, (target, _) in INN_ALIASES.items() if target == moiety]
                names.extend((name, False) for name in (moiety, *aliases))
            for raw, brand in names:
                name = normalise(raw)
                variants = [name]
                if brand and " " in name:
                    variants.append(name.replace(" ", ""))
                for variant in dict.fromkeys(variants):
                    prefix = ARABIC_CLITICS if re.search(r"[\u0600-\u06ff]", name) else ""
                    pattern = re.compile(rf"(?<!\w){prefix}{re.escape(variant)}(?!\w)")
                    matches.extend(
                        (found.start(), found.end(), entry, brand)
                        for found in pattern.finditer(normalised)
                    )
        return matches

    def _brand_entry(self, text: str, country: str | None = None) -> CatalogueEntry | None:
        entry = self.resolve(text, country)
        if entry is None:
            return None
        return entry if any(e is entry and brand for _, _, e, brand in self._matches(text)) else None

    def brand_entry(self, text: str, country: str | None = None) -> CatalogueEntry | None:
        """The resolved entry, only when the text matched its brand or alias name."""
        return self._brand_entry(text, country)

    def implied_release(self, text: str, country: str | None = None) -> Release:
        entry = self._brand_entry(text, country)
        return entry.release if entry else Release.UNKNOWN

    def splittable(self, text: str, country: str | None = None) -> bool | None:
        entry = self._brand_entry(text, country)
        return entry.splittable if entry else None


def load_catalogue(path: str | Path | None = None) -> Catalogue:
    """Read catalogue entries from YAML, defaulting to the bundled file."""
    source = Path(path) if path is not None else Path(__file__).with_suffix(".yaml")
    with source.open(encoding="utf-8") as stream:
        records = yaml.safe_load(stream)
    return Catalogue(
        tuple(
            CatalogueEntry(
                brand=record["brand"],
                inns=frozenset(canonical_inn(inn) for inn in record["inns"]),
                countries=tuple(record["countries"]),
                synthetic=record["synthetic"],
                release=Release(record["release"]),
                splittable=record["splittable"],
                aliases=tuple(record.get("aliases", ())),
            )
            for record in records
        )
    )
