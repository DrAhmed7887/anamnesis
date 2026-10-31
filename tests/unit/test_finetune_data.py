"""finetune/gen.py, real_slice.py and score.py, offline: the data is deterministic, every answer passes the
product's own parser with nothing dropped, the held-out drugs and test-only templates stay out of training,
and the scorer gives the answers themselves 100% with nothing harmful."""

import json
import re
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from anamnesis.core.catalogue import normalise
from anamnesis.core.guardrails import assert_no_advice
from anamnesis.providers import SpendGuard
from anamnesis.providers.claims import _SYSTEM_PROMPT, MetaClaimExtractor, parse_claims_json
from anamnesis.providers.meta import MetaClient
from anamnesis.schema import PatientClaim
from finetune import gen, real_slice
from finetune import score as scorer
from finetune.common import DATA_DIR, claim_strings, read_jsonl, turns_from_records
from finetune.drugs import all_names, load_medicines, usable_brand

GENERATED = [split for split, _ in gen.SPLITS]
SPLITS = [*GENERATED, "test_real"]
SIZES = {**dict(gen.SPLITS), "test_real": 33}
ZERO_HARM = {"claims": 0, "amounts": 0, "inns": 0}


@pytest.fixture(scope="module")
def data(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("finetune-data")
    gen.generate(out)
    real_slice.build(out)
    return out


def rows(folder: Path, split: str) -> list[dict]:
    return read_jsonl(folder / f"{split}.jsonl")


def answers(folder: Path, split: str) -> list[dict]:
    return read_jsonl(folder / f"{split}.answers.jsonl")


def literal_claims(answer: str) -> list[dict]:
    """The answer JSON taken at its word: what parse_claims_json gives if it keeps every field."""
    return [
        PatientClaim.model_validate({
            **{key: value for key, value in claim.items() if key != "turn_ids"},
            "claim_id": f"c{index}", "audio_evidence": claim["turn_ids"],
        }).model_dump(mode="json")
        for index, claim in enumerate(json.loads(answer)["claims"], start=1)
    ]


def test_same_seed_same_files_byte_for_byte(data, tmp_path):
    again = tmp_path / "again"
    gen.generate(again)
    real_slice.build(again)
    names = sorted(path.name for path in data.iterdir())
    assert names == sorted(path.name for path in again.iterdir())
    for name in names:
        assert (data / name).read_bytes() == (again / name).read_bytes(), name
    other = tmp_path / "other"
    gen.generate(other, seed=gen.SEED + 1)
    assert (other / "train.jsonl").read_bytes() != (data / "train.jsonl").read_bytes()
    if (DATA_DIR / "train.jsonl").exists():  # the files on disk are what the code writes
        for name in names:
            assert (DATA_DIR / name).read_bytes() == (data / name).read_bytes(), name


def test_split_sizes(data):
    for split in SPLITS:
        assert len(rows(data, split)) == SIZES[split], split
        assert len(answers(data, split)) == SIZES[split], split
    assert {note for line in answers(data, "test_real") for note in line["notes"]} == set(real_slice.SCRIPTS)


def test_lines_hold_only_weighted_messages_with_the_products_prompt(data):
    for split in SPLITS:
        for row in rows(data, split):
            assert list(row) == ["messages"]
            system, user, assistant = row["messages"]
            assert [message["role"] for message in row["messages"]] == ["system", "user", "assistant"]
            assert [message["weight"] for message in row["messages"]] == [0, 0, 1]
            assert system["content"] == f"{_SYSTEM_PROMPT}\nReasoning strength: low"
            assert user["content"] and assistant["content"]


def test_user_message_is_exactly_what_the_extractor_sends(data, tmp_path):
    train, train_answers = rows(data, "train"), answers(data, "train")
    picks = [0, *[index for index, line in enumerate(train_answers) if len(line["turns"]) > 2][:3]]
    for index in picks:
        sent = []

        def respond(request, index=index, sent=sent):
            sent.append(json.loads(request.content))
            return httpx.Response(200, json={
                "id": "chat_finetune", "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                "choices": [{"message": {"content": train[index]["messages"][2]["content"]}}],
            })

        client = MetaClient("test-key", transport=httpx.MockTransport(respond))
        extractor = MetaClaimExtractor(client, SpendGuard(tmp_path / f"ledger{index}.jsonl", Decimal("1")))
        claims, _ = extractor.extract(turns_from_records(train_answers[index]["turns"]))
        assert sent[0]["messages"][1]["content"] == train[index]["messages"][1]["content"]
        assert [claim.model_dump(mode="json") for claim in claims] == train_answers[index]["claims"]


def test_held_out_drugs_and_test_only_templates_stay_out_of_training(data):
    meta = json.loads((data / "meta.json").read_text(encoding="utf-8"))
    held = {item["key"] for item in meta["held_out"]}
    test_only = set(meta["templates"]["test_only"])
    assert len(held) == 10 and all(key.startswith("rxnorm:") for key in held) and len(test_only) >= 20
    medicines = {medicine.key: medicine for medicine in load_medicines()}
    held_names = {normalise(name) for key in held for name in all_names(medicines[key])}
    for split in ("train", "val", "test_iid", "test_codeswitch"):
        for row, line in zip(rows(data, split), answers(data, split), strict=True):
            assert not held & set(line["drugs"]) and not test_only & set(line["templates"]), line["id"]
            words = f" {normalise(row['messages'][1]['content'])} "
            assert not [name for name in held_names if f" {name} " in words], line["id"]
    shift = answers(data, "test_shift")
    assert all(set(line["drugs"]) <= held and set(line["templates"]) <= test_only for line in shift)
    assert {key for line in shift for key in line["drugs"]} == held


def test_every_answer_parses_to_its_intended_claims_with_nothing_dropped(data):
    for split in SPLITS:
        for row, line in zip(rows(data, split), answers(data, split), strict=True):
            answer = row["messages"][2]["content"]
            parsed = [claim.model_dump(mode="json")
                      for claim in parse_claims_json(answer, turns_from_records(line["turns"]))]
            assert parsed == literal_claims(answer) == line["claims"], line["id"]
            assert line["claims"], line["id"]


def test_every_amount_is_a_strength_rxnorm_lists_for_that_medicine(data):
    medicines = {medicine.key: medicine for medicine in load_medicines()}
    to_mg = {"mg": Decimal(1), "mcg": Decimal("0.001"), "g": Decimal(1000)}
    for split in GENERATED:
        for line in answers(data, split):
            for key, claim in zip(line["drugs"], line["claims"], strict=True):
                marketed = {strength.mg for strength in medicines[key].strengths}
                parts = [claim["intake_amount"]] + (claim["strength"] or {}).get("ingredients", [])
                for part in filter(None, parts):
                    assert Decimal(part["amount"]) * to_mg[part["unit"]] in marketed, (line["id"], part)


def test_no_claim_field_fails_the_advice_check(data):
    """Only where the product runs the check: name_text, inn and every ingredient inn. The patient's speech
    isn't checked, so English notes say "I take", as every real transcript does."""
    for split in SPLITS:
        for row in rows(data, split):
            strings = claim_strings(row["messages"][2]["content"])
            assert strings
            for text in strings:
                assert_no_advice(text)
                assert not re.search(r"\btak(e|es|ing)\b", text, re.IGNORECASE)
    english = [row["messages"][1]["content"] for split in GENERATED
               for row, line in zip(rows(data, split), answers(data, split), strict=True)
               if line["mix"] == "en"]
    saying_take = [text for text in english if re.search(r"\btake\b", text)]
    assert len(saying_take) > len(english) / 3


def test_the_noise_rate_is_set_and_recorded(data):
    meta = json.loads((data / "meta.json").read_text(encoding="utf-8"))
    assert meta["noise_rate"] == gen.NOISE_RATE
    for split, size in gen.SPLITS:
        lines = answers(data, split)
        noisy = [line for line in lines if line["noise"]]
        assert len(noisy) == meta["splits"][split]["noisy"] == round(size * gen.NOISE_RATE), split
        for line in noisy:
            assert line["noise"][0]["text"] in " ".join(turn["transcript"] for turn in line["turns"])


def test_the_answers_score_100_percent_with_nothing_harmful(data):
    for split in SPLITS:
        replies = {index: row["messages"][2]["content"] for index, row in enumerate(rows(data, split))}
        report = scorer.score(answers(data, split), replies)
        assert report["outcomes"]["parsed"] == SIZES[split] and report["all_correct"] == SIZES[split]
        assert set(report["fields"].values()) == {report["claims"]}
        assert report["missing"] == report["extra"] == 0 and report["misses"] == []
        assert report["harm"] == {"before": ZERO_HARM, "after": ZERO_HARM}


def test_the_scorer_counts_drops_invalid_json_and_harm(data):
    lines = answers(data, "test_real")
    index = next(i for i, line in enumerate(lines) if line["notes"] == ["U1"])  # "I take Concor five ..."
    claim = {"name_text": "Concor", "inn": None, "strength": None,
             "intake_amount": {"inn": "Concor", "amount": "5", "unit": "mg"},
             "regimen": {"units_per_intake": None, "intakes_per_day": "1", "as_needed": None},
             "status": "active", "turn_ids": ["turn-0"]}

    def reply(**change) -> str:
        return json.dumps({"claims": [{**claim, **change}]})

    cases = {
        "right": reply(),
        "inferred": reply(inn="bisoprolol"),
        "unstated": reply(intake_amount={"inn": "Concor", "amount": "10", "unit": "mg"}),
        "ungrounded": reply(name_text="Concor Plus"),
        "fenced": f"```json\n{reply()}\n```",
    }
    results = {name: scorer.score_example(lines[index], text) for name, text in cases.items()}
    assert results["right"]["problems"] == [] and results["right"]["harm_before"] == []
    # batch 24 nulls the unsaid inn, so it is no longer kept
    assert results["inferred"]["harm_before"] and not results["inferred"]["harm_after"]
    assert results["unstated"]["harm_before"] and not results["unstated"]["harm_after"]  # the amount isn't
    assert results["unstated"]["problems"] == ["c1 intake: got null, want 5 mg"]
    assert results["ungrounded"]["outcome"] == "dropped"
    assert results["fenced"]["outcome"] == "invalid_json"


def test_the_brand_rule_drops_the_oddities():
    for name in ("Wal-Zyr", "Wal-itin", "Aller-Tec", "Mapap", "Zantac Reformulated Aug 2022", "Levo-T"):
        assert usable_brand(name, ("cetirizine",)) is None, name
    assert usable_brand("Bayer Aspirin", ("acetylsalicylic acid", "aspirin")) is None
    assert usable_brand("MILLIPRED", ("prednisolone",)) == "Millipred"
    assert usable_brand("Zyrtec", ("cetirizine",)) == "Zyrtec"
    kept = {brand for medicine in load_medicines() for brand in medicine.brands}
    assert not {"Wal-Zyr", "Wal-itin", "Aller-Tec", "Mapap", "Bayer Aspirin"} & kept
    assert {"Concor", "Beloc-Zok", "Zyrtec", "Tylenol", "Panadol"} <= kept
