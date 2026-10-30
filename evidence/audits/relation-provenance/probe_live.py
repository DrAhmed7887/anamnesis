"""The relation audit's eight transcripts, live: what Spark 1.3 and the tuned Glimmer actually extract, and
the findings the full intake then shows. One call per case and model, through the product's own extractors.

    PYTHONPATH=. GLIMMER_URL=<server> uv run python evidence/audits/relation-provenance/probe_live.py

Keys come from the Keychain and are never printed. The transcripts are invented text, never a person's speech.
"""

import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from audit import CASES, FACT, PHOTO, REGION, outcome, turns_of  # noqa: E402

from anamnesis.providers import SpendGuard  # noqa: E402
from anamnesis.providers.base import ProviderError  # noqa: E402
from anamnesis.providers.claims import MetaClaimExtractor  # noqa: E402
from anamnesis.providers.glimmer import GLIMMER_TIMEOUT_S, GlimmerClaimExtractor  # noqa: E402
from anamnesis.providers.meta import MetaClient  # noqa: E402
from anamnesis.providers.openweight import OpenWeightClient  # noqa: E402
from tests.contract.test_b19_brief import AUDIO, intake, reading  # noqa: E402

ROOT = HERE.parents[2]


def keychain(service: str) -> str:
    return subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                          capture_output=True, text=True, check=True).stdout.strip()


def findings(case, claims) -> str:
    label, strength = case["pack"]
    report = intake(AUDIO[0], [(PHOTO, "image/png")], turns=turns_of(case), claims=claims,
                    by_sha={REGION.image_sha256: [REGION]},
                    reads={REGION.region_id: [reading(label=label, strength=strength)] * 4})
    return ", ".join(sorted(f.type.value for f in report.findings))


def summary(claims) -> list:
    return [{"name": c.name_text, "intake": str(c.intake_amount.amount) if c.intake_amount else None,
             "units": str(c.regimen.units_per_intake) if c.regimen and c.regimen.units_per_intake else None,
             "status": getattr(c.status, "value", c.status)} for c in claims]


def main() -> None:
    guard = SpendGuard(ROOT / "evidence/spend/ledger.jsonl", cap_usd=Decimal("11.00"))
    extractors = {
        "spark-1.3": MetaClaimExtractor(MetaClient(api_key=keychain("META_API_KEY")), guard),
        "glimmer-lora-r1": GlimmerClaimExtractor(
            OpenWeightClient(api_key=keychain("MODAL_PROXY_TOKEN"), base_url=os.environ["GLIMMER_URL"],
                             provider="modal", timeout=GLIMMER_TIMEOUT_S), guard),
    }
    rows = []
    print("| Case | Pattern | The careful listener's findings | Model | Its claims | Its findings "
          "| Wrong as fact? |")
    print("|---|---|---|---|---|---|---|")
    only = set(sys.argv[1:])  # case ids to run, or all
    for case in [c for c in CASES if not only or c["id"] in only]:
        right, _ = outcome(case, case["right"])
        for name, extractor in extractors.items():
            try:
                claims, _ = extractor.extract(turns_of(case))
                got, extracted = findings(case, claims), summary(claims)
            except ProviderError as exc:
                got, extracted = f"no claims ({exc.provider} error)", []
            wrong = got != right and bool(set(got.split(", ")) & FACT)
            rows.append({"case": case["id"], "model": name, "claims": extracted, "findings": got,
                         "right": right, "wrong_as_fact": wrong})
            shown = json.dumps(extracted, ensure_ascii=False)
            print(f"| {case['id']} | {case['pattern']} | {right} | {name} | {shown}"
                  f" | {got} | {'yes' if wrong else 'no'} |")
    out = json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
    name = "probe_live.json" if not only else f"probe_live_{''.join(sorted(only))}.json"
    (HERE / name).write_text(out, encoding="utf-8")


if __name__ == "__main__":
    main()
