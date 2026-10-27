"""Small synthetic catalogue for deterministic name resolution."""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from anamnesis.schema.medication import INN_ALIASES, Release, canonical_inn


def _normalise(text: str) -> str:
    text = text.casefold().replace("®", "").replace("™", "")
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


@dataclass(frozen=True)
class CatalogueEntry:
    brand: str
    inns: frozenset[str]
    countries: tuple[str, ...]
    synthetic: bool
    release: Release
    splittable: bool | None


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
                entry.brand.casefold(),
                country_code is not None and country_code not in entry.countries,
                entry.countries,
            )
        )
        return entries[0]

    def _matches(self, text: str) -> list[tuple[int, int, CatalogueEntry, bool]]:
        normalised = _normalise(text)
        matches = []
        for entry in self.entries:
            names = [(entry.brand, True)]
            if len(entry.inns) == 1:
                (moiety,) = entry.inns
                aliases = [alias for alias, (target, _) in INN_ALIASES.items() if target == moiety]
                names.extend((name, False) for name in (moiety, *aliases))
            for raw, brand in names:
                name = _normalise(raw)
                variants = [name]
                if brand and " " in name:
                    variants.append(name.replace(" ", ""))
                for variant in dict.fromkeys(variants):
                    pattern = re.compile(rf"(?<!\w){re.escape(variant)}(?!\w)")
                    matches.extend(
                        (found.start(), found.end(), entry, brand)
                        for found in pattern.finditer(normalised)
                    )
        return matches

    def _brand_entry(self, text: str) -> CatalogueEntry | None:
        entry = self.resolve(text)
        if entry is None:
            return None
        return entry if any(e is entry and brand for _, _, e, brand in self._matches(text)) else None

    def implied_release(self, text: str) -> Release:
        entry = self._brand_entry(text)
        return entry.release if entry else Release.UNKNOWN

    def splittable(self, text: str) -> bool | None:
        entry = self._brand_entry(text)
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
            )
            for record in records
        )
    )
