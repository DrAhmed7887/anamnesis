# Muse Spark Open

Verified 2026-10-26

Open-weight release of Muse Spark: 816B-parameter sparse mixture-of-experts, 42B active per token. NOT served on Meta Model API; run it yourself or call a hosted provider ([models](https://dev.meta.ai/docs/models#muse-spark-open), [overview](https://dev.meta.ai/docs/muse-spark-open)). Released Oct 15, 2026 per [Modal](https://modal.com/blog/meta-muse-spark-open-now-available-on-modal).

## Facts

| Item | Value | Source |
|---|---|---|
| Size | 816B total, 42B active, sparse MoE with built-in perception encoders | [overview](https://dev.meta.ai/docs/muse-spark-open) |
| Inputs / output | text, image, video, audio in; text out | same |
| Context | 1,048,576 tokens | same |
| Languages | trained on 100+ languages; per-language quality Not documented | same |
| Licence | Muse Model License plus Acceptable Use Policy. NOT Apache 2.0 | [overview](https://dev.meta.ai/docs/muse-spark-open), [LICENSE](https://huggingface.co/meta-models/Muse-Spark-Open-816B-A42B/blob/main/LICENSE.md) |
| Weights | BF16 about 1.65 TB (`meta-models/Muse-Spark-Open-816B-A42B`); NVFP4 about 537 GB (`meta-models/Muse-Spark-Open-816B-A42B-NVFP4`); GGUF `ggml-org/Muse-Spark-Open-816B-A42B-GGUF` | [get the model](https://dev.meta.ai/docs/muse-spark-open/get-the-model), [deploy](https://dev.meta.ai/docs/muse-spark-open/deploy) |
| Self-host hardware | BF16 on 8 x B300 (about 2 TB VRAM); NVFP4 on 4 x B300. Not realistic on a laptop | [overview](https://dev.meta.ai/docs/muse-spark-open), [settings](https://dev.meta.ai/docs/muse-spark-open/settings) |
| Runtimes | SGLang, vLLM, TensorRT-LLM, Dynamo, Transformers, llama.cpp, Unsloth GGUF, MLX | [deploy](https://dev.meta.ai/docs/muse-spark-open/deploy) |

## Where to run it and exact ids

| Where | Model string | Base URL | Notes | Source |
|---|---|---|---|---|
| Baseten Model APIs | `meta-models/muse-spark-open` | `https://inference.baseten.co/v1` | Serverless per token (also Dedicated). Text, image, video, audio. NO structured outputs and NO JSON mode; tool calling yes; `n>1` returns 400; logprobs ignored | [deploy](https://dev.meta.ai/docs/muse-spark-open/deploy#baseten), [Baseten Model APIs](https://docs.baseten.co/inference/model-apis/overview) |
| Modal | Shared Endpoint (per token, NVFP4); model name is shown in the dashboard or `GET <endpoint>/v1/models` | endpoint URL, Proxy Token required | $1.25 / $0.15 / $4.25 per 1M | [Modal library](https://modal.com/library/meta/muse-spark-open), [Modal endpoints](https://modal.com/docs/guide/endpoints) |
| Fireworks | `accounts/fireworks/models/muse-spark-open` | `https://api.fireworks.ai/inference/v1` | Serverless per token; Meta's page says text and images in, tool calling, `reasoning_effort`, JSON mode works | [deploy](https://dev.meta.ai/docs/muse-spark-open/deploy#fireworks-ai) |
| Together AI | `meta-models/muse-spark-open` | `https://api.together.xyz/v1` | | [deploy](https://dev.meta.ai/docs/muse-spark-open/deploy#hosted-providers) |
| Groq, Nebius, OpenRouter | see provider tabs | | Groq needs org approval | [deploy](https://dev.meta.ai/docs/muse-spark-open/deploy#hosted-providers) |

**Hackathon Baseten slug `meta-models/muse-spark-open-1026`: UNVERIFIED.** It appears in neither the Meta docs (which say `meta-models/muse-spark-open`), the [Baseten library page](https://www.baseten.co/library/muse-spark-open), nor the [Baseten Model APIs page](https://docs.baseten.co/inference/model-apis/overview) (its model table is JS-rendered and empty in raw fetches). Confirm with `GET https://inference.baseten.co/v1/models` using your Baseten key, then use whichever slug is listed.

## Capabilities and settings

- Reasoning: `reasoning_effort` `low` (8), `medium` (32), `high` (256), `xhigh` (512, DEFAULT). It reasons long by default, so set it explicitly and stream (`stream: true`) ([settings](https://dev.meta.ai/docs/muse-spark-open/settings)).
- Sampling: recommended `temperature 1.0`, `top_p 1.0`. Never stop on `<|eom|>`; stop on `<|eot|>` ([settings](https://dev.meta.ai/docs/muse-spark-open/settings)).
- Tool calling: via the chat template and a tool-call parser (`--tool-call-parser muse` on SGLang/vLLM); hosted providers expose OpenAI-style `tools` ([deploy](https://dev.meta.ai/docs/muse-spark-open/deploy), [prompting](https://dev.meta.ai/docs/muse-spark-open/prompting)).
- Structured output: Fireworks says JSON mode works; Baseten says it does NOT. Schema-constrained decoding on any host: Not documented. Validate with Pydantic and retry ([Baseten](https://docs.baseten.co/inference/model-apis/overview)).
- Media on Baseten: media over about 74 MB should go by URL; video by URL up to 200 MB; the video encoder samples at most 96 frames per clip (about 144 tokens per second at 720p, capped near 6.9K tokens) ([deploy](https://dev.meta.ai/docs/muse-spark-open/deploy#baseten)). Audio length and format limits: Not documented.
- Audio inputs use `audio_url` content parts on OpenAI-compatible hosts ([deploy](https://dev.meta.ai/docs/muse-spark-open/deploy#baseten)). Whether hosted providers accept every audio format: Not documented.

## Fine-tuning

Options listed by Meta ([post-training](https://dev.meta.ai/docs/muse-spark-open/post-training)): TorchTitan (SFT LoRA or full, RL), Miles (GRPO, 64 GPUs), NVIDIA NeMo AutoModel, Megatron Bridge, TRL (SFT LoRA), Together AI (SFT, RL), Fireworks AI (serverless LoRA: SFT, DPO, ORPO, distillation, RL; full-parameter on dedicated GPUs). Fireworks base model for training: `accounts/fireworks/models/muse-spark-open-nvfp4`, LoRA rank up to 64, sequences up to 262,144 tokens; if the account lacks access, contact Fireworks. The free-SFT promotion is for Muse Glimmer, not Spark Open ([Fireworks](https://docs.fireworks.ai/fine-tuning/fine-tuning-models)). Spark Open training price: Not documented in the pages read.

## Related

[partners.md](partners.md), [muse-glimmer.md](muse-glimmer.md), [gotchas.md](gotchas.md). Cookbook: [meta-oss-cookbook/muse-spark](https://github.com/meta-models/meta-oss-cookbook/tree/main/muse-spark).
