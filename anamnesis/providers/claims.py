"""Muse Spark extraction of patient-reported medication claims."""

import json
import re
import unicodedata
from typing import Any

from pydantic import ValidationError

from anamnesis.core.catalogue import ARABIC_CLITICS, Catalogue, load_catalogue, normalise
from anamnesis.core.guardrails import AdviceLeak, assert_no_advice, assert_no_advice_in_ingredients
from anamnesis.providers.base import ProviderError, ProviderTrace, cost_usd, with_one_retry
from anamnesis.providers.meta import MetaClient, spark_call_estimate
from anamnesis.providers.numbers import coerce_strength, parse_amount_text
from anamnesis.providers.relations import (
    another_names_for_claim,
    count_values_for_cited_turns,
    is_amount_grounded,
    mentions_for_cited_turns,
    own_names_for_claim,
)
from anamnesis.providers.spend import SpendGuard
from anamnesis.providers.stated import UNIT_WORDS, has_number_role, stated_amounts
from anamnesis.schema import (
    AudioTurn,
    IngredientAmount,
    MedicationStatus,
    PatientClaim,
    Release,
    StrengthPer,
    Unit,
    canonical_inn,
    salt_of,
)

_SYSTEM_PROMPT = (
    "Extract every medicine the patient mentions, with one claim per medicine. "
    "Copy name_text exactly as spoken. Fill inn only if the patient said the ingredient name; "
    "never infer it from a brand. An amount spoken with a frequency, such as '50 mg twice a day', "
    "is an intake_amount with regimen.intakes_per_day. Use strength only when the patient explicitly "
    "describes the tablet or pack, such as 'the 5 mg tablets'. 'I stopped' or 'no longer take' means "
    "discontinued. If unclear, use unknown. Leave anything not said as null. Cite the turn_ids each "
    "claim comes from. Write every amount and count as digits, even when the patient said it in words "
    "('five' is 5, 'خمسة' is 5, 'twice a day' is 2), with the unit the patient said, "
    "and never convert units. "
    "Give no medical advice. Only report what the patient said."
)

_COMBINATION_SENTENCE = (
    "A combination product said with one amount per ingredient, such as "
    "'Augmentin 875 and 125 milligrams', is its strength: one ingredient per amount, "
    "in the order said, each named for the ingredient it belongs to."
)
"""The batch 29 sentence, SPEC §2 word for word; only Spark 1.3's claim prompt gets it."""

_SPARK_CLAIM_PROMPT = f"{_SYSTEM_PROMPT} {_COMBINATION_SENTENCE}"
"""What MetaClaimExtractor sends: the trained prompt plus the combination sentence."""

_AMOUNT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["inn", "amount", "unit"],
    "properties": {
        "inn": {"type": "string"},
        "amount": {"type": "string"},
        "unit": {"type": "string", "enum": [item.value for item in Unit]},
    },
}

_STRENGTH_SCHEMA: dict[str, Any] = {
    "type": ["object", "null"],
    "additionalProperties": False,
    "required": ["ingredients", "per", "release"],
    "properties": {
        "ingredients": {"type": "array", "items": _AMOUNT_SCHEMA},
        "per": {"type": "string", "enum": [item.value for item in StrengthPer]},
        "release": {"type": "string", "enum": [item.value for item in Release]},
    },
}

_REGIMEN_SCHEMA: dict[str, Any] = {
    "type": ["object", "null"],
    "additionalProperties": False,
    "required": ["units_per_intake", "intakes_per_day", "as_needed"],
    "properties": {
        "units_per_intake": {"type": ["string", "null"]},
        "intakes_per_day": {"type": ["string", "null"]},
        "as_needed": {"type": ["boolean", "null"]},
    },
}

CLAIMS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["claims"],
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name_text", "inn", "strength", "intake_amount", "regimen", "status", "turn_ids",
                ],
                "properties": {
                    "name_text": {"type": "string"},
                    "inn": {"type": ["string", "null"]},
                    "strength": _STRENGTH_SCHEMA,
                    "intake_amount": _AMOUNT_SCHEMA | {"type": ["object", "null"]},
                    "regimen": _REGIMEN_SCHEMA,
                    "status": {"type": "string", "enum": [item.value for item in MedicationStatus]},
                    "turn_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}


def _expect_keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} has an invalid shape")


def _validate_raw_shape(data: Any) -> list[dict[str, Any]]:
    _expect_keys(data, {"claims"}, "claims response")
    claims = data["claims"]
    if not isinstance(claims, list):
        raise ValueError("claims must be an array")
    claim_keys = {
        "name_text", "inn", "strength", "intake_amount", "regimen", "status", "turn_ids",
    }
    amount_keys = {"inn", "amount", "unit"}
    for claim in claims:
        _expect_keys(claim, claim_keys, "claim")
        strength = claim["strength"]
        if strength is not None:
            _expect_keys(strength, {"ingredients", "per", "release"}, "strength")
            if not isinstance(strength["ingredients"], list):
                raise ValueError("strength ingredients must be an array")
            for amount in strength["ingredients"]:
                _expect_keys(amount, amount_keys, "strength ingredient")
        intake_amount = claim["intake_amount"]
        if intake_amount is not None:
            _expect_keys(intake_amount, amount_keys, "intake amount")
        regimen = claim["regimen"]
        if regimen is not None:
            _expect_keys(regimen, {"units_per_intake", "intakes_per_day", "as_needed"}, "regimen")
    return claims


def _advice_strings(raw: dict[str, Any]) -> list[str]:
    """Raw model-written scalar strings subject to the advice check (SPEC §2).

    Ingredient `inn` strings go through the shared helper instead.
    """
    strings = [raw.get("name_text"), raw.get("inn")]
    intake = raw.get("intake_amount")
    if isinstance(intake, dict):
        strings.append(intake.get("inn"))
    return [text for text in strings if isinstance(text, str) and text]


def _check_no_advice(strings: list[str]) -> None:
    for text in strings:
        try:
            assert_no_advice(text)
        except AdviceLeak as exc:
            raise ValueError("claim string failed the advice check") from exc


def _coerce_intake(raw: Any) -> Any:
    """Return an intake dict with a parsed amount, or None to drop it."""
    if not isinstance(raw, dict):
        return raw
    amount = parse_amount_text(raw.get("amount"))
    if amount is None:
        return None
    try:
        IngredientAmount.model_validate({**raw, "amount": amount})
    except (TypeError, ValueError, ValidationError):
        return None
    return {**raw, "amount": amount}


def _coerce_regimen(raw: Any) -> Any:
    """Parse each regimen number on its own; unparseable becomes null."""
    if not isinstance(raw, dict):
        return raw
    return {
        **raw,
        "units_per_intake": parse_amount_text(raw.get("units_per_intake")),
        "intakes_per_day": parse_amount_text(raw.get("intakes_per_day")),
    }


def _check_grounded(name: Any, turn_ids: list[Any], transcripts: dict[str, str]) -> None:
    """Require name_text to occur in a cited turn (both sides normalised)."""
    if not isinstance(name, str):
        raise ValueError("claim name_text must be a string")
    needle = normalise(name)
    if not needle or not any(needle in normalise(transcripts[turn_id]) for turn_id in turn_ids):
        raise ValueError("claim name_text must occur in a turn the claim cites")


_BUNDLED_CATALOGUE: Catalogue | None = None


def _bundled_catalogue() -> Catalogue:
    global _BUNDLED_CATALOGUE
    if _BUNDLED_CATALOGUE is None:
        _BUNDLED_CATALOGUE = load_catalogue()
    return _BUNDLED_CATALOGUE


_AMOUNT_ONLY_WORDS = frozenset({
    "milligram", "milligrams", "gram", "grams", "microgram", "micrograms",
    "millilitre", "millilitres", "milliliter", "milliliters",
    "unit", "units", "iu",
    "and", "y", "und", "a", "point", "coma", "komma",
})
"""English unit words and joiners that also count as amount words (SPEC §2, round 2 #7)."""


def _resolve_strength_inn(name: str, catalogue: Catalogue) -> str:
    """Resolve a strength label as the reconciler does (SPEC §2, round 2 #1)."""
    canonical = canonical_inn(name)
    known_moieties = {inn for entry in catalogue.entries for inn in entry.inns}
    if canonical in known_moieties:
        return canonical
    entry = catalogue.resolve(name)
    if entry is not None and len(entry.inns) == 1:
        return next(iter(entry.inns))
    return canonical


def _grounded_by_turns(field: object, cited: list[str]) -> bool:
    """An ingredient field grounded by cited turns (SPEC §2, batch 24)."""
    if not isinstance(field, str):
        return False
    norm_field = normalise(unicodedata.normalize("NFC", field))
    if not norm_field:
        return False
    field_words = norm_field.split()
    only_numbers = True
    for word in field_words:
        if word in UNIT_WORDS or word in _AMOUNT_ONLY_WORDS or stated_amounts(word) or has_number_role(word):
            continue
        if word.isdigit():
            continue
        only_numbers = False
        break
    if only_numbers:
        return False
    field_pair = (canonical_inn(field), salt_of(field))
    for text in cited:
        norm_turn = normalise(unicodedata.normalize("NFC", text))
        if not norm_turn:
            continue
        parts = []
        for word in field_words:
            if re.search(r"[\u0600-\u06ff]", word):
                parts.append(f"{ARABIC_CLITICS}{re.escape(word)}")
            else:
                parts.append(re.escape(word))
        if re.search(r"(?<!\w)" + r"\s+".join(parts) + r"(?!\w)", norm_turn):
            return True
        turn_words = norm_turn.split()
        matched = True
        for word in field_words:
            if len(word) < 3:
                if word not in turn_words:
                    matched = False
                    break
                continue
            stem = word[:-1] if len(word) >= 6 and word[-1] in "aeiou" else word
            if not any(turn_word.startswith(stem) for turn_word in turn_words):
                matched = False
                break
        if matched:
            return True
        for start in range(len(turn_words)):
            for size in (1, 2, 3):
                run = " ".join(turn_words[start:start + size])
                if not run:
                    continue
                if (canonical_inn(run), salt_of(run)) == field_pair:
                    return True
    return False


def _grounded_label(field: object, cited: list[str], catalogue: Catalogue, name_text: object) -> bool:
    """An amount label grounded by turns or by the brand's own ingredients."""
    if _grounded_by_turns(field, cited):
        return True
    if not isinstance(field, str) or not isinstance(name_text, str):
        return False
    entry = catalogue.resolve(name_text)
    return entry is not None and canonical_inn(field) in entry.inns


def parse_claims_json(
    text: str, turns: list[AudioTurn], catalogue: Catalogue | None = None,
) -> list[PatientClaim]:
    """Validate Spark JSON and attach only cited transcript turns as evidence."""
    cat = catalogue if catalogue is not None else _bundled_catalogue()
    try:
        raw_claims = _validate_raw_shape(json.loads(text))
        transcripts = {turn.turn_id: turn.transcript for turn in turns}
        claims = []
        for index, raw in enumerate(raw_claims, start=1):
            _check_no_advice(_advice_strings(raw))
            assert_no_advice_in_ingredients(raw)
            turn_ids = raw["turn_ids"]
            invalid_turn_ids = any(
                not isinstance(turn_id, str) or turn_id not in transcripts for turn_id in turn_ids
            ) if isinstance(turn_ids, list) else True
            if not isinstance(turn_ids, list) or not turn_ids or invalid_turn_ids:
                raise ValueError("claim turn_ids must cite existing turns")
            _check_grounded(raw["name_text"], turn_ids, transcripts)
            cited = [transcripts[turn_id] for turn_id in turn_ids]
            raw_inn = raw.get("inn")
            if raw_inn is None:
                grounded_inn: Any = None
            elif isinstance(raw_inn, str):
                grounded_inn = raw_inn if _grounded_by_turns(raw_inn, cited) else None
            else:
                grounded_inn = raw_inn
            raw_intake = raw["intake_amount"]
            if isinstance(raw_intake, dict):
                label = raw_intake.get("inn")
                if not (
                    isinstance(label, str) and _grounded_label(label, cited, cat, raw["name_text"])
                ):
                    fallback = grounded_inn if isinstance(grounded_inn, str) else raw["name_text"]
                    raw_intake = {**raw_intake, "inn": fallback}
            raw_strength: Any = raw["strength"]
            if isinstance(raw_strength, dict) and isinstance(raw_strength.get("ingredients"), list):
                relabelled = []
                for part in raw_strength["ingredients"]:
                    if isinstance(part, dict):
                        label = part.get("inn")
                        if isinstance(label, str) and _grounded_label(
                            label, cited, cat, raw["name_text"],
                        ):
                            relabelled.append(part)
                        else:
                            fallback = (
                                grounded_inn if isinstance(grounded_inn, str) else raw["name_text"]
                            )
                            relabelled.append({**part, "inn": fallback})
                    else:
                        relabelled.append(part)
                raw_strength = {**raw_strength, "ingredients": relabelled}
            strength_was_empty = (
                isinstance(raw["strength"], dict) and raw["strength"].get("ingredients") == []
            )
            strength = coerce_strength(raw_strength) if raw_strength is not None else None
            if isinstance(strength, dict):
                resolved = {
                    _resolve_strength_inn(part["inn"], cat) for part in strength["ingredients"]
                }
                if len(resolved) < len(strength["ingredients"]):
                    strength = None
            intake_amount = _coerce_intake(raw_intake)
            regimen = _coerce_regimen(raw["regimen"])
            said: set = set()
            for cited_id in turn_ids:
                said |= stated_amounts(transcripts[cited_id])
            if isinstance(strength, dict) and not all(
                part["amount"] in said for part in strength["ingredients"]
            ):
                strength = None
            if isinstance(intake_amount, dict) and intake_amount["amount"] not in said:
                intake_amount = None
            relation_dropped = False
            own: list[str] = []
            another: list[str] = []
            is_discontinued = raw.get("status") == "discontinued"
            if isinstance(strength, dict) or isinstance(intake_amount, dict):
                entry = cat.resolve(raw["name_text"]) if isinstance(raw.get("name_text"), str) else None
                other_texts = [
                    other.get("name_text")
                    for pos, other in enumerate(raw_claims) if pos != index - 1
                ]
                own = own_names_for_claim(raw.get("name_text"), grounded_inn, cat)
                another = another_names_for_claim(
                    own, entry, cat, other_texts, raw.get("name_text"),
                )
                mentions = mentions_for_cited_turns(cited, own, another, is_discontinued)
                if isinstance(strength, dict) and not all(
                    is_amount_grounded(
                        part["amount"], part["unit"], mentions, False,
                    )
                    for part in strength["ingredients"]
                ):
                    strength = None
                    relation_dropped = True
                if isinstance(intake_amount, dict) and not is_amount_grounded(
                    intake_amount["amount"], intake_amount["unit"], mentions, True,
                ):
                    intake_amount = None
                    relation_dropped = True
            if (
                relation_dropped
                and isinstance(regimen, dict)
                and regimen.get("units_per_intake") is not None
                and regimen["units_per_intake"] not in count_values_for_cited_turns(
                    cited, own, another, is_discontinued,
                )
            ):
                regimen = {**regimen, "units_per_intake": None}
            units_sent = (
                isinstance(raw.get("regimen"), dict)
                and raw["regimen"].get("units_per_intake") is not None
            )
            units_dropped = units_sent and (
                not isinstance(regimen, dict) or regimen.get("units_per_intake") is None
            )
            if (raw["strength"] is not None and strength is None and not strength_was_empty) or (
                raw["intake_amount"] is not None and intake_amount is None
            ) or units_dropped:
                # A dropped claim amount takes the other one with it (SPEC §2).
                strength = None
                intake_amount = None
            values = {
                **{key: value for key, value in raw.items() if key != "turn_ids"},
                "inn": grounded_inn,
                "regimen": regimen,
                "intake_amount": intake_amount,
                "strength": strength,
                "claim_id": f"c{index}",
                "audio_evidence": turn_ids,
            }
            claims.append(PatientClaim.model_validate(values))
        return claims
    except (TypeError, ValueError, ValidationError) as exc:
        raise ProviderError("spark", f"malformed patient claims: {exc}", retryable=True) from exc


class MetaClaimExtractor:
    def __init__(
        self, client: MetaClient, guard: SpendGuard, model: str = "muse-spark-1.3",
    ) -> None:
        if "-contributor" in model.strip().casefold():
            raise ValueError("contributor models are not permitted")
        self.client = client
        self.guard = guard
        self.model = model

    def extract(self, turns: list[AudioTurn]) -> tuple[list[PatientClaim], ProviderTrace | None]:
        if not turns:
            return [], None

        transcript = "\n".join(
            f"[{turn.turn_id} {turn.start_ms}–{turn.end_ms} ms, speaker {turn.speaker or 'unknown'}] "
            f"{turn.transcript}"
            for turn in turns
        )
        body = {
            "model": self.model,
            "reasoning_effort": "low",
            "max_tokens": 16000,
            "messages": [
                {"role": "system", "content": _SPARK_CLAIM_PROMPT},
                {"role": "user", "content": transcript},
            ],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "patient_claims", "strict": True, "schema": CLAIMS_SCHEMA,
            }},
        }

        estimate = spark_call_estimate(body)

        def attempt() -> tuple[list[PatientClaim], ProviderTrace]:
            self.guard.check(estimate)
            payload, latency_ms = self.client.post("/chat/completions", json=body)
            try:
                usage = payload["usage"]
                input_tokens = int(usage["prompt_tokens"])
                output_tokens = int(usage["completion_tokens"])
                content = payload["choices"][0]["message"]["content"]
                call_id = payload["id"]
                if not isinstance(call_id, str) or not call_id:
                    raise ValueError("missing id")
                cost = cost_usd(self.model, input_tokens=input_tokens, output_tokens=output_tokens)
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise ProviderError(
                    "spark", "malformed Spark response", retryable=True,
                    billable_uncertain=True, estimated_reason="malformed Spark response",
                ) from exc
            trace = ProviderTrace(
                call_id=call_id,
                model_id=self.model,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
            )
            self.guard.charge_prechecked(trace)
            if payload["choices"][0].get("finish_reason") == "length":
                raise ProviderError(
                    "spark", "Spark reply stopped at the length limit", retryable=False,
                    attempt_trace=trace,
                )
            try:
                claims = parse_claims_json(content, turns)
            except ProviderError as exc:
                raise ProviderError(
                    exc.provider, self.client._safe(str(exc)), retryable=True,
                    attempt_trace=trace,
                ) from None
            return claims, trace

        return with_one_retry(attempt, guard=self.guard, model_id=self.model, estimate=estimate)
