"""Score the U12 hero's runs by its pre-registered row in manifest.md (28 Oct), from the repo root:

    PYTHONPATH=. uv run python evidence/batches/21/u12_score.py evidence/live/2026-10-28
"""

import sys
from decimal import Decimal
from pathlib import Path

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.overlap import cross_medication
from anamnesis.schema import ReconciliationReport

CATALOGUE = load_catalogue()
PRINTED_MG = {"bisoprolol": {Decimal(5)}, "metoprolol": {Decimal(50)}}  # what the two boxes print
EXPECTED = {"concor": "strength_mismatch", "beloc": "match"}


def amounts(strength) -> list[tuple[str, Decimal]]:
    return [(part.inn.split()[0], part.amount) for part in (strength.ingredients if strength else [])
            if part.unit.value == "mg"]


def score(report: ReconciliationReport) -> tuple[bool, list[str], list[str]]:
    observations = {o.observation_id: o for o in report.observations}
    harms = [f"{o.observation_id} reads {inn} {mg} mg" for o in observations.values()
             if o.readability.value == "readable" for inn, mg in amounts(o.strength)
             if mg not in PRINTED_MG.get(inn, {mg})]
    verdicts, ok = [], True
    for key, want in EXPECTED.items():
        claim = next((c for c in report.claims if key in c.name_text.casefold().replace("-", "")), None)
        finding = next((f for f in report.findings if claim and f.claim_id == claim.claim_id), None)
        got = finding.type.value if finding else "no claim"
        pack = observations.get(finding.observation_id) if finding and finding.observation_id else None
        printed = ", ".join(f"{inn} {mg} mg" for inn, mg in amounts(pack.strength)) if pack else "no pack"
        verdicts.append(f"{key}: {got} ({printed})")
        ok &= got == want
        if key == "concor" and got == "match":
            harms.append("a false match on Concor")
    kinds = sorted({overlap.kind.value for overlap in cross_medication(report.claims, CATALOGUE)})
    verdicts.append(f"across: {', '.join(kinds) or 'none'}")
    ok &= "same_class" in kinds
    return ok, verdicts, harms


runs = sorted(Path(sys.argv[1]).glob("report_U12_r*.json"))
correct = harmed = 0
for path in runs:
    report = ReconciliationReport.model_validate_json(path.read_text(encoding="utf-8"))
    ok, verdicts, harms = score(report)
    correct += ok
    harmed += bool(harms)
    others = [f"{f.type.value}({f.observation_id})" for f in report.findings if f.claim_id is None]
    print(f"{path.stem[7:]:4} {'correct' if ok else 'miss':7} {' | '.join(verdicts)}"
          + (f" | other: {', '.join(others)}" if others else "")
          + (f" | HARM: {'; '.join(harms)}" if harms else ""))
print(f"U12: {correct} of {len(runs)} correct, {harmed} with a harm")
