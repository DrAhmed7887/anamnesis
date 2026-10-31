"""Score the hero's ten fresh runs (31 Oct) both ways, as `hero-rerun-plan.md` set out before any call:
as registered on 28 Oct (Concor `strength_mismatch`), and with the system's own categories (Concor
`intake_differs_from_unit_strength`). Same rules as `evidence/batches/21/u12_score.py` otherwise.

    PYTHONPATH=. uv run python evidence/diagnostics/hero-claims-2026-10-31/score_rerun.py \
        evidence/live/2026-10-31
"""

import sys
from decimal import Decimal
from pathlib import Path

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.overlap import cross_medication
from anamnesis.schema import ReconciliationReport

CATALOGUE = load_catalogue()
PRINTED_MG = {"bisoprolol": {Decimal(5)}, "metoprolol": {Decimal(50)}}  # what the two boxes print
WAYS = {"registered": {"concor": "strength_mismatch", "beloc": "match"},
        "own categories": {"concor": "intake_differs_from_unit_strength", "beloc": "match"}}


def amounts(strength) -> list[tuple[str, Decimal]]:
    return [(part.inn.split()[0], part.amount) for part in (strength.ingredients if strength else [])
            if part.unit.value == "mg"]


def score(report: ReconciliationReport, expected: dict) -> tuple[bool, list[str], list[str]]:
    observations = {o.observation_id: o for o in report.observations}
    harms = [f"{o.observation_id} reads {inn} {mg} mg" for o in observations.values()
             if o.readability.value == "readable" for inn, mg in amounts(o.strength)
             if mg not in PRINTED_MG.get(inn, {mg})]
    verdicts, ok = [], True
    for key, want in expected.items():
        claim = next((c for c in report.claims if key in c.name_text.casefold().replace("-", "")), None)
        finding = next((f for f in report.findings if claim and f.claim_id == claim.claim_id), None)
        got = finding.type.value if finding else "no claim"
        verdicts.append(f"{key}: {got}")
        ok &= got == want
        if key == "concor" and got == "match":
            harms.append("a false match on Concor")
    kinds = sorted({overlap.kind.value for overlap in cross_medication(report.claims, CATALOGUE)})
    verdicts.append(f"across: {', '.join(kinds) or 'none'}")
    ok &= "same_class" in kinds
    return ok, verdicts, harms


def main() -> None:
    runs = sorted(Path(sys.argv[1]).glob("report_U12-b27_r*.json"))
    for way, expected in WAYS.items():
        correct = harmed = 0
        print(f"### {way}")
        for path in runs:
            report = ReconciliationReport.model_validate_json(path.read_text(encoding="utf-8"))
            ok, verdicts, harms = score(report, expected)
            correct += ok
            harmed += bool(harms)
            transcript = " / ".join(turn.transcript for turn in report.turns)
            print(f"{path.stem[7:]:12} {'correct' if ok else 'miss':7} {' | '.join(verdicts)}"
                  + (f" | HARM: {'; '.join(harms)}" if harms else "") + f" | heard: {transcript}")
        print(f"{way}: {correct} of {len(runs)} correct, {harmed} with a harm\n")


if __name__ == "__main__":
    main()
