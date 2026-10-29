# ruff: noqa: E501
"""The rules behind manifest.md's expected findings, checked before any live call (29 Oct): the reconciler on
each case's likely claim and pack shapes, with no model and no network. From the repo root:

    PYTHONPATH=. .venv/bin/python evidence/batches/24/expected_check.py

Batch 24a's grounding runs in the claim parser, before the reconciler, so an unsaid INN is passed here as None.
The "pre-24a" rows show what an INN the model adds would change.
"""

from decimal import Decimal

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all
from anamnesis.schema import IngredientAmount, PackObservation, PatientClaim, Strength
from anamnesis.schema.medication import DoseRegimen


def mg(inn, amount, salt=None):
    return IngredientAmount(inn=inn, amount=Decimal(str(amount)), unit="mg", salt=salt)


def claim(name, inn=None, strength=None, intake=None, units=None, per_day=None, prn=None, status="active"):
    regimen = None
    if units or per_day or prn:
        regimen = DoseRegimen(units_per_intake=Decimal(str(units)) if units else None,
                              intakes_per_day=Decimal(per_day) if per_day else None, as_needed=prn)
    return PatientClaim(claim_id="c1", name_text=name, inn=inn, status=status, audio_evidence=["t1"],
                        strength=Strength(ingredients=[strength], per="tablet", release="unknown") if strength
                        else None, intake_amount=intake, regimen=regimen)


def pack(label, part, readability="readable"):
    return PackObservation(observation_id="o1", label_text=label, readability=readability, visual_evidence=["r1"],
                           strength=Strength(ingredients=[part], per="tablet", release="unknown") if part else None)


BISOPROLOL = pack("Bisoprolol Orion 2,5 mg", mg("bisoprolol", 2.5, "fumarate"))
METOPROLOL = pack("Metoprolol-ratiopharm 50 mg", mg("metoprolol", 50, "tartrate"))
CASES = {
    "S1": ([claim("Emconcor", intake=mg("Emconcor", 5), per_day=1)], []),
    "S1, model's INN kept (pre-24a)": ([claim("Emconcor", inn="bisoprolol", intake=mg("bisoprolol", 5), per_day=1)], []),
    "S2, as a strength": ([claim("bisoprolol", inn="bisoprolol", strength=mg("bisoprolol", 2.5))], [BISOPROLOL]),
    "S2, as an intake": ([claim("bisoprolol", inn="bisoprolol", intake=mg("bisoprolol", 2.5))], [BISOPROLOL]),
    "S3": ([claim("Gelocatil", intake=IngredientAmount(inn="Gelocatil", amount=Decimal(1), unit="g"), prn=True)], []),
    "S4": ([claim("Panadol", strength=mg("paracetamol", 500), units=0.5)], [pack("Panadol 500 mg", mg("paracetamol", 500))]),
    "G1, as an intake": ([claim("Metoprolol", inn="metoprolol", intake=mg("metoprolol", 50), per_day=2)], [METOPROLOL]),
    "G1, as a strength": ([claim("Metoprolol", inn="metoprolol", strength=mg("metoprolol", 50), per_day=2)],
                          [METOPROLOL]),
    "G1, pack partial": ([claim("Metoprolol", inn="metoprolol", intake=mg("metoprolol", 50), per_day=2)],
                         [pack("Metoprolol-ratiopharm 50", None, "partial")]),
    "G2": ([claim("Beloc-Zok", strength=mg("Beloc-Zok", 100), units=0.5)], []),
    "G3": ([claim("Sortis", intake=mg("Sortis", 40))], [pack("Sortis 40 mg", mg("atorvastatin", 40))]),
    "G3, pack partial": ([claim("Sortis", intake=mg("Sortis", 40))], [pack("Sortis 40", None, "partial")]),
    "G3, model's INN kept (pre-24a)": ([claim("Sortis", inn="atorvastatin", intake=mg("atorvastatin", 40))],
                                       [pack("Sortis 40 mg", mg("atorvastatin", 40))]),
    "G4": ([claim("Ibuprofen", inn="ibuprofen", intake=mg("ibuprofen", 400), status="discontinued")], []),
}

if __name__ == "__main__":
    catalogue = load_catalogue()
    for name, (claims, packs) in CASES.items():
        found = reconcile_all(claims, packs, catalogue)
        print(f"{name:32}", ", ".join(f"{f.type.value} ({f.claim_id}, {f.observation_id})" for f in found))
