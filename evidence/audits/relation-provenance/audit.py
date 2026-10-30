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
