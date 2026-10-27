# Muse Glimmer

Verified 2026-10-26

Meta's 30B open-weight model, distilled from Muse Spark, for local and edge agents. Not served on Meta Model API ([models](https://dev.meta.ai/docs/models#muse-glimmer)).

## Facts

| Item | Value | Source |
|---|---|---|
| Size | 30B parameters, DENSE (not MoE), 52 layers | [overview](https://dev.meta.ai/docs/muse-glimmer), [Modal](https://modal.com/library/meta/muse-glimmer-30b-bf16) |
| Inputs / output | text and image in; text out. Images: YES | [overview](https://dev.meta.ai/docs/muse-glimmer), [prompting](https://dev.meta.ai/docs/muse-glimmer/prompting#multimodal-input) |
| Audio / video input | No (not listed). Audio, video: Not documented as supported | [overview](https://dev.meta.ai/docs/muse-glimmer) |
| Context | 128K tokens by default (131,072); longer supported | [overview](https://dev.meta.ai/docs/muse-glimmer) |
| Licence | Apache 2.0 | [overview](https://dev.meta.ai/docs/muse-glimmer) |
| Languages | trained on 100+ languages; per-language quality Not documented | [Modal](https://modal.com/library/meta/muse-glimmer-30b-bf16) |
| Reasoning | `low`, `medium`, `high`, `xhigh`; long chain-of-thought by default, so stream and leave `max_tokens` headroom | [deploy](https://dev.meta.ai/docs/muse-glimmer/deploy), [Modal](https://modal.com/library/meta/muse-glimmer-30b-bf16) |
| Tool calling | Yes, parsed by the server into OpenAI-style `tool_calls` (vLLM `--tool-call-parser muse_glimmer --enable-auto-tool-choice`) | [prompting](https://dev.meta.ai/docs/muse-glimmer/prompting#tool-calling), [deploy](https://dev.meta.ai/docs/muse-glimmer/deploy) |
| Structured / JSON output | Not documented in Meta's Glimmer pages | |
| Released | Aug 2026 (Together lists Aug 10, 2026) | [deploy](https://dev.meta.ai/docs/muse-glimmer/deploy#hosted-providers) |

## Weights (Hugging Face)

[`meta-models/Muse-Glimmer-30B`](https://huggingface.co/meta-models/Muse-Glimmer-30B) (bf16, about 60 GB, needs about 72 GB VRAM), [`-GGUF`](https://huggingface.co/meta-models/Muse-Glimmer-30B-GGUF) (Q4_K_M about 17 GB fits under 24 GB VRAM; `mmproj` file about 1.4 GB is required for image input), `-assistant` (draft model), `-ExecuTorch-PTE`. Needs `transformers` 5.15 or later ([get the model](https://dev.meta.ai/docs/muse-glimmer/get-the-model)). Use `AutoProcessor`, not the bare tokenizer, for images ([prompting](https://dev.meta.ai/docs/muse-glimmer/prompting)).

## Where to run it

| Where | How | Notes | Source |
|---|---|---|---|
| Modal | Dedicated Endpoint: `modal endpoint create --model meta-models/Muse-Glimmer-30B` | Billed per second of compute while running; not a per-token Shared Endpoint. Modal's spec lists modality "Text" for the BF16 build and the NVFP4 build (`RadixArk/Muse-Glimmer-NVFP4`) is text-only (no vision tower). VERIFY image input on a Modal endpoint before relying on it | [Modal BF16](https://modal.com/library/meta/muse-glimmer-30b-bf16), [Modal NVFP4](https://modal.com/library/meta/muse-glimmer-30b-nvfp4), [endpoints](https://modal.com/docs/guide/endpoints) |
| Together AI | Serverless, model `meta-models/Muse-Glimmer-30B`, `https://api.together.xyz/v1` | $0.35 / $0.04 cached / $1.50 per 1M; text and image in; the only hosted provider Meta's Glimmer page lists | [deploy](https://dev.meta.ai/docs/muse-glimmer/deploy#hosted-providers) |
| Fireworks | Base model id `accounts/fireworks/models/muse-glimmer-30b` for fine-tuning; whether serverless inference exists for it: Not documented | See fine-tuning | [Fireworks cookbook](https://docs.fireworks.ai/fine-tuning/training-api/cookbook/muse-glimmer) |
| Local | vLLM, SGLang, llama.cpp, ExecuTorch, Ollama, LM Studio, Unsloth | A 30B Q4 GGUF is the laptop option | [deploy](https://dev.meta.ai/docs/muse-glimmer/deploy) |

## Fine-tuning

- Fireworks: Muse Glimmer 30B LoRA SFT is free through Nov 30, 2026, no credit card, via the UI, Managed SFT or Serverless Training API. The starter script refuses to launch after 2026-12-01 (PT) without `--allow-paid`. Not covered by the promotion: RL, DPO, full-parameter training, deployments, and inference ([Fireworks cookbook](https://docs.fireworks.ai/fine-tuning/training-api/cookbook/muse-glimmer), [blog](https://fireworks.ai/blog/train-muse-glimmer-for-free), [models](https://docs.fireworks.ai/fine-tuning/models)). Tokenizer `meta-models/Muse-Glimmer-30B`, renderer `muse_glimmer`, default LoRA rank 8. Vision SFT works (receipt example) with `--max-context-length 8192`.
- Serving a tuned model on Fireworks: trained LoRAs cannot be served on serverless inference; they need an on-demand (dedicated) deployment billed per GPU-hour ([Fireworks cookbook](https://docs.fireworks.ai/fine-tuning/training-api/cookbook/muse-glimmer), [fine-tuning models](https://docs.fireworks.ai/fine-tuning/fine-tuning-models)). Budget for that.
- Self-managed on your own GPUs: Axolotl (QLoRA, bf16 LoRA, full FSDP2), TRL (LoRA, QLoRA, DPO, GRPO), TitanRL (GRPO). QLoRA also runs on 1 x H100 ([post-training](https://dev.meta.ai/docs/muse-glimmer/post-training)). Meta says start with SFT.
- Modal accepts fine-tuned weights on Dedicated Endpoints ("Bring fine-tuned weights") ([Modal BF16](https://modal.com/library/meta/muse-glimmer-30b-bf16)); a step-by-step recipe: Not documented.

## Related

[partners.md](partners.md), [muse-spark-open.md](muse-spark-open.md), [gotchas.md](gotchas.md). Cookbooks: [meta-oss-cookbook/muse-glimmer](https://github.com/meta-models/meta-oss-cookbook/tree/main/muse-glimmer); hybrid local-plus-Spark agent recipe [glimmer-api-agent](https://dev.meta.ai/docs/cookbook/glimmer-api-agent) (uses Hermes, Glimmer locally, `consult_remote_model` to Spark with an approval gate).
