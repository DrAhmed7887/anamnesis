"""Score one system's replies on one split (plan.md, "The metrics, fixed now").

    .venv/bin/python finetune/score.py <split> <predictions.jsonl> [--data DIR]

Each prediction line is {"index": n, "reply": "<raw model reply text>"}, n being the example's line number
(from 0) in <split>.jsonl. A reply is read exactly as the product reads Spark 1.3's: parse_claims_json against
that example's turns, with its shape, grounding, stated-amount and no-advice checks. A reply that fails is
counted as invalid JSON, or as dropped by those checks, and the two are kept apart.

Per claim, against the answer: name_text (case, spaces and hyphens ignored), inn, the intake's amount and
unit, the strength's amounts and units, each regimen field, and status. Per transcript: every claim right,
none missing, none extra. Harmful: a claim with an amount or an INN that the transcript doesn't support (an
amount it doesn't state, an INN string it doesn't contain), counted on the raw reply before the product's
checks, and again on what survives them. Every miss is listed with the example's index and template ids.
"""

import argparse
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from anamnesis.core.catalogue import normalise  # noqa: E402
from anamnesis.providers.base import ProviderError  # noqa: E402
from anamnesis.providers.claims import parse_claims_json  # noqa: E402
from anamnesis.providers.numbers import parse_amount_text  # noqa: E402
from anamnesis.providers.stated import stated_amounts  # noqa: E402
from anamnesis.schema import PatientClaim, canonical_inn  # noqa: E402
from finetune.common import DATA_DIR, read_jsonl, turns_from_records  # noqa: E402

FIELDS = (
    "name_text", "inn", "intake", "strength", "units_per_intake", "intakes_per_day", "as_needed", "status",
)


def name_key(text: Any) -> Any:
    return re.sub(r"[\s-]+", "", text.casefold()) if isinstance(text, str) else text


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def fields_of(claim: dict[str, Any]) -> dict[str, Any]:
    """The compared fields of one claim, in PatientClaim.model_dump(mode="json") form."""
    regimen = claim.get("regimen") or {}
    intake, strength = claim.get("intake_amount"), claim.get("strength")
    return {
        "name_text": name_key(claim["name_text"]),
        "inn": name_key(claim["inn"]),
        "intake": None if intake is None else (_decimal(intake["amount"]), intake["unit"]),
        "strength": None if strength is None else tuple(sorted(
            (_decimal(part["amount"]), part["unit"]) for part in strength["ingredients"]
        )),
        "units_per_intake": _decimal(regimen.get("units_per_intake")),
        "intakes_per_day": _decimal(regimen.get("intakes_per_day")),
        "as_needed": regimen.get("as_needed"),
        "status": claim["status"],
    }


def show(field: str, value: Any) -> str:
    if value is None:
        return "null"
    if field == "intake":
        return f"{value[0]} {value[1]}"
    if field == "strength":
        return " + ".join(f"{amount} {unit}" for amount, unit in value)
    return str(value)


def align(wanted: list[dict], got: list[dict]) -> tuple[dict[int, int], list[int], list[int]]:
    """Pair answer claims with reply claims: same name first, then the rest in order."""
    pairs: dict[int, int] = {}
    for w_index, want in enumerate(wanted):
        for g_index, have in enumerate(got):
            if g_index not in pairs.values() and have["name_text"] == want["name_text"]:
                pairs[w_index] = g_index
                break
    rest_w = [index for index in range(len(wanted)) if index not in pairs]
    rest_g = [index for index in range(len(got)) if index not in pairs.values()]
    pairs.update(zip(rest_w, rest_g, strict=False))
    return pairs, rest_w[len(rest_g):], rest_g[len(rest_w):]


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _unsupported(raw: dict, turns: list, keep: tuple[bool, bool] | None) -> list[str]:
    """Amounts and INN strings of one raw claim that the transcript doesn't support. With `keep`, only the
    fields the product kept count (intake, strength), plus the claim's inn, which it always keeps."""
    said: set[Decimal] = set()
    for turn in turns:
        said |= stated_amounts(turn.transcript)
    texts = [normalise(turn.transcript) for turn in turns]
    intake, strength = _dict(raw.get("intake_amount")), _dict(raw.get("strength"))
    parts = [part for part in strength.get("ingredients") or [] if isinstance(part, dict)]
    keep_intake, keep_strength = keep if keep is not None else (True, True)
    amounts = ([intake.get("amount")] if keep_intake else []) + (
        [part.get("amount") for part in parts] if keep_strength else [])
    inns = [raw.get("inn")] + ([intake.get("inn")] if keep_intake else []) + (
        [part.get("inn") for part in parts] if keep_strength else [])
    found = []
    for amount in amounts:
        value = parse_amount_text(amount)
        if value is not None and value not in said:
            found.append(f"amount {value} not stated")
    for inn in inns:
        if isinstance(inn, str) and normalise(inn) and not any(normalise(inn) in text for text in texts):
            found.append(f"INN {inn!r} not in the transcript")
    return found


def _as_said(kept: str | None, written: Any) -> str | None:
    """The string the product kept, spelled as the model wrote it when the product only canonicalised it."""
    if kept is not None and isinstance(written, str) and canonical_inn(written) == canonical_inn(kept):
        return written
    return kept


def _unsupported_kept(claim: PatientClaim, raw: dict, turns: list) -> list[str]:
    """Amounts and INN strings of one claim as the product kept it that the transcript doesn't support.

    Counted on the product's own output (batch 24): an INN it nulled or a label it replaced no longer counts,
    and an INN said under an alias ("acetaminophen", kept as "paracetamol") counts as said. Before batch 24
    the product kept the model's strings as written, so this gives the same counts as the raw reply with the
    kept fields.
    """
    said: set[Decimal] = set()
    for turn in turns:
        said |= stated_amounts(turn.transcript)
    texts = [normalise(turn.transcript) for turn in turns]
    intake, strength = _dict(raw.get("intake_amount")), _dict(raw.get("strength"))
    raw_parts = [part for part in strength.get("ingredients") or [] if isinstance(part, dict)]
    amounts, inns = [], [_as_said(claim.inn, raw.get("inn"))]
    if claim.intake_amount is not None:
        amounts.append(claim.intake_amount.amount)
        inns.append(_as_said(claim.intake_amount.inn, intake.get("inn")))
    if claim.strength is not None:
        for index, part in enumerate(claim.strength.ingredients):
            amounts.append(part.amount)
            written = raw_parts[index].get("inn") if index < len(raw_parts) else None
            inns.append(_as_said(part.inn, written))
    found = [f"amount {amount} not stated" for amount in amounts if amount not in said]
    found += [f"INN {inn!r} not in the transcript" for inn in inns if isinstance(inn, str) and normalise(inn)
              and not any(normalise(inn) in text for text in texts)]
    return found


def score_example(answer: dict, reply: Any) -> dict:
    """The outcome of one reply against one answer line."""
    turns = turns_from_records(answer["turns"])
    wanted = [fields_of(claim) for claim in answer["claims"]]
    result: dict = {"outcome": "parsed", "problems": [], "correct": dict.fromkeys(FIELDS, 0),
                    "harm_before": [], "harm_after": [], "missing": 0, "extra": 0}
    if reply is None:
        result.update(outcome="no_reply", problems=["no reply"], missing=len(wanted))
        return result
    try:
        if not isinstance(reply, str):
            raise ValueError("not text")
        raw = json.loads(reply)
    except ValueError:
        result.update(outcome="invalid_json", problems=["invalid JSON"], missing=len(wanted))
        return result
    raw_claims = [claim for claim in _dict(raw).get("claims") or [] if isinstance(claim, dict)]
    result["harm_before"] = [harm for claim in raw_claims if (harm := _unsupported(claim, turns, None))]
    try:
        parsed = parse_claims_json(reply, turns)
    except ProviderError as exc:
        result.update(outcome="dropped", problems=[f"dropped by the product's checks: {exc}"],
                      missing=len(wanted))
        return result
    result["harm_after"] = [harm for claim, raw_claim in zip(parsed, raw_claims, strict=True)
                            if (harm := _unsupported_kept(claim, raw_claim, turns))]
    got = [fields_of(claim.model_dump(mode="json")) for claim in parsed]
    pairs, missing, extra = align(wanted, got)
    result.update(missing=len(missing), extra=len(extra))
    for w_index, g_index in pairs.items():
        for field in FIELDS:
            if wanted[w_index][field] == got[g_index][field]:
                result["correct"][field] += 1
            else:
                result["problems"].append(
                    f"c{w_index + 1} {field}: got {show(field, got[g_index][field])}, "
                    f"want {show(field, wanted[w_index][field])}")
    result["problems"] += [f"missing claim {answer['claims'][index]['name_text']!r}" for index in missing]
    result["problems"] += [f"extra claim {parsed[index].name_text!r}" for index in extra]
    return result


def load_predictions(path: Path, size: int) -> dict[int, Any]:
    replies: dict[int, Any] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        index = row.get("index") if isinstance(row, dict) else None
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < size:
            raise ValueError(f"{path}:{number}: index must be an integer from 0 to {size - 1}")
        if index in replies:
            raise ValueError(f"{path}:{number}: index {index} given twice")
        replies[index] = row.get("reply")
    return replies


def score(answers: list[dict], replies: dict[int, Any]) -> dict:
    """The split's metrics, and every miss."""
    report: dict = {
        "examples": len(answers), "replies": len(replies), "claims": 0, "missing": 0, "extra": 0,
        "outcomes": dict.fromkeys(("parsed", "dropped", "invalid_json", "no_reply"), 0),
        "fields": dict.fromkeys(FIELDS, 0), "all_correct": 0,
        "harm": {stage: {"claims": 0, "amounts": 0, "inns": 0} for stage in ("before", "after")},
        "misses": [],
    }
    for index, answer in enumerate(answers):
        result = score_example(answer, replies.get(index))
        report["claims"] += len(answer["claims"])
        report["outcomes"][result["outcome"]] += 1
        report["missing"] += result["missing"]
        report["extra"] += result["extra"]
        for field in FIELDS:
            report["fields"][field] += result["correct"][field]
        for stage in ("before", "after"):
            harms, tally = result[f"harm_{stage}"], report["harm"][stage]
            items = [item for harm in harms for item in harm]
            tally["claims"] += len(harms)
            tally["amounts"] += sum(item.startswith("amount") for item in items)
            tally["inns"] += sum(item.startswith("INN") for item in items)
        problems = result["problems"] + [f"harmful before the checks: {'; '.join(harm)}"
                                         for harm in result["harm_before"]]
        if result["outcome"] == "parsed" and not result["problems"]:
            report["all_correct"] += 1
        if problems:
            report["misses"].append({"index": index, "templates": "+".join(answer["templates"]),
                                     "problems": problems})
    return report


def _share(count: int, total: int) -> str:
    return f"{count}/{total} ({count / total:.1%})" if total else f"{count}/0"


def render(split: str, report: dict) -> str:
    examples, claims, outcomes = report["examples"], report["claims"], report["outcomes"]
    valid = outcomes["parsed"] + outcomes["dropped"]
    lines = [
        f"split {split}: {examples} examples, {report['replies']} replies, {claims} answer claims",
        f"valid JSON {_share(valid, examples)}; dropped by the product's checks {outcomes['dropped']}; "
        f"invalid JSON {outcomes['invalid_json']}; no reply {outcomes['no_reply']}",
        "per-claim field accuracy:",
        *(f"  {field:16} {_share(report['fields'][field], claims)}" for field in FIELDS),
        f"claims missing {report['missing']}, extra {report['extra']}",
        f"transcripts all correct {_share(report['all_correct'], examples)}",
    ]
    for stage, label in (("before", "raw reply, before the product's checks"), ("after", "after them")):
        harm = report["harm"][stage]
        lines.append(f"harmful claims, {label}: {harm['claims']} "
                     f"(unsupported amounts {harm['amounts']}, unsupported INNs {harm['inns']})")
    lines.append(f"examples with a miss or a harmful claim: {len(report['misses'])}")
    for miss in report["misses"]:
        lines.append(f"  #{miss['index']} [{miss['templates']}] " + " | ".join(miss["problems"]))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("split")
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--data", type=Path, default=DATA_DIR)
    args = parser.parse_args()
    answers = read_jsonl(args.data / f"{args.split}.answers.jsonl")
    print(render(args.split, score(answers, load_predictions(args.predictions, len(answers)))))


if __name__ == "__main__":
    main()
