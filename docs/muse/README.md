# Meta Muse models and tools: reference for coding agents

Verified 2026-10-26

Audience: Claude Code, Codex, Muse Code. Read this folder before touching Anamnesis code. RESEARCH ONLY: the hackathon build period had not started when these were written (hackathon begins Oct 26 per [event page](https://dev.meta.ai/events/global-hackathon)).

Rules for every file here: every fact has a source link; "Not documented" means the official docs say nothing; no secrets are stored anywhere.

## Files

| File | Read it when |
|---|---|
| [meta-model-api.md](meta-model-api.md) | Calling any hosted model: base URL, auth, endpoints, limits, pricing, errors |
| [muse-spark.md](muse-spark.md) | Calling Muse Spark (vision, tools, JSON, reasoning) |
| [muse-voice-transcribe.md](muse-voice-transcribe.md) | Speech to text (Arabic, Spanish, German) |
| [sam-3-1.md](sam-3-1.md) | Cutting pill packs out of photos (geometry only) |
| [muse-spark-open.md](muse-spark-open.md) | Open-weight 816B model on Baseten, Modal, Fireworks |
| [muse-glimmer.md](muse-glimmer.md) | Open-weight 30B model, fine-tuning |
| [muse-image-and-wonder.md](muse-image-and-wonder.md) | Muse Image and Muse Wonder (not planned for Anamnesis) |
| [muse-code.md](muse-code.md) | The `muse` CLI, headless use, skills, cookbook recipes |
| [partners.md](partners.md) | Baseten, Modal, Fireworks specifics |
| [gotchas.md](gotchas.md) | Traps, doc contradictions, and the claim check of the existing notes |

## Overview table

"Role in Anamnesis" is the role proposed in `MUSE_RESOURCES_PLAN_GRILL_TASTE.md`, not a Meta statement.

| Model or tool | What it does | Inputs -> outputs | Where to call it | Model id or slug | Cost and credits | Role in Anamnesis |
|---|---|---|---|---|---|---|
| Muse Spark 1.3 | Agentic multimodal reasoning model | text, image, video, audio, PDF -> text ([models](https://dev.meta.ai/docs/models)) | Meta Model API only | `muse-spark-1.3` (also `-1.2`, `-1.1`, `-1.3-contributor`, `-1.2-contributor`) | $1.25 in / $0.15 cached / $4.25 out per 1M tokens; Contributor $0.10 / $0.002 / $0.20 ([pricing](https://dev.meta.ai/docs/pricing-rate-limits)) | Hosted baseline: extraction, checking. Audio on 1.3 is degraded |
| Muse Voice Transcribe | Streaming and file speech to text, diarization | audio -> transcript text, turn-level timestamps ([STT](https://dev.meta.ai/docs/speech-to-text)) | Meta Model API (`/v1/asr/transcribe`, `wss://api.meta.ai/v1/asr/realtime`) | `muse-voice-transcribe-1.0` | $0.18 per audio hour ([pricing](https://dev.meta.ai/docs/pricing-rate-limits)) | ASR for AR/ES/DE patient voice notes |
| SAM 3.1 | Detect, segment, track objects | text noun phrase or box/point prompts + image/video -> boxes and masks (geometry, not text) ([models](https://dev.meta.ai/docs/models)) | Meta Model API (`POST /v1/responses`) | `sam-3.1` | $2.50 per 1,000 images; $0.20 per 1,000 video frames | Crop pill packs and labels |
| Muse Spark Open | Open-weight 816B MoE (42B active) | text, image, video, audio -> text ([overview](https://dev.meta.ai/docs/muse-spark-open)) | Baseten, Modal, Fireworks, Together, Groq, Nebius, OpenRouter, self-host (NOT Meta API) | `meta-models/muse-spark-open` on Baseten and Together; `accounts/fireworks/models/muse-spark-open` on Fireworks; hackathon slug `meta-models/muse-spark-open-1026` UNVERIFIED | $1.25 / $0.15 / $4.25 per 1M on Baseten and Modal ([Baseten](https://www.baseten.co/library/muse-spark-open), [Modal](https://modal.com/library/meta/muse-spark-open)); hackathon partner credits per `credit-requests.md` (not in public docs) | Open-weight comparison arm |
| Muse Glimmer | Open-weight 30B dense, local agents | text, image -> text ([overview](https://dev.meta.ai/docs/muse-glimmer)) | Modal Dedicated Endpoint, Together serverless, Fireworks (fine-tune), local | `meta-models/Muse-Glimmer-30B`; Fireworks `accounts/fireworks/models/muse-glimmer-30b` | Together $0.35 in / $1.50 out per 1M; Fireworks LoRA SFT free to Nov 30 ([docs](https://docs.fireworks.ai/fine-tuning/training-api/cookbook/muse-glimmer)) | Open-weight comparison arm, fine-tune candidate |
| Muse Image | Image generation and editing | text, image -> image | Meta Model API | `muse-image-1.0` | $0.01 per image | Not used (plan dropped synthetic pill images) |
| Muse Wonder | Top Meta model, coding, computer use (preview) | text, image, video, audio, PDF -> text | Meta Model API; Wonder Full only in Muse Code subscription | `muse-wonder-1.0` | $4 in / $0.20 cached / $20 out per 1M | Not planned |
| Muse Code | Terminal and CI coding agent | prompt -> edits, commands | Local CLI `~/.local/bin/muse` (installed, v1.4.13) | default model `muse-spark-1.2` | Pay-as-you-go or $5 to $200 per month plans ([landing](https://dev.meta.ai/lp/muse-code)) | Build tool |

## Credits

The "$150 hackathon API credits" are NOT documented on any public Meta page I could read ([pricing](https://dev.meta.ai/docs/pricing-rate-limits), [event page](https://dev.meta.ai/events/global-hackathon), [billing help](https://dev.meta.ai/help/billing/api-bill)). Arithmetic only: $150 buys about 120M Spark 1.3 input tokens, or about 35M output tokens, or about 833 hours of transcription, or 60,000 SAM images.

## Source priority used

1. dev.meta.ai docs (raw Markdown at `https://dev.meta.ai/docs/<page>.md` and `https://dev.meta.ai/llms.txt`, no login needed) and model pages.
2. Cookbooks: [meta-model-cookbook](https://github.com/meta-models/meta-model-cookbook), [meta-oss-cookbook](https://github.com/meta-models/meta-oss-cookbook).
3. Local `muse --help` output (read-only; no login performed).
4. Partner docs: [Baseten](https://docs.baseten.co), [Modal](https://modal.com/docs/guide/intro), [Fireworks](https://docs.fireworks.ai/fine-tuning/fine-tuning-models).
