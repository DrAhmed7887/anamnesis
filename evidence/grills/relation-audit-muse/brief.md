# Double-check a provenance audit, read-only

You are checking an audit the CEO ran on Anamnesis's provenance checks. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, and use no API key;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file. The audit's files are inline below.

You may open `anamnesis/` and `tests/` (for instance `anamnesis/providers/claims.py`'s `parse_claims_json`, `anamnesis/providers/stated.py`, `anamnesis/core/reconcile.py`, and SPEC.md §2 "Known limits").

## 1. Goal
The check is done ONLY when your reply has the four sections in §3, and every point cites a file and line you opened, or a line below.

## 2. What to check
1. **The method:** do the audit's fakes really run the product's own checks and reconciler, so its offline table is what the product would do?
2. **Missing traps:** which relation-level patterns that could produce a **false `match`** (the worst kind) are missing? For instance: mg against mcg, "twice" against "two", amounts per day against per intake, two medicines with one ingredient, or a strength said for another brand. For each, say whether today's checks would catch the error.
3. **The conclusion:** is "no code change before the freeze; document the limit" right, given that both models got all eight traps right live, one run each? If not, what is the smallest safe change, and what could it break?
4. **The wording:** is the README sentence the audit proposes accurate?

## 3. Reply
1. **Verdict:** one line.
2. **Findings:** numbered, each with severity, file:line, the evidence and a fix.
3. **Missing traps:** a list, each marked "caught by today's checks" or "would pass".
4. **Open questions.**

Keep it under 600 words.

## The audit's README
# Relation-level provenance audit (31 Oct)

**Why:** GPT-6 Astra's win grill (`evidence/grills/win-grill-astra/`) said the provenance checks "prove words occurred, not that the finding follows". Ahmed said yes to an hour's audit before the freeze.

**What:** eight invented transcripts, each with one pack reading.
- **Each case has two replies:** the claim a careful listener would write ("right"), and one claim with a relation error ("wrong").
- **Both go through the product's real path:** its own checks (`parse_claims_json`), then the full intake with the real reconciler, on the brief tests' fake providers.
- **The run:** `audit.py`, offline, no model call.

## Offline result: what the checks do with a wrong reply
| Case | Pattern | Right reply | Wrong reply | The wrong reply, shown as fact? |
|---|---|---|---|---|
| A | a negated amount ("ten, not five") | `intake_differs_from_unit_strength` | `match` | **yes: a false match** |
| B | a past amount ("used to take ten") | `match` | `intake_differs_from_unit_strength` | yes |
| C | another medicine's amount, same turn | `insufficient_information` | `strength_mismatch` | yes |
| D | a tablet count read as milligrams | `intake_differs_from_unit_strength` | `strength_mismatch` | yes |
| E | one part of a combination | `match` | `insufficient_information` | no: fails safe |
| F | another medicine's amount, another turn | `insufficient_information` | `insufficient_information` | no: the amount is dropped |
| G | a stopped medicine read as active | `discontinued_but_present` | `insufficient_information` | no: fails safe |
| H | a negated amount, Egyptian Arabic | `intake_differs_from_unit_strength` | `match` | **yes: a false match** |

- **So:** the checks test that an amount is said in the cited turn, not what it's said about (SPEC §2, "Known limits").
- **Five of the eight errors would pass** and show a wrong finding as fact, if a model made them. Two of those (A, H) would be false matches.
- **Combinations, other turns and stopped medicines** fail safe.

## The live probe, written before any call
`probe_live.py` sends the same eight transcripts once to Spark 1.3 and once to the tuned Glimmer, through the product's own extractors. Each model's claims then go through the same intake, and its findings are compared with the careful listener's. The question is whether the real models make these errors. The transcripts are invented text, never a person's speech. Spend: about $0.10 of Meta, and about $0.60 of Modal with its cold start.

## Live result (31 Oct, 00:07–00:09 CET), one call per case and model
| Case | Pattern | Spark 1.3 | Tuned Glimmer (Modal) |
|---|---|---|---|
| A | a negated amount ("ten, not five") | 10 mg ✓ | 10 mg ✓ |
| B | a past amount | 5 mg ✓ | 5 mg ✓ |
| C | another medicine's amount, same turn | 500 mg on Panadol, none on Concor ✓ | the same ✓ |
| D | a tablet count | 2 tablets, no mg ✓ | the same ✓ |
| E | one part of a combination | no amount: fails safe | 875 mg only: fails safe |
| F | another medicine's amount, another turn | ✓ | ✓ |
| G | a stopped medicine | discontinued ✓ | discontinued ✓ |
| H | a negated amount, Egyptian Arabic | 10 mg ✓ | 10 mg ✓ |

- **Wrong findings shown as fact: 0 of 16.** On C and F, the second claim (Panadol, not photographed) adds the expected `missing_modality`. On E, neither model wrote the combination's two parts as a strength, so the intake fails safe (`insufficient_information`).
- **What it means:**
  - **The checks don't test relations.** In five of eight patterns, a wrong tie between an amount and a medicine would pass them and show a wrong finding as fact.
  - **On these eight transcripts, neither extractor made such an error.** That is one run each, on invented text, so it shows the models' behaviour on these traps, not a guarantee.
- **No code change before the freeze.** A negation rule would be a new, multilingual heuristic that drops amounts. SPEC §2's known limits say what the check doesn't test, and the README should say it plainly, with this audit.
- **Spend:** Spark 1.3 $0.08 for 8 calls. Modal: per-call estimates of $0.04, plus the container's time, reconciled from Modal's billing.

## audit.py
```python
"""Relation-level provenance audit (31 Oct, after GPT-6 Astra's win grill): when the model ties the wrong
words together, does the product fail safe or show a wrong finding as fact?

    PYTHONPATH=. uv run python evidence/audits/relation-provenance/audit.py

Each case is one invented transcript, one pack reading, the claim a careful listener would write ("right"),
and one claim with a relation error ("wrong"). Both replies go through the product's own checks
(`parse_claims_json`) and then the full intake with the real reconciler, on the brief tests' fake
providers. Offline, no model call.
"""

import json

from anamnesis.providers.base import ProviderError
from anamnesis.providers.claims import parse_claims_json
from anamnesis.schema import AudioTurn
from tests.contract.test_b19_brief import AUDIO, intake, mg, png, reading, region_on, st

PHOTO = png(600, 300)
REGION = region_on(PHOTO, (10, 20, 139, 279), 0, 0.95)
FACT = {"match", "strength_mismatch", "intake_differs_from_unit_strength", "ingredient_mismatch",
        "ratio_mismatch", "formulation_mismatch", "discontinued_but_present"}


def claim(name, *, intake_amount=None, units=None, status="active", turns=("turn-0",), strength=None):
    return {"name_text": name, "inn": None, "strength": strength,
            "intake_amount": intake_amount,
            "regimen": {"units_per_intake": units, "intakes_per_day": None, "as_needed": None},
            "status": status, "turn_ids": list(turns)}


def amount(inn, value, unit="mg"):
    return {"inn": inn, "amount": str(value), "unit": unit}


CONCOR_5 = ("Concor 5 mg\nBisoprolol fumarate", st(mg("bisoprolol", 5)))
PANADOL_500 = ("Panadol 500 mg\nParacetamol", st(mg("paracetamol", 500)))
AUGMENTIN = ("Augmentin 875 mg/125 mg\nAmoxicillin / clavulanic acid",
             st(mg("amoxicillin", 875), mg("clavulanic acid", 125)))

CASES = [
    {"id": "A", "pattern": "a negated amount",
     "turns": ["I take Concor ten milligrams in the morning, not five."], "pack": CONCOR_5,
     "right": claim("Concor", intake_amount=amount("bisoprolol", 10)),
     "wrong": claim("Concor", intake_amount=amount("bisoprolol", 5))},
    {"id": "B", "pattern": "a past amount",
     "turns": ["I used to take Concor ten milligrams. Now I take five milligrams once a day."],
     "pack": CONCOR_5,
     "right": claim("Concor", intake_amount=amount("bisoprolol", 5)),
     "wrong": claim("Concor", intake_amount=amount("bisoprolol", 10))},
    {"id": "C", "pattern": "another medicine's amount, same turn",
     "turns": ["I take Concor every morning and Panadol five hundred milligrams when I need it."],
     "pack": CONCOR_5,
     "right": claim("Concor"),
     "wrong": claim("Concor", intake_amount=amount("bisoprolol", 500))},
    {"id": "D", "pattern": "a tablet count read as milligrams",
     "turns": ["I take two Panadol tablets when I have a headache."], "pack": PANADOL_500,
     "right": claim("Panadol", units="2"),
     "wrong": claim("Panadol", intake_amount=amount("paracetamol", 2))},
    {"id": "E", "pattern": "one part of a combination",
     "turns": ["I take Augmentin, eight hundred seventy-five and one hundred twenty-five milligrams, "
               "twice a day."],
     "pack": AUGMENTIN,
     "right": claim("Augmentin", strength={"ingredients": [amount("amoxicillin", 875),
                                                            amount("clavulanic acid", 125)],
                                           "per": "tablet", "release": "unknown"}),
     "wrong": claim("Augmentin", intake_amount=amount("amoxicillin", 875))},
    {"id": "F", "pattern": "another medicine's amount, another turn",
     "turns": ["I take Concor.", "And Panadol, five hundred milligrams."], "pack": CONCOR_5,
     "right": claim("Concor"),
     "wrong": claim("Concor", intake_amount=amount("bisoprolol", 500))},
    {"id": "G", "pattern": "a stopped medicine read as active",
     "turns": ["I stopped taking Concor last month."], "pack": CONCOR_5,
     "right": claim("Concor", status="discontinued"),
     "wrong": claim("Concor")},
    {"id": "H", "pattern": "a negated amount, Egyptian Arabic",
     "turns": ["باخد كونكور عشرة مجم الصبح، مش خمسة."], "pack": CONCOR_5,
     "right": claim("كونكور", intake_amount=amount("bisoprolol", 10)),
     "wrong": claim("كونكور", intake_amount=amount("bisoprolol", 5))},
]


def turns_of(case):
    return [AudioTurn(turn_id=f"turn-{i}", start_ms=4000 * i, end_ms=4000 * i + 3500, transcript=text)
            for i, text in enumerate(case["turns"])]


def outcome(case, reply_claim):
    """The product's answer to one reply: dropped by the checks, or the findings the full intake shows."""
    turns = turns_of(case)
    try:
        claims = parse_claims_json(json.dumps({"claims": [reply_claim]}), turns)
    except ProviderError as exc:
        return "dropped by the checks", str(exc)[:90]
    label, strength = case["pack"]
    report = intake(AUDIO[0], [(PHOTO, "image/png")], turns=turns, claims=claims,
                    by_sha={REGION.image_sha256: [REGION]},
                    reads={REGION.region_id: [reading(label=label, strength=strength)] * 4})
    return ", ".join(sorted(f.type.value for f in report.findings)), ""


def main() -> None:
    print("| Case | Pattern | Right reply | Wrong reply | The wrong reply, shown as fact? |")
    print("|---|---|---|---|---|")
    for case in CASES:
        right, _ = outcome(case, case["right"])
        wrong, why = outcome(case, case["wrong"])
        if wrong.startswith("dropped"):
            shown = "no: dropped"
        elif wrong == right:
            shown = "no: the same findings as the right reply"
        elif set(wrong.split(", ")) & FACT:
            shown = "yes"
        else:
            shown = "no: fails safe"
        detail = f" ({why})" if why else ""
        print(f"| {case['id']} | {case['pattern']} | {right} | {wrong}{detail} | {shown} |")


if __name__ == "__main__":
    main()
```

## probe_live.py
```python
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
    for case in CASES:
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
    (HERE / "probe_live.json").write_text(out, encoding="utf-8")


if __name__ == "__main__":
    main()
```
