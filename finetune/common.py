"""Shared pieces of the fine-tune data (evidence/finetune/plan.md): the prompt, the user message, the answer
and the check every answer must pass before it is written."""

import json
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from anamnesis.core.guardrails import AdviceLeak, assert_no_advice
from anamnesis.providers.base import ProviderError
from anamnesis.providers.claims import _SYSTEM_PROMPT, parse_claims_json
from anamnesis.schema import AudioTurn, PatientClaim

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "finetune" / "data"
# The product's own prompt, plus the reasoning line every model in the comparison gets (plan.md, Training).
SYSTEM_CONTENT = f"{_SYSTEM_PROMPT}\nReasoning strength: low"


class DataError(Exception):
    """An example that must not be written: its answer doesn't survive the product's own parser."""


@dataclass(frozen=True)
class Amount:
    """One amount as the patient said it. `inn` is the name the patient used for the medicine: the
    ingredient if they said it, otherwise the brand itself, so no INN is ever inferred from a brand."""

    value: Decimal
    unit: str
    inn: str


@dataclass(frozen=True)
class ClaimSpec:
    """What the patient meant about one medicine, built in code from the choices behind the utterance."""

    name_text: str
    turn_ids: tuple[str, ...]
    status: str = "active"
    inn: str | None = None
    intake: Amount | None = None
    strength: Amount | None = None
    per: str | None = None
    units: Decimal | None = None
    per_day: Decimal | None = None
    as_needed: bool | None = None


def number(value: Decimal) -> str:
    """Plain digits, the way the prompt asks for every amount: 50, 2.5, 0.025 (never 5E+1 or 50.000)."""
    return format(value.normalize(), "f")


def format_turns(turns: list[AudioTurn]) -> str:
    """The user message exactly as MetaClaimExtractor.extract builds it (a unit test pins the two)."""
    return "\n".join(
        f"[{turn.turn_id} {turn.start_ms}–{turn.end_ms} ms, speaker {turn.speaker or 'unknown'}] "
        f"{turn.transcript}"
        for turn in turns
    )


def _has_regimen(spec: ClaimSpec) -> bool:
    return spec.units is not None or spec.per_day is not None or spec.as_needed is not None


def _answer_amount(amount: Amount) -> dict[str, str]:
    return {"inn": amount.inn, "amount": number(amount.value), "unit": amount.unit}


def answer_claim(spec: ClaimSpec) -> dict[str, Any]:
    """One claim in CLAIMS_SCHEMA's shape and key order. Anything not said is null, regimen included."""
    strength = None
    if spec.strength is not None:
        strength = {"ingredients": [_answer_amount(spec.strength)], "per": spec.per, "release": "unknown"}
    regimen = None
    if _has_regimen(spec):
        regimen = {
            "units_per_intake": None if spec.units is None else number(spec.units),
            "intakes_per_day": None if spec.per_day is None else number(spec.per_day),
            "as_needed": spec.as_needed,
        }
    return {
        "name_text": spec.name_text,
        "inn": spec.inn,
        "strength": strength,
        "intake_amount": None if spec.intake is None else _answer_amount(spec.intake),
        "regimen": regimen,
        "status": spec.status,
        "turn_ids": list(spec.turn_ids),
    }


def answer_text(specs: list[ClaimSpec]) -> str:
    return json.dumps({"claims": [answer_claim(spec) for spec in specs]}, ensure_ascii=False)


def _claim_amount(amount: Amount) -> dict[str, Any]:
    return {"inn": amount.inn, "amount": amount.value, "unit": amount.unit}


def intended_claims(specs: list[ClaimSpec]) -> list[PatientClaim]:
    """The claims the answer must parse to, built straight from the specs with Decimal values."""
    claims = []
    for index, spec in enumerate(specs, start=1):
        strength = None
        if spec.strength is not None:
            strength = {"ingredients": [_claim_amount(spec.strength)], "per": spec.per, "release": "unknown"}
        regimen = None
        if _has_regimen(spec):
            regimen = {
                "units_per_intake": spec.units, "intakes_per_day": spec.per_day, "as_needed": spec.as_needed,
            }
        claims.append(PatientClaim.model_validate({
            "claim_id": f"c{index}",
            "name_text": spec.name_text,
            "inn": spec.inn,
            "strength": strength,
            "intake_amount": None if spec.intake is None else _claim_amount(spec.intake),
            "regimen": regimen,
            "status": spec.status,
            "audio_evidence": list(spec.turn_ids),
        }))
    return claims


def claim_strings(answer: str) -> list[str]:
    """The strings the product's advice check covers in a claims reply (parse_claims_json, SPEC §2): each
    claim's name_text and inn, and the inn of its intake and of every strength ingredient."""
    strings = []
    for claim in json.loads(answer)["claims"]:
        parts = [claim["intake_amount"], *(claim["strength"] or {}).get("ingredients", [])]
        strings += [claim["name_text"], claim["inn"], *(part["inn"] for part in parts if part)]
    return [text for text in strings if text]


def check_example(turns: list[AudioTurn], specs: list[ClaimSpec], answer: str) -> list[PatientClaim]:
    """Fail loudly unless the answer passes parse_claims_json against its own turns and parses to exactly the
    intended claims. assert_no_advice runs only where the product runs it, on the answer's claim fields, and
    never on the patient's speech: patients say "I take ..." and "I stopped taking ...", and every real
    transcript does."""
    try:
        parsed = parse_claims_json(answer, turns)
    except ProviderError as exc:
        raise DataError(f"parse_claims_json rejects the answer {answer}: {exc}") from exc
    wanted = intended_claims(specs)
    if [claim.model_dump() for claim in parsed] != [claim.model_dump() for claim in wanted]:
        got = [claim.model_dump(mode="json") for claim in parsed]
        want = [claim.model_dump(mode="json") for claim in wanted]
        raise DataError(f"the answer parses to other claims than intended:\n got  {got}\n want {want}")
    for text in claim_strings(answer):
        try:
            assert_no_advice(text)
        except AdviceLeak as exc:
            raise DataError(f"a claim field fails assert_no_advice: {text!r}") from exc
    return parsed


def chat_row(user: str, answer: str) -> dict[str, Any]:
    """One Fireworks chat SFT line: the answer is the only target (weights set explicitly, plan.md)."""
    return {"messages": [
        {"role": "system", "content": SYSTEM_CONTENT, "weight": 0},
        {"role": "user", "content": user, "weight": 0},
        {"role": "assistant", "content": answer, "weight": 1},
    ]}


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def turns_from_records(records: list[dict[str, Any]]) -> list[AudioTurn]:
    return [AudioTurn.model_validate(record) for record in records]
