"""The Glimmer LoRA on Modal: the settings fixed before any run, and the plain-Python steps that the GPU
code calls (evidence/finetune/plan.md, "Amended 29 Oct: training on Modal"). Standard library only, so the
unit tests run offline and the same file runs inside Modal's containers (finetune/modal_glimmer.py)."""

import math
import random
from datetime import datetime
from decimal import ROUND_UP, Decimal
from typing import Any

MODEL_ID = "meta-models/Muse-Glimmer-30B"
REVISION = "cec94fcfd6512f2cfe708138c32533b346ea4f69"  # the Hub's main on 29 Oct 2026, pinned
# One 80 GB H100: Modal asks for a payment method before it runs H200s (29 Oct). The 59.6 GB of bf16 weights
# fit with the LoRA, its optimizer and checkpointed activations at micro-batch 2.
GPU = "H100"
CPU_CORES = 8.0
MEMORY_MIB = 32768
# Modal's list prices, read on modal.com/pricing on 29 Oct 2026: the H100, one physical core, one GiB.
USD_PER_S = {"gpu": Decimal("0.001097"), "core": Decimal("0.0000131"), "gib": Decimal("0.00000222")}
DOWNLOAD_TIMEOUT_S = 3600
TRAIN_TIMEOUT_S = 2 * 3600
EVAL_TIMEOUT_S = 2 * 3600

# Rank 16, set explicitly as in the Fireworks plan, with alpha 32 and dropout 0.05. The adapter goes on every
# linear layer of the 52 language-model blocks except the attention's output gate: q, k, v and o, and the
# MLP's gate, up and down. The vision tower stays frozen and untouched.
LORA = {"r": 16, "lora_alpha": 32, "lora_dropout": 0.05, "bias": "none",
        "target_modules": (r".*language_model\.layers\.\d+\."
                           r"(self_attn\.(q|k|v|o)_proj|mlp\.(gate|up|down)_proj)")}
LORA_LAYERS = 52 * 7
TRAIN = {"epochs": 2, "lr": 1e-4, "warmup_steps": 8, "micro_batch": 2, "grad_accum": 8,
         "max_grad_norm": 1.0, "seed": 20261029}
# Inference, the same for base and tuned Glimmer: the model card's recommended sampling, one reply per
# example, and the max_tokens of the product's own claim request (anamnesis/providers/claims.py).
SAMPLING = {"temperature": 1.0, "top_p": 0.95, "top_k": 64}
MAX_TOKENS = 16000
MAX_MODEL_LEN = 20480
EVAL_SEED = 20261029
# The reasoning channel ends and the answer to the user opens with this header (chat_template.jinja).
ANSWER_OPEN = "to=user<|message|>"
TEST_SPLITS = ("test_iid", "test_shift", "test_codeswitch", "test_real")
ROLES = ("system", "user", "assistant")
MESSAGE_WEIGHTS = (0, 0, 1)
IGNORE = -100


def messages_of(row: Any) -> list[dict[str, str]]:
    """One example's three messages as gen.py writes them, without their weights: system and user at weight 0,
    the answer at weight 1. Anything else is refused rather than trained on."""
    messages = row.get("messages") if isinstance(row, dict) else None
    if (not isinstance(messages, list) or not all(isinstance(m, dict) for m in messages)
            or tuple(m.get("role") for m in messages) != ROLES
            or tuple(m.get("weight") for m in messages) != MESSAGE_WEIGHTS
            or not all(isinstance(m.get("content"), str) and m["content"] for m in messages)):
        raise ValueError("an example needs system, user and assistant messages, weighted 0, 0 and 1")
    return [{"role": m["role"], "content": m["content"]} for m in messages]


def prompt_text(tokenizer: Any, conversation: list[dict[str, str]]) -> str:
    """The system and user turns and the assistant's opening, as the chat template renders them."""
    return tokenizer.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)


def prompt_ids(tokenizer: Any, conversation: list[dict[str, str]]) -> list[int]:
    """The prompt's ids, exactly as training masks them (the template writes the BOS itself)."""
    return tokenizer(prompt_text(tokenizer, conversation), add_special_tokens=False)["input_ids"]


def encode(tokenizer: Any, row: Any) -> tuple[list[int], list[int]]:
    """One training example's ids and labels. The prompt is masked with IGNORE; the target is the rest of the
    assistant's turn: its channel header, the answer and its end token."""
    messages = messages_of(row)
    prompt = prompt_text(tokenizer, messages[:2])
    full = tokenizer.apply_chat_template(messages, tokenize=False)
    if not full.startswith(prompt):
        raise ValueError("the chat template's answer doesn't extend its prompt")
    head = prompt_ids(tokenizer, messages[:2])
    tail = tokenizer(full[len(prompt):], add_special_tokens=False)["input_ids"]
    if not tail:
        raise ValueError("an example with no target")
    return head + tail, [IGNORE] * len(head) + tail


def steps_per_epoch(size: int) -> int:
    """Whole optimizer steps only; the few examples left over change with each epoch's shuffle."""
    return size // (TRAIN["micro_batch"] * TRAIN["grad_accum"])


def epoch_order(size: int, epoch: int) -> list[int]:
    """A fixed shuffle of the training set for each epoch."""
    order = list(range(size))
    random.Random(TRAIN["seed"] * 100 + epoch).shuffle(order)
    return order


def learning_rate(step: int, total: int) -> float:
    """Linear warm-up over the first steps, then a cosine decay to 0 at the last step (step counts from 0)."""
    peak, warm = TRAIN["lr"], TRAIN["warmup_steps"]
    if step < warm:
        return peak * (step + 1) / warm
    progress = (step - warm) / max(1, total - warm)
    return peak * 0.5 * (1 + math.cos(math.pi * progress))


def pad_batch(examples: list[tuple[list[int], list[int]]], pad_id: int) -> dict[str, list[list[int]]]:
    """Right-padded ids, labels and attention mask; padding is never a target."""
    width = max(len(ids) for ids, _ in examples)
    return {
        "input_ids": [[*ids, *[pad_id] * (width - len(ids))] for ids, _ in examples],
        "labels": [[*labels, *[IGNORE] * (width - len(labels))] for _, labels in examples],
        "attention_mask": [[1] * len(ids) + [0] * (width - len(ids)) for ids, _ in examples],
    }


def opened_answer(first_text: str) -> bool:
    """Whether the first pass ended by opening the answer to the user, the only place a reply can follow."""
    return first_text.endswith(ANSWER_OPEN)


def usd_per_s(gpu: bool) -> Decimal:
    machine = USD_PER_S["core"] * Decimal(str(CPU_CORES)) + USD_PER_S["gib"] * Decimal(MEMORY_MIB) / 1024
    return machine + (USD_PER_S["gpu"] if gpu else Decimal(0))


def cost_usd(seconds: float, gpu: bool = True) -> Decimal:
    """List price for this many seconds of one container, rounded up."""
    return (usd_per_s(gpu) * Decimal(str(seconds))).quantize(Decimal("0.00001"), rounding=ROUND_UP)


def ledger_line(step: str, run: str, seconds: float, at: datetime) -> dict[str, Any]:
    """One line of evidence/spend/modal_ledger.jsonl: the local wall time around the call at list price. It is
    an estimate: Modal also bills each container's idle minute after its last input, so on 29 Oct these lines
    came to 6% under Modal's billing summary, and the difference went in as its own line."""
    gpu = step != "download"
    return {"model_id": f"glimmer-{step}@modal", "run": run, "gpu": GPU if gpu else None,
            "seconds": round(seconds, 1), "cost_usd": str(cost_usd(seconds, gpu)), "estimated": True,
            "at": at.isoformat(timespec="seconds")}
