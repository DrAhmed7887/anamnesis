"""The Glimmer LoRA's offline pieces: the settings, the training targets, the cost lines, the Modal file's
imports and the Spark baseline's capture (evidence/finetune/plan.md, "Amended 29 Oct: training on Modal")."""

import ast
import json
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from anamnesis.providers.base import ProviderError
from anamnesis.providers.spend import SpendCapExceeded
from finetune import glimmer, spark_eval
from finetune.common import DATA_DIR, read_jsonl

ROOT = Path(__file__).resolve().parents[2]


class FakeTokenizer:
    """A chat template shaped like Glimmer's: the prompt ends by opening the assistant's turn, and the answer
    adds its channel header, the text and the end token. One id per character."""

    pad_token_id = 0

    def __init__(self, answer_extends_prompt: bool = True) -> None:
        self.answer_extends_prompt = answer_extends_prompt

    def apply_chat_template(self, messages, add_generation_prompt=False, tokenize=False):
        assert tokenize is False
        turns = [m for m in messages if m["role"] != "assistant"]
        text = "<s>" + "".join(f"<{m['role']}>{m['content']}<eot>" for m in turns)
        if add_generation_prompt:
            return text + "<start>assistant"
        answer = next(m["content"] for m in messages if m["role"] == "assistant")
        opening = "<start>assistant" if self.answer_extends_prompt else "<start>model"
        return text + f"{opening} to=user<msg>{answer}<eot>"

    def __call__(self, text, add_special_tokens=True):
        assert add_special_tokens is False
        return {"input_ids": [ord(char) for char in text]}


def row(answer: str = '{"claims": []}', **changes) -> dict:
    messages = [{"role": "system", "content": "Extract.", "weight": 0},
                {"role": "user", "content": "[turn-0] I take Concor", "weight": 0},
                {"role": "assistant", "content": answer, "weight": 1}]
    return {"messages": [{**message, **changes.get(message["role"], {})} for message in messages]}


def text_of(ids: list[int]) -> str:
    return "".join(chr(i) for i in ids)


# The rows gen.py wrote are the rows trained on.
@pytest.mark.parametrize("split", ["train", "val", *glimmer.TEST_SPLITS])
def test_every_committed_example_has_the_three_weighted_messages(split):
    rows = read_jsonl(DATA_DIR / f"{split}.jsonl")
    assert rows
    for line in rows:
        messages = glimmer.messages_of(line)
        assert [m["role"] for m in messages] == ["system", "user", "assistant"]
        assert messages[0]["content"].endswith("Reasoning strength: low")
        assert "weight" not in messages[0]


@pytest.mark.parametrize("bad", [
    None, {}, {"messages": "text"},
    row(system={"weight": 1}), row(assistant={"weight": 0}), row(user={"role": "assistant"}),
    row(answer=""), row(user={"content": None}),
    {"messages": row()["messages"][:2]},
    {"messages": [*row()["messages"], {"role": "user", "content": "more", "weight": 0}]},
])
def test_messages_refuses_any_other_shape(bad):
    with pytest.raises(ValueError):
        glimmer.messages_of(bad)


def test_the_eval_prompt_never_carries_the_answer():
    conversation = glimmer.messages_of(row(answer='{"claims": ["secret"]}'))[:2]
    assert "secret" not in json.dumps(conversation)


def test_encode_masks_the_prompt_and_targets_the_whole_answer_turn():
    tokenizer = FakeTokenizer()
    ids, labels = glimmer.encode(tokenizer, row(answer='{"claims": []}'))
    prompt = glimmer.prompt_ids(tokenizer, glimmer.messages_of(row())[:2])
    assert len(ids) == len(labels)
    assert ids[:len(prompt)] == prompt
    assert labels[:len(prompt)] == [glimmer.IGNORE] * len(prompt)
    assert text_of(labels[len(prompt):]) == ' to=user<msg>{"claims": []}<eot>'
    assert text_of(ids).startswith("<s><system>Extract.<eot>")


def test_encode_refuses_a_template_whose_answer_does_not_extend_the_prompt():
    with pytest.raises(ValueError, match="extend"):
        glimmer.encode(FakeTokenizer(answer_extends_prompt=False), row())


def test_the_lora_targets_every_language_model_linear_but_the_attention_gate():
    names = [f"model.language_model.layers.{layer}.{module}" for layer in range(52) for module in (
        "self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj", "self_attn.o_proj", "self_attn.gate_proj",
        "mlp.gate_proj", "mlp.up_proj", "mlp.down_proj")]
    others = ["model.vision_tower.layers.0.attn.q_proj", "model.vision_tower.layers.0.mlp.fc1", "lm_head",
              "model.language_model.embed_tokens", "model.vision_adapter.fc1"]
    hits = [name for name in names + others if re.fullmatch(glimmer.LORA["target_modules"], name)]
    assert len(hits) == glimmer.LORA_LAYERS == 364
    assert not any(name.endswith("self_attn.gate_proj") or "vision" in name for name in hits)
    assert glimmer.LORA["r"] == 16


def test_two_epochs_of_whole_steps_and_a_fixed_shuffle_per_epoch():
    assert glimmer.steps_per_epoch(1200) == 75
    first, again, second = (glimmer.epoch_order(1200, 0), glimmer.epoch_order(1200, 0),
                            glimmer.epoch_order(1200, 1))
    assert first == again and first != second
    assert sorted(first) == sorted(second) == list(range(1200))


def test_the_learning_rate_warms_up_then_decays_to_zero():
    total, peak = 150, glimmer.TRAIN["lr"]
    rates = [glimmer.learning_rate(step, total) for step in range(total)]
    warm = glimmer.TRAIN["warmup_steps"]
    assert rates[0] == pytest.approx(peak / warm)
    assert rates[warm - 1] == pytest.approx(peak) and rates[warm] == pytest.approx(peak)
    assert all(a >= b for a, b in zip(rates[warm:], rates[warm + 1:], strict=False))
    assert rates[-1] < peak * 0.001


def test_padding_is_never_a_target():
    batch = glimmer.pad_batch([([5, 6, 7], [glimmer.IGNORE, 6, 7]), ([8], [8])], pad_id=0)
    assert batch["input_ids"] == [[5, 6, 7], [8, 0, 0]]
    assert batch["labels"] == [[glimmer.IGNORE, 6, 7], [8, glimmer.IGNORE, glimmer.IGNORE]]
    assert batch["attention_mask"] == [[1, 1, 1], [1, 0, 0]]


@pytest.mark.parametrize(("text", "opened"), [
    (" to=user<|message|>", True),
    (" to=self<|message|>short<|eom|><|start|>assistant to=user<|message|>", True),
    (" to=self<|message|>reasoning cut off", False),
    ("", False),
    (" to=user<|message|>{}", False),
])
def test_a_reply_follows_only_an_opened_answer(text, opened):
    assert glimmer.opened_answer(text) is opened


def test_cost_lines_use_the_list_price_and_go_to_the_modal_ledger():
    assert glimmer.cost_usd(3600) == Decimal("4.58223")
    assert glimmer.cost_usd(3600, gpu=False) == Decimal("0.63303")
    at = datetime(2026, 10, 29, 9, 0, tzinfo=UTC)
    line = glimmer.ledger_line("train", "r1", 600.04, at)
    assert line == {"model_id": "glimmer-train@modal", "run": "r1", "gpu": "H100", "seconds": 600.0,
                    "cost_usd": "0.76376", "estimated": True, "at": "2026-10-29T09:00:00+00:00"}
    assert glimmer.ledger_line("download", "r1", 60, at)["gpu"] is None


def test_the_modal_file_imports_nothing_the_containers_lack():
    tree = ast.parse((ROOT / "finetune/modal_glimmer.py").read_text(encoding="utf-8"))
    top = {alias.name.split(".")[0] for node in tree.body if isinstance(node, ast.Import)
           for alias in node.names}
    top |= {node.module.split(".")[0] for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module}
    assert top <= {"json", "os", "subprocess", "sys", "time", "datetime", "pathlib", "modal", "glimmer"}


class FakeMeta:
    def __init__(self, replies):
        self.replies, self.bodies = list(replies), []

    def post(self, path, json):
        self.bodies.append(json)
        content = self.replies.pop(0)
        return ({"id": f"call-{len(self.bodies)}", "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                 "choices": [{"message": {"content": content}, "finish_reason": "stop"}]}, 7)

    def _safe(self, text):
        return text


def test_capturing_keeps_each_reply_and_forwards_the_rest():
    capture = spark_eval.Capturing(FakeMeta(['{"claims": []}']))
    payload, latency = capture.post("/chat/completions", json={"model": "m"})
    assert latency == 7 and payload["id"] == "call-1"
    assert capture.replies == [{"reply": '{"claims": []}', "finish": "stop", "latency_ms": 7,
                                "usage": {"prompt_tokens": 10, "completion_tokens": 5}}]
    assert capture._safe("x") == "x"


class FakeExtractor:
    """Posts through the capture like MetaClaimExtractor: a rejected reply is asked for once more."""

    def __init__(self, capture, outcomes):
        self.capture, self.outcomes = capture, list(outcomes)

    def extract(self, turns):
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        for _ in range(outcome):
            self.capture.post("/chat/completions", json={})
        return [], None


def answers(n: int) -> list[dict]:
    turn = {"turn_id": "turn-0", "start_ms": 0, "end_ms": 1000, "transcript": "Concor", "speaker": None,
            "lang_hint": "en"}
    return [{"index": i, "turns": [turn]} for i in range(n)]


def test_run_split_scores_the_first_reply_and_counts_the_second(tmp_path):
    capture = spark_eval.Capturing(FakeMeta(["first", "first-of-two", "second-of-two"]))
    out = tmp_path / "split.jsonl"
    error = ProviderError("spark", "rejected", retryable=False)
    counts = spark_eval.run_split(FakeExtractor(capture, [1, 2, error]), capture, answers(3), out)
    lines = [json.loads(line) for line in out.read_text().splitlines()]
    assert [line["reply"] for line in lines] == ["first", "first-of-two", None]
    assert [line["attempts"] for line in lines] == [1, 2, 0]
    assert lines[2]["error"] and lines[0]["error"] is None
    assert counts == {"examples": 3, "replies": 2, "second_attempts": 1, "errors": 1}


def test_run_split_stops_at_a_spend_cap_instead_of_writing_empty_replies(tmp_path):
    capture = spark_eval.Capturing(FakeMeta(["first"]))
    out = tmp_path / "split.jsonl"
    with pytest.raises(SpendCapExceeded):
        spark_eval.run_split(FakeExtractor(capture, [1, SpendCapExceeded("cap")]), capture, answers(2), out)
    assert len(out.read_text().splitlines()) == 1


def test_run_split_refuses_answer_lines_out_of_order(tmp_path):
    capture = spark_eval.Capturing(FakeMeta([]))
    rows = [{**answers(1)[0], "index": 3}]
    with pytest.raises(ValueError, match="index"):
        spark_eval.run_split(FakeExtractor(capture, [0]), capture, rows, tmp_path / "split.jsonl")
