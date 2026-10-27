"""Small synthetic catalogue for deterministic name resolution."""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


def _normalise(text: str) -> str:
    text = text.casefold().replace("®", "").replace("™", "")
    text = re.sub(r"(?<!\w)[/-]|[/-](?!\w)|[^\w\s/-]", " ", text)
    return " ".join(text.split())


@dataclass(frozen=True)
class CatalogueEntry:
    brand: str
    inns: frozenset[str]
    countries: tuple[str, ...]
    synthetic: bool


@dataclass(frozen=True)
class Catalogue:
    entries: tuple[CatalogueEntry, ...]

    def resolve(self, text: str, country: str | None = None) -> CatalogueEntry | None:
        """Best match for the text; the country is a preference, never a filter."""
        if country is not None:
            local = self._best(text, country.upper())
            if local is not None:
                return local
        return self._best(text, None)

    def _best(self, text: str, country: str | None) -> CatalogueEntry | None:
        normalised = _normalise(text)
        best: tuple[int, CatalogueEntry] | None = None
        for entry in self.entries:
            if country is not None and country not in entry.countries:
                continue
            names = [entry.brand]
            if len(entry.inns) == 1:
                names.extend(entry.inns)
            for name in names:
                candidate = _normalise(name)
                if re.search(rf"(?<!\w){re.escape(candidate)}(?!\w)", normalised):
                    if best is None or len(candidate) > best[0]:
                        best = (len(candidate), entry)
        return best[1] if best else None


def load_catalogue(path: str | Path | None = None) -> Catalogue:
    """Read catalogue entries from YAML, defaulting to the bundled file."""
    source = Path(path) if path is not None else Path(__file__).with_suffix(".yaml")
    with source.open(encoding="utf-8") as stream:
        records = yaml.safe_load(stream)
    return Catalogue(
        tuple(
            CatalogueEntry(
                brand=record["brand"],
                inns=frozenset(record["inns"]),
                countries=tuple(record["countries"]),
                synthetic=record["synthetic"],
            )
            for record in records
        )
    )
