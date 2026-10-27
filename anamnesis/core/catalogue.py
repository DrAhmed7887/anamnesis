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
            (name, entry, brand)
            for name, entry, brand in matches
            if not any(name != other and name in other for other, _, _ in matches)
        ]
        products = {entry.brand for _, entry, _ in maximal}
        if len(products) != 1:
            return None
        entries = [entry for _, entry, _ in maximal]
        if country:
            entries.sort(key=lambda entry: country.upper() not in entry.countries)
        return entries[0]

    def _matches(self, text: str) -> list[tuple[str, CatalogueEntry, bool]]:
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
                if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", normalised):
                    matches.append((name, entry, brand))
        return matches

    def _brand_entry(self, text: str) -> CatalogueEntry | None:
        entry = self.resolve(text)
        if entry is None:
            return None
        return entry if any(e is entry and brand for _, e, brand in self._matches(text)) else None

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
