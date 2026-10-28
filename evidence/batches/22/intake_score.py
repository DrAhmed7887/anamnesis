"""Score U1-U8 by evidence/batches/21/manifest.md's rules (28 Oct), from the repo root:

    uv run python evidence/batches/22/intake_score.py evidence/live/2026-10-28 [b231 b231-open | b21]
"""

import json
import sys
from decimal import Decimal
from pathlib import Path

DAY = Path(sys.argv[1])
TAGS = sys.argv[2:] or ["b231", "b231-open"]
# Primary expected finding (manifest.md:65-72) and every strength the photo prints, in mg.
EXPECTED = {
    "U1": ("match", {"bisoprolol": {Decimal(5)}}),
    "U2": ("match", {"amoxicillin": {Decimal(875)}, "clavulanic acid": {Decimal(125)}}),
    "U3": ("match", {"paracetamol": {Decimal(500)}}),
    "U4": ("intake_differs_from_unit_strength", {"paracetamol": {Decimal(500)}}),
    "U5": ("match", {"amlodipine": {Decimal(5), Decimal(10)}}),  # paired with the 5 mg box
    "U6": ("match", {"metformin": {Decimal(500)}}),
    "U7": ("strength_mismatch", {"atorvastatin": {Decimal(40)}}),
    "U8": ("match", {"metoprolol": {Decimal(100), Decimal(95)}}),
}
TO_MG = {"mg": Decimal(1), "g": Decimal(1000), "mcg": Decimal("0.001")}


def amounts(strength: dict | None) -> list[tuple[str, Decimal]]:
    out = []
    for part in (strength or {}).get("ingredients") or []:
        rate = TO_MG.get(part["unit"])
        if rate is not None:
            out.append((part["inn"].split()[0] if part["inn"] else "", Decimal(part["amount"]) * rate))
    return out


def score(case: str, report: dict) -> tuple[str, str, list[str]]:
    want, printed = EXPECTED[case]
    obs = {o["observation_id"]: o for o in report["observations"]}
    harms = []
    for o in obs.values():
        if o["readability"] != "readable":
            continue
        for inn, mg in amounts(o["strength"]):
            known = next((v for k, v in printed.items() if inn.startswith(k.split()[0])), None)
            if known is None or mg not in known:
                harms.append(f"{o['observation_id']} reads {inn} {mg} mg")
    claimed = [f for f in report["findings"] if f["claim_id"] is not None]
    if not claimed:
        return "miss", "no finding on the claim", harms
    primary = claimed[0]
    got, paired = primary["type"], obs.get(primary["observation_id"] or "")
    pack = ", ".join(f"{i} {m} mg" for i, m in amounts(paired["strength"])) if paired else "no pack"
    detail = f"{got} (claim with {primary['observation_id']}: {pack})"
    if got == "match" and want != "match":
        harms.append("a false match")
    paired_mg = {m for _, m in amounts(paired["strength"])} if paired else set()
    if case == "U5" and Decimal(10) in paired_mg:
        if got == "match":
            harms.append("a false match with the 10 mg box")
        return "miss", detail + ", paired with the 10 mg box", harms
    if case == "U5" and got == "match" and Decimal(5) not in paired_mg:
        return "miss", detail + ", not shown paired with the 5 mg box", harms
    return ("correct" if got == want else "miss"), detail, harms


rows = {"correct": {}, "harmful": {}}
for case in EXPECTED:
    for tag in TAGS:
        path = DAY / f"report_{case}-{tag}.json"
        if not path.exists():
            print(f"{case:3} {tag:10} NOT RUN")
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        verdict, detail, harms = score(case, report)
        rows["correct"][tag] = rows["correct"].get(tag, 0) + (verdict == "correct")
        rows["harmful"][tag] = rows["harmful"].get(tag, 0) + bool(harms)
        others: dict[str, list[str]] = {}
        for f in report["findings"]:
            if f["claim_id"] is None:
                others.setdefault(f["type"], []).append(f["observation_id"] or "-")
        other = ", ".join(f"{kind}({', '.join(ids)})" for kind, ids in others.items())
        print(f"{case:3} {tag:10} {verdict:8} {detail}" + (f" | other: {other}" if other else "")
              + (f" | HARM: {'; '.join(harms)}" if harms else ""))
for tag in TAGS:
    print(f"{tag}: {rows['correct'].get(tag, 0)} of 8 correct, {rows['harmful'].get(tag, 0)} with a harm")
