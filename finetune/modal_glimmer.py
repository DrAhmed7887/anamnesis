"""Train and test the Glimmer LoRA on Modal (evidence/finetune/plan.md, "Amended 29 Oct: training on Modal").

    ~/.local/bin/modal run finetune/modal_glimmer.py --step download
    ~/.local/bin/modal run finetune/modal_glimmer.py --step train --run r1 [--smoke]
    ~/.local/bin/modal run finetune/modal_glimmer.py --step eval --run r1 [--smoke]

Every step first runs scripts/spend_check.py with the most it can cost (its timeout at Modal's list price),
and afterwards appends what it cost (the local wall time at that price, an estimate checked against
`modal billing summary`) to evidence/spend/modal_ledger.jsonl. The weights come from the Hub at a pinned
revision into a Modal volume. The adapter stays in a second volume. Only the generated fine-tune data and
the 33 synthetic-voice transcripts go to Modal (docs/DATA_HANDLING.md).

Eval runs base and tuned Glimmer in one vLLM engine, in two passes per example. The first pass is free: the
model reasons, until it opens its answer to the user. The second pass continues from there under the product's
claims JSON schema, as Meta's API constrains Spark 1.3's reply after its reasoning. Replies come back to
evidence/finetune/runs/<run>/<system>/<split>.jsonl for finetune/score.py; the reasoning goes to
evidence/raw/finetune/ (git-ignored).
"""

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import glimmer  # noqa: E402

ROOT = HERE.parent
DATA = ROOT / "finetune" / "data"
RUNS_DIR = ROOT / "evidence" / "finetune" / "runs"
RAW_DIR = ROOT / "evidence" / "raw" / "finetune"
LEDGER = ROOT / "evidence" / "spend" / "modal_ledger.jsonl"
WEIGHTS = f"/weights/{glimmer.REVISION}"
SYSTEMS = ("glimmer-base", "glimmer-lora")
SPECIAL = ("<|eot|>", "<|eom|>", "<|start|>", "<|message|>", "<|end_of_text|>")
SMOKE = {"train_rows": 32, "val_rows": 8, "max_steps": 2, "test_rows": 2, "max_tokens": 2000}

weights = modal.Volume.from_name("anamnesis-glimmer-weights", create_if_missing=True)
runs = modal.Volume.from_name("anamnesis-glimmer-runs", create_if_missing=True)
VOLUMES = {"/weights": weights, "/runs": runs}
hub_image = (modal.Image.debian_slim(python_version="3.12")
             .pip_install("huggingface_hub==2.3.0", "hf_xet==1.7.1")
             .add_local_file(HERE / "glimmer.py", "/root/glimmer.py"))
train_image = (modal.Image.debian_slim(python_version="3.12")
               .pip_install("torch==2.15.0", "transformers==5.21.0", "peft==0.21.2", "accelerate==1.15.0",
                            "huggingface_hub==2.3.0")
               .add_local_file(HERE / "glimmer.py", "/root/glimmer.py"))
# FlashInfer's sampler needs a CUDA compiler that the slim image lacks (29 Oct smoke run), so vLLM samples
# with its PyTorch top-k/top-p path: the same settings, drawn by a different kernel.
eval_image = (modal.Image.debian_slim(python_version="3.12")
              .pip_install("vllm==0.32.0")
              .env({"VLLM_USE_FLASHINFER_SAMPLER": "0"})
              .add_local_file(HERE / "glimmer.py", "/root/glimmer.py"))
app = modal.App("anamnesis-glimmer-lora")
MACHINE = {"cpu": glimmer.CPU_CORES, "memory": glimmer.MEMORY_MIB, "volumes": VOLUMES}


@app.function(image=hub_image, timeout=glimmer.DOWNLOAD_TIMEOUT_S, **MACHINE)
def download() -> dict:
    from huggingface_hub import snapshot_download

    clock = time.monotonic()
    snapshot_download(glimmer.MODEL_ID, revision=glimmer.REVISION, local_dir=WEIGHTS)
    weights.commit()
    files = [path for path in Path(WEIGHTS).rglob("*") if path.is_file() and ".cache" not in path.parts]
    return {"revision": glimmer.REVISION, "files": len(files),
            "gb": round(sum(path.stat().st_size for path in files) / 1e9, 2),
            "seconds": round(time.monotonic() - clock, 1)}


def _tensors(batch: dict) -> dict:
    import torch

    return {key: torch.tensor(value, dtype=torch.long, device="cuda") for key, value in batch.items()}


def _validation_loss(model, examples: list, pad_id: int) -> float:
    """Mean loss per target token over the validation set."""
    import torch

    model.eval()
    total, count = 0.0, 0
    with torch.no_grad():
        for start in range(0, len(examples), 4):
            chunk = examples[start:start + 4]
            targets = sum(1 for _, labels in chunk for label in labels if label != glimmer.IGNORE)
            total += model(**_tensors(glimmer.pad_batch(chunk, pad_id))).loss.item() * targets
            count += targets
    model.train()
    return round(total / count, 4)


@app.function(image=train_image, gpu=glimmer.GPU, timeout=glimmer.TRAIN_TIMEOUT_S, **MACHINE)
def train(run: str, train_rows: list, val_rows: list, max_steps: int | None = None) -> dict:
    import peft
    import torch
    import transformers
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForImageTextToText, AutoTokenizer

    clock = time.monotonic()
    settings = glimmer.TRAIN
    torch.manual_seed(settings["seed"])
    tokenizer = AutoTokenizer.from_pretrained(WEIGHTS)
    train_set = [glimmer.encode(tokenizer, row) for row in train_rows]
    val_set = [glimmer.encode(tokenizer, row) for row in val_rows]
    ids, labels = train_set[0]
    first_target = next(i for i, label in enumerate(labels) if label != glimmer.IGNORE)
    check = {"prompt_end": tokenizer.decode(ids[max(0, first_target - 6):first_target]),
             "target": tokenizer.decode(ids[first_target:]),
             "special_ids": {token: tokenizer.convert_tokens_to_ids(token) for token in SPECIAL},
             "pad_id": tokenizer.pad_token_id}
    print(json.dumps(check, ensure_ascii=False))

    model = AutoModelForImageTextToText.from_pretrained(WEIGHTS, dtype=torch.bfloat16, device_map={"": 0})
    load_s = round(time.monotonic() - clock, 1)
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model = get_peft_model(model, LoraConfig(task_type="CAUSAL_LM", **glimmer.LORA))
    adapted = {name.split(".lora_A.")[0] for name, _ in model.named_parameters() if ".lora_A." in name}
    if len(adapted) != glimmer.LORA_LAYERS:
        raise RuntimeError(f"the LoRA is on {len(adapted)} layers, not {glimmer.LORA_LAYERS}")
    params = [param for param in model.parameters() if param.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=settings["lr"], weight_decay=0.0)
    micro, accum = settings["micro_batch"], settings["grad_accum"]
    per_epoch = glimmer.steps_per_epoch(len(train_set))
    total = per_epoch * settings["epochs"] if max_steps is None else max_steps
    history, val_losses, tokens, step = [], [], 0, 0
    model.train()
    train_clock = time.monotonic()
    for epoch in range(settings["epochs"]):
        order = glimmer.epoch_order(len(train_set), epoch)
        for start in range(0, per_epoch * micro * accum, micro * accum):
            if step >= total:
                break
            lr = glimmer.learning_rate(step, total)
            for group in optimizer.param_groups:
                group["lr"] = lr
            step_loss = 0.0
            for offset in range(start, start + micro * accum, micro):
                batch = _tensors(glimmer.pad_batch([train_set[i] for i in order[offset:offset + micro]],
                                                   tokenizer.pad_token_id))
                loss = model(**batch).loss
                (loss / accum).backward()
                step_loss += loss.item() / accum
                tokens += int(batch["attention_mask"].sum())
            norm = torch.nn.utils.clip_grad_norm_(params, settings["max_grad_norm"])
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            step += 1
            history.append({"step": step, "epoch": epoch + 1, "loss": round(step_loss, 4), "lr": lr,
                            "grad_norm": round(float(norm), 4)})
            if step % 10 == 0 or step == total:
                rate = tokens / (time.monotonic() - train_clock)
                print(f"step {step}/{total} loss {step_loss:.4f} lr {lr:.2e} {rate:.0f} tok/s")
        val_losses.append({"epoch": epoch + 1, "after_step": step,
                           "val_loss": _validation_loss(model, val_set, tokenizer.pad_token_id)})
        print(json.dumps(val_losses[-1]))
        if step >= total:
            break
    adapter = f"/runs/{run}/adapter"
    model.save_pretrained(adapter)
    metrics = {"run": run, "model": glimmer.MODEL_ID, "revision": glimmer.REVISION, "lora": glimmer.LORA,
               "train": settings, "examples": len(train_set), "val_examples": len(val_set), "steps": step,
               "tokens_seen": tokens, "load_s": load_s, "train_s": round(time.monotonic() - train_clock, 1),
               "peak_gib": round(torch.cuda.max_memory_allocated() / 2**30, 1),
               "trainable": sum(param.numel() for param in params), "adapted_layers": len(adapted),
               "adapter_files": sorted(path.name for path in Path(adapter).iterdir()),
               "versions": {"torch": str(torch.__version__), "transformers": transformers.__version__,
                            "peft": peft.__version__},
               "check": check, "val_losses": val_losses, "history": history}
    Path(f"/runs/{run}/train.json").write_text(json.dumps(metrics, indent=1, ensure_ascii=False))
    runs.commit()
    return metrics


def _two_passes(llm, tokenizer, conversations: list, lora, schema: dict, max_tokens: int) -> dict:
    """One reply per conversation: free reasoning until the answer opens, then the answer under the schema."""
    from vllm import SamplingParams
    from vllm.sampling_params import StructuredOutputsParams

    clock = time.monotonic()
    stops = [tokenizer.convert_tokens_to_ids("<|eot|>"), tokenizer.eos_token_id]
    prompts = [glimmer.prompt_ids(tokenizer, conversation) for conversation in conversations]
    firsts = llm.generate(
        [{"prompt_token_ids": prompt} for prompt in prompts],
        [SamplingParams(**glimmer.SAMPLING, seed=glimmer.EVAL_SEED + i, max_tokens=max_tokens,
                        stop=[glimmer.ANSWER_OPEN], include_stop_str_in_output=True,
                        skip_special_tokens=False, stop_token_ids=stops) for i in range(len(prompts))],
        lora_request=lora)
    rows, follow = [], []
    for i, (prompt, result) in enumerate(zip(prompts, firsts, strict=True)):
        first = result.outputs[0]
        opened = glimmer.opened_answer(first.text)
        rows.append({"index": i, "reply": None, "opened_answer": opened, "first_tokens": len(first.token_ids),
                     "first_finish": first.finish_reason, "first_text": first.text})
        budget = max_tokens - len(first.token_ids)
        if opened and budget > 0:
            # vLLM's default, as pre-registered: whitespace stays free. In the 29 Oct smoke runs base Glimmer
            # sometimes filled it until the limit; vLLM 0.32 only removes it engine-wide and then drops the
            # spaces in ", " and ": " too, the separators the tuned model was trained on.
            constraint = StructuredOutputsParams(json=schema)
            follow.append((i, {"prompt_token_ids": [*prompt, *first.token_ids]},
                           SamplingParams(**glimmer.SAMPLING, seed=glimmer.EVAL_SEED + i, max_tokens=budget,
                                          stop_token_ids=stops, structured_outputs=constraint)))
    if follow:
        answers = llm.generate([prompt for _, prompt, _ in follow], [params for _, _, params in follow],
                               lora_request=lora)
        for (i, _, _), result in zip(follow, answers, strict=True):
            answer = result.outputs[0]
            rows[i] = {**rows[i], "reply": answer.text, "answer_tokens": len(answer.token_ids),
                       "answer_finish": answer.finish_reason}
    return {"wall_s": round(time.monotonic() - clock, 1), "rows": rows}


@app.function(image=eval_image, gpu=glimmer.GPU, timeout=glimmer.EVAL_TIMEOUT_S, **MACHINE)
def evaluate(run: str, splits: dict, schema: dict, max_tokens: int, out: str) -> dict:
    """Each system and split is saved to the volume as it finishes, and a split already saved there is read
    back instead of run again: on 29 Oct a dropped laptop connection cancelled a run 17 minutes in."""
    import vllm

    clock = time.monotonic()
    runs.reload()
    saved = {(system, split): Path(f"/runs/{out}/eval/{system}/{split}.json")
             for system in SYSTEMS for split in splits}
    done = {key: json.loads(path.read_text(encoding="utf-8")) for key, path in saved.items() if path.exists()}
    result = {"run": run, "vllm": vllm.__version__, "max_tokens": max_tokens, "resumed": len(done),
              "load_s": 0.0}
    todo = [key for key in saved if key not in done]
    if todo:
        from vllm import LLM
        from vllm.lora.request import LoRARequest

        llm = LLM(model=WEIGHTS, enable_lora=True, max_lora_rank=glimmer.LORA["r"], max_loras=1,
                  max_model_len=glimmer.MAX_MODEL_LEN, limit_mm_per_prompt={"image": 0, "video": 0},
                  seed=glimmer.EVAL_SEED)
        tokenizer = llm.get_tokenizer()
        loras = {"glimmer-base": None,
                 "glimmer-lora": LoRARequest("glimmer-lora", 1, f"/runs/{run}/adapter")}
        result["load_s"] = round(time.monotonic() - clock, 1)
        for system, split in todo:
            outcome = _two_passes(llm, tokenizer, splits[split], loras[system], schema, max_tokens)
            saved[(system, split)].parent.mkdir(parents=True, exist_ok=True)
            saved[(system, split)].write_text(json.dumps(outcome, ensure_ascii=False), encoding="utf-8")
            runs.commit()
            done[(system, split)] = outcome
    result["systems"] = {system: {split: done[(system, split)] for split in splits} for system in SYSTEMS}
    return result


def _read(path: Path) -> list:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _gate(usd) -> None:
    """scripts/spend_check.py with this step's most, before anything is sent."""
    check = subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/spend_check.py"),
                            "--next", f"modal={usd}"], cwd=ROOT)
    if check.returncode != 0:
        raise SystemExit("spend_check.py says STOP: nothing was sent to Modal")


def _charge(step: str, run: str, seconds: float) -> None:
    line = glimmer.ledger_line(step, run, seconds, datetime.now(UTC))
    with LEDGER.open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps(line) + "\n")
    print(f"charged {line['model_id']} {line['seconds']} s ${line['cost_usd']} (estimate)")


def _schema() -> dict:
    """The product's CLAIMS_SCHEMA, read through the repo's own environment."""
    code = ("import json; from anamnesis.providers.claims import CLAIMS_SCHEMA; "
            "print(json.dumps(CLAIMS_SCHEMA))")
    out = subprocess.run([str(ROOT / ".venv/bin/python"), "-c", code], cwd=ROOT, capture_output=True,
                         text=True, check=True, env={**os.environ, "PYTHONPATH": str(ROOT)})
    return json.loads(out.stdout)


def _train(run: str, smoke: bool) -> None:
    train_rows, val_rows = _read(DATA / "train.jsonl"), _read(DATA / "val.jsonl")
    if smoke:
        train_rows, val_rows = train_rows[:SMOKE["train_rows"]], val_rows[:SMOKE["val_rows"]]
    metrics = train.remote(run, train_rows, val_rows, SMOKE["max_steps"] if smoke else None)
    out = RUNS_DIR / run
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(metrics, indent=1, ensure_ascii=False) + "\n"
    (out / "train.json").write_text(text, encoding="utf-8")
    keys = ("steps", "tokens_seen", "load_s", "train_s", "peak_gib", "trainable", "val_losses", "check")
    print(json.dumps({key: metrics[key] for key in keys}, ensure_ascii=False))


def _eval(run: str, smoke: bool) -> None:
    limit = SMOKE["test_rows"] if smoke else None
    splits = {split: [glimmer.messages_of(row)[:2] for row in _read(DATA / f"{split}.jsonl")[:limit]]
              for split in glimmer.TEST_SPLITS}
    out = f"smoke-{run}" if smoke else run  # smoke replies are never scored (plan.md)
    max_tokens = SMOKE["max_tokens"] if smoke else glimmer.MAX_TOKENS
    result = evaluate.remote(run, splits, _schema(), max_tokens, out)
    summary = {key: result[key] for key in ("run", "vllm", "load_s", "max_tokens", "resumed")}
    for system, by_split in result["systems"].items():
        for split, outcome in by_split.items():
            kept, raw = RUNS_DIR / out / system / f"{split}.jsonl", RAW_DIR / out / system / f"{split}.jsonl"
            for path in (kept, raw):
                path.parent.mkdir(parents=True, exist_ok=True)
            rows = outcome["rows"]
            kept.write_text("".join(json.dumps({k: v for k, v in row.items() if k != "first_text"},
                                               ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
            raw.write_text("".join(json.dumps({"index": row["index"], "first_text": row["first_text"]},
                                              ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
            summary[f"{system}/{split}"] = {"wall_s": outcome["wall_s"], "examples": len(rows),
                                            "opened_answer": sum(row["opened_answer"] for row in rows)}
    (RUNS_DIR / out / "eval.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))


@app.local_entrypoint()
def main(step: str, run: str = "r1", smoke: bool = False) -> None:
    """--step download, train or eval. --smoke: 2 training steps on 32 examples, or 2 examples per split."""
    timeouts = {"download": glimmer.DOWNLOAD_TIMEOUT_S, "train": glimmer.TRAIN_TIMEOUT_S,
                "eval": glimmer.EVAL_TIMEOUT_S}
    if step not in timeouts:
        raise SystemExit(f"--step must be one of {', '.join(timeouts)}")
    _gate(glimmer.cost_usd(timeouts[step], gpu=step != "download"))
    clock = time.monotonic()
    try:
        if step == "download":
            print(json.dumps(download.remote()))
        elif step == "train":
            _train(run, smoke)
        else:
            _eval(run, smoke)
    finally:
        _charge(f"{step}-smoke" if smoke else step, run, time.monotonic() - clock)
