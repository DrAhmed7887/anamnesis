"""Cross-medication observations from what the patient reports (SPEC §7)."""

from dataclasses import dataclass
from enum import StrEnum

from anamnesis.core.catalogue import Catalogue, normalise
from anamnesis.core.reconcile import _claim_identity
from anamnesis.schema.templates import SAME_CLASS_NOTE, SAME_INGREDIENT_NOTE


class OverlapKind(StrEnum):
    SAME_INGREDIENT = "same_ingredient"
    SAME_CLASS = "same_class"


@dataclass(frozen=True)
class Overlap:
    kind: OverlapKind
    key: str
    claim_ids: tuple[str, ...]
    audio_evidence: tuple[str, ...]
    note: str


DRUG_CLASSES: dict[str, frozenset[str]] = {
    "beta-blockers": frozenset({"bisoprolol", "metoprolol"}),
}


def _counted(claims, catalogue: Catalogue):
    """Claims with a buildable identity set that were not reported as stopped."""
    counted = []
    for claim in claims:
        if claim.status.value == "discontinued":
            continue
        inns, _ = _claim_identity(claim, catalogue)
        if inns is None:
            continue
        entry = catalogue.brand_entry(claim.name_text)
        product = entry.brand if entry is not None else normalise(claim.name_text)
        counted.append((claim, frozenset(inns), product))
    return counted


def _observation(kind: OverlapKind, key: str, claims, note: str) -> Overlap:
    ids = tuple(sorted(claim.claim_id for claim in claims))
    turns = tuple(sorted({turn for claim in claims for turn in claim.audio_evidence}))
    return Overlap(kind=kind, key=key, claim_ids=ids, audio_evidence=turns, note=note)


def cross_medication(claims, catalogue: Catalogue) -> list[Overlap]:
    """One observation per INN or class with 2+ different products (SPEC §7)."""
    counted = _counted(claims, catalogue)
    found: list[Overlap] = []
    inns = sorted({inn for _, sets, _ in counted for inn in sets})
    for inn in inns:
        holders = [claim for claim, sets, _ in counted if inn in sets]
        products = {product for claim, sets, product in counted if inn in sets}
        if len(products) >= 2:
            found.append(_observation(OverlapKind.SAME_INGREDIENT, inn, holders, SAME_INGREDIENT_NOTE))
    for name in sorted(DRUG_CLASSES):
        members = DRUG_CLASSES[name]
        holders = [claim for claim, sets, _ in counted if sets & members]
        seen = {inn for _, sets, _ in counted for inn in sets & members}
        products = {product for claim, sets, product in counted if sets & members}
        if len(seen) >= 2 and len(products) >= 2:
            found.append(_observation(OverlapKind.SAME_CLASS, name, holders, SAME_CLASS_NOTE))
    return found


__all__ = ["DRUG_CLASSES", "Overlap", "OverlapKind", "cross_medication"]
