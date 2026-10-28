# ruff: noqa: E501  (the record of the m7 triage, as it ran on 28 Oct)
"""Run each m7 grill finding's input against the code, offline: no model call (#5 uses a mock transport).

    PYTHONPATH=.:scripts uv run python evidence/grills/m7-pre-freeze/verify_grill.py
"""

import json
import pathlib
import tempfile
from decimal import Decimal

import httpx
import reader_eval

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.guardrails import assert_no_advice
from anamnesis.core.reconcile import reconcile_pair
from anamnesis.providers.numbers import parse_amount_text
from anamnesis.providers.openweight import OpenWeightClient, OpenWeightLabelReader
from anamnesis.providers.spark import parse_label_json
from anamnesis.providers.spend import SessionGuard, SpendGuard
from anamnesis.schema import (
    ImageRegion,
    IngredientAmount,
    MedicationStatus,
    PackObservation,
    PatientClaim,
    Strength,
)

CATALOGUE = load_catalogue()


def kept(text: str, inn: str, amount: str, per: str) -> str:
    raw = {"label_text": text, "inn": inn, "country": None, "readability": "readable",
           "strength": {"ingredients": [{"inn": inn, "amount": amount, "unit": "mg"}], "per": per,
                        "release": "unknown"}}
    strength = parse_label_json(json.dumps(raw, ensure_ascii=False), "r1").strength
    return "null" if strength is None else f"{strength.ingredients[0].amount} mg per {per}"


def pack(text: str, inn: str, mg: int, salt: str | None = None) -> PackObservation:
    part = IngredientAmount(inn=inn, salt=salt, amount=Decimal(mg), unit="mg")
    return PackObservation(observation_id="o1", label_text=text, inn=inn, readability="readable",
                           strength=Strength(ingredients=[part], per="tablet"), visual_evidence=["r1"])


def claim(name: str, inn: str, mg: int) -> PatientClaim:
    return PatientClaim(claim_id="c1", name_text=name, status=MedicationStatus.ACTIVE, audio_evidence=["t1"],
                        intake_amount=IngredientAmount(inn=inn, amount=Decimal(mg), unit="mg"))


def contributor_price_key() -> str:
    sent: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content)["model"])
        content = json.dumps({"label_text": "Paracetamol 500 mg", "inn": "paracetamol", "country": None,
                              "readability": "readable", "strength": None})
        return httpx.Response(200, json={"id": "x1", "usage": {"prompt_tokens": 100, "completion_tokens": 10},
                                         "choices": [{"finish_reason": "stop", "message": {"content": content}}]})

    ledger = pathlib.Path(tempfile.mkdtemp()) / "ledger.jsonl"
    guard = SessionGuard(SpendGuard(ledger, cap_usd=Decimal(1)), max_usd=Decimal(1), max_calls=5)
    client = OpenWeightClient("k", "https://example.invalid/v1", "baseten", transport=httpx.MockTransport(handler))
    reader = OpenWeightLabelReader(client, guard, model="meta-models/muse-spark-open",
                                   price_key="muse-spark-open-contributor@baseten", json_mode=False)
    region = ImageRegion(region_id="a" * 12 + "-0", image_sha256="a" * 64, object_id=0, x1=0, y1=0, x2=8, y2=8,
                         frame_w=10, frame_h=10)
    try:
        reader.read(b"\x89PNG", region, mime="image/png", cropped=True)
        outcome = "read went through"
    except Exception as exc:  # the outcome is the finding
        outcome = f"read raised {type(exc).__name__}"
    lines = len(ledger.read_text().splitlines()) if ledger.exists() else 0
    return f"constructed; {outcome}; requests sent: {len(sent)}; ledger lines: {lines}"


print("#1 '250 mg / 5 ملي' per ml:", kept("Amoxicillin 250 mg / 5 ملي", "amoxicillin", "250", "ml"))
print("#2 'Each 5 ml contains 250 mg per dose' per dose:",
      kept("Each 5 ml contains 250 mg per dose", "paracetamol", "250", "dose"))
print("#2 'Each 5 ml contains 250 mg/ml' per dose:", kept("Each 5 ml contains 250 mg/ml", "paracetamol", "250", "dose"))
print("#2 'Each 5 ml contains 250 mg. 250 mg tablets' per tablet:",
      kept("Each 5 ml contains 250 mg. 250 mg tablets", "paracetamol", "250", "tablet"))
print("#3 'Each five ml contains 250 mg' per ml:", kept("Each five ml contains 250 mg", "amoxicillin", "250", "ml"))
for name in ("amoxicillin clavulanic acid", "amoxicillin and clavulanic acid", "Augmentin"):
    finding = reconcile_pair(claim(name, "amoxicillin", 500), pack("Amoxil 500 mg", "amoxicillin", 500), CATALOGUE)
    print(f"#4 claim {name!r} 500 mg vs 'Amoxil 500 mg':", finding.type.value)
finding = reconcile_pair(claim("metoprolol", "metoprolol", 100),
                         pack("Metoprolol succinate 95 mg", "metoprolol", 95, "succinate"), CATALOGUE)
print("#4 claim 'metoprolol' 100 mg vs 'Metoprolol succinate 95 mg':", finding.type.value)
print("#5 contributor price key:", contributor_price_key())
for rel in ("public/dailymed/panadol_extra_e5c2d88a_carton.jpg", "public/../real/x.jpg",
            "public/gemini-commons/augmentin_1g_gsk_box.jpg"):
    try:
        reader_eval.public_photo(rel)
        print(f"#6 reader_eval.public_photo({rel!r}): allowed")
    except SystemExit:
        print(f"#6 reader_eval.public_photo({rel!r}): refused")
try:
    assert_no_advice("Panadol - take two tablets daily")
    print("#7 the extractor's check passes advice in name_text")
except Exception as exc:  # the outcome is the finding
    print(f"#7 the extractor's check refuses advice in name_text: {type(exc).__name__}")
for text in ("amoxicillin clavulanic acid", "co-amoxiclav", "أملوديبين 5 مجم", "Augmentin"):
    entry = CATALOGUE.resolve(text)
    print(f"#10 resolve({text!r}):", None if entry is None else (entry.brand, sorted(entry.inns)))
for value in (1e-5, "١,٥", "1.000"):
    print(f"#11 parse_amount_text({value!r}):", parse_amount_text(value))
