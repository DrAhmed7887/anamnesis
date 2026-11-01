"""Score the Spanish hero's ten runs (U13, 1 Nov) as `plan.md` set out before any call: Emconcor
`intake_differs_from_unit_strength`, metoprolol against the Lopresor box `match`, and the beta-blocker note.
The rules of `evidence/diagnostics/hero-claims-2026-10-31/score_rerun.py`, with this case's names and boxes.

    PYTHONPATH=. uv run python evidence/diagnostics/hero-es-2026-11-01/score.py evidence/live/2026-11-01
"""

import sys
from decimal import Decimal
from pathlib import Path

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.overlap import cross_medication
from anamnesis.schema import ReconciliationReport
from anamnesis.schema.medication import canonical_inn

CATALOGUE = load_catalogue()
PRINTED_MG = {"bisoprolol": {Decimal(5)}, "metoprolol": {Decimal(100)}}  # what the two boxes print
# Each claim: the names it may be heard as, the ingredient to find it by otherwise, and its expected finding.
EXPECTED = {"emconcor": (("concor",), "bisoprolol", "intake_differs_from_unit_strength"),
            "metoprolol": (("metoprol", "lopres"), "metoprolol", "match")}


def amounts(strength) -> list[tuple[str, Decimal]]:
    return [(part.inn.split()[0], part.amount) for part in (strength.ingredients if strength else [])
            if part.unit.value == "mg"]


def find(report: ReconciliationReport, names: tuple[str, ...], inn: str):
    for claim in report.claims:
        if any(name in claim.name_text.casefold().replace("-", "") for name in names):
            return claim
    return next((c for c in report.claims if c.inn and canonical_inn(c.inn) == inn), None)


def score(report: ReconciliationReport) -> tuple[bool, list[str], list[str]]:
    harms = [f"{o.observation_id} reads {inn} {mg} mg" for o in report.observations
             if o.readability.value == "readable" for inn, mg in amounts(o.strength)
             if mg not in PRINTED_MG.get(inn, {mg})]
    verdicts, ok = [], True
    for key, (names, inn, want) in EXPECTED.items():
        claim = find(report, names, inn)
        finding = next((f for f in report.findings if claim and f.claim_id == claim.claim_id), None)
        got = finding.type.value if finding else "no claim"
        verdicts.append(f"{key}: {got}")
        ok &= got == want
        if key == "emconcor" and got == "match":
            harms.append("a false match on Emconcor")
    kinds = sorted({overlap.kind.value for overlap in cross_medication(report.claims, CATALOGUE)})
    verdicts.append(f"across: {', '.join(kinds) or 'none'}")
    ok &= "same_class" in kinds
    return ok, verdicts, harms


def main() -> None:
    runs = sorted(Path(sys.argv[1]).glob("report_U13_r*.json"))
    correct = harmed = 0
    for path in runs:
        report = ReconciliationReport.model_validate_json(path.read_text(encoding="utf-8"))
        ok, verdicts, harms = score(report)
        correct += ok
        harmed += bool(harms)
        transcript = " / ".join(turn.transcript for turn in report.turns)
        print(f"{path.stem[7:]:8} {'correct' if ok else 'miss':7} {' | '.join(verdicts)}"
              + (f" | HARM: {'; '.join(harms)}" if harms else "") + f" | heard: {transcript}")
    print(f"{correct} of {len(runs)} correct, {harmed} with a harm")


if __name__ == "__main__":
    main()
