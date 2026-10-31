"""Batch 28's live check, scored as `live-plan.md` set out before any call: each U1-U8 intake with the second
reader, and the same intake without it. A pack whose `second_read` replaced Spark 1.3's reading goes back to
partial, and the findings are reconciled again; within one run that is exact, because nothing before step 5b
depends on the second reader.

    PYTHONPATH=. uv run python evidence/batches/28/score_paired.py evidence/live/2026-10-31 b28
"""

import sys
from decimal import Decimal
from pathlib import Path

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all
from anamnesis.schema import Readability, ReconciliationReport
from anamnesis.schema.report import AgentAction

CATALOGUE = load_catalogue()
EXPECTED = {  # evidence/batches/22/intake_score.py: the primary finding and every strength printed, in mg
    "U1": ("match", {"bisoprolol": {Decimal(5)}}),
    "U2": ("match", {"amoxicillin": {Decimal(875)}, "clavulanic acid": {Decimal(125)}}),
    "U3": ("match", {"paracetamol": {Decimal(500)}}),
    "U4": ("intake_differs_from_unit_strength", {"paracetamol": {Decimal(500)}}),
    "U5": ("match", {"amlodipine": {Decimal(5), Decimal(10)}}),
    "U6": ("match", {"metformin": {Decimal(500)}}),
    "U7": ("strength_mismatch", {"atorvastatin": {Decimal(40)}}),
    "U8": ("match", {"metoprolol": {Decimal(100), Decimal(95)}}),
}
TO_MG = {"mg": Decimal(1), "g": Decimal(1000), "mcg": Decimal("0.001")}


def amounts(strength) -> list[tuple[str, Decimal]]:
    out = []
    for part in (strength.ingredients if strength else []):
        rate = TO_MG.get(part.unit.value)
        if rate is not None:
            out.append((part.inn.split()[0] if part.inn else "", part.amount * rate))
    return out


def score(case: str, report: ReconciliationReport) -> tuple[str, list[str]]:
    want, printed = EXPECTED[case]
    obs = {o.observation_id: o for o in report.observations}
    harms = []
    for o in obs.values():
        if o.readability.value != "readable":
            continue
        for inn, mg in amounts(o.strength):
            known = next((v for k, v in printed.items() if inn.startswith(k.split()[0])), None)
            if known is None or mg not in known:
                harms.append(f"{o.observation_id} reads {inn} {mg} mg")
    claimed = [f for f in report.findings if f.claim_id is not None]
    if not claimed:
        return "miss", harms
    primary = claimed[0]
    got = primary.type.value
    paired = obs.get(primary.observation_id or "")
    paired_mg = {m for _, m in amounts(paired.strength)} if paired else set()
    if got == "match" and want != "match":
        harms.append("a false match")
    if case == "U5" and (Decimal(10) in paired_mg or (got == "match" and Decimal(5) not in paired_mg)):
        if got == "match" and Decimal(10) in paired_mg:
            harms.append("a false match with the 10 mg box")
        return "miss", harms
    return ("correct" if got == want else "miss"), harms


def replaced_regions(report: ReconciliationReport) -> dict[str, str]:
    """Every region with a second read, and what it did: replaced, or kept the first reading (and why)."""
    out: dict[str, str] = {}
    for step in report.steps:  # a conflict or region note follows its call's step, so the last one wins
        if step.action is AgentAction.SECOND_READ:
            did = "replaced" if step.outcome == "readable" else f"kept the first ({step.outcome})"
            out[step.target] = did
    return out


def without_second(report: ReconciliationReport, regions: dict[str, str]) -> ReconciliationReport:
    gone = {region for region, did in regions.items() if did == "replaced"}
    observations = [o.model_copy(update={"readability": Readability.PARTIAL})
                    if set(o.visual_evidence) & gone else o for o in report.observations]
    findings = reconcile_all(list(report.claims), observations, CATALOGUE)
    return report.model_copy(update={"observations": observations, "findings": findings})


def main() -> None:
    day, tag = Path(sys.argv[1]), sys.argv[2]
    totals = {"with": 0, "without": 0, "harm_with": 0, "harm_without": 0, "n": 0}
    for path in sorted(day.glob(f"report_U?-{tag}-r*.json")):
        case = path.stem.split("_")[1].split("-")[0]
        report = ReconciliationReport.model_validate_json(path.read_text(encoding="utf-8"))
        regions = replaced_regions(report)
        verdict, harms = score(case, report)
        verdict_without, harms_without = score(case, without_second(report, regions))
        totals["n"] += 1
        totals["with"] += verdict == "correct"
        totals["without"] += verdict_without == "correct"
        totals["harm_with"] += bool(harms)
        totals["harm_without"] += bool(harms_without)
        reads = "; ".join(f"{region[-4:]}: {did}" for region, did in regions.items()) or "no second read"
        print(f"{path.stem[7:]:16} with {verdict:7} without {verdict_without:7}"
              f" | second reads: {reads}"
              + (f" | HARM: {'; '.join(harms)}" if harms else ""))
    print(f"\n{totals['n']} intakes: correct with the second reader {totals['with']}, "
          f"without it {totals['without']}; "
          f"harmful with {totals['harm_with']}, without {totals['harm_without']}")


if __name__ == "__main__":
    main()
