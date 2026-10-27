# Gotchas and claim check

Verified 2026-10-26

## 1. Claim check of `MUSE_RESOURCES_PLAN_GRILL_TASTE.md`, Part 1

| Claim in the notes | Status | Evidence |
|---|---|---|
| Base URL `https://api.meta.ai/v1` | CONFIRMED | [overview](https://dev.meta.ai/docs/overview), [quickstart](https://dev.meta.ai/docs/quickstart). Anthropic SDK and Claude Code use `https://api.meta.ai` (no `/v1`): [SDKs](https://dev.meta.ai/docs/sdks) |
| OpenAI and Anthropic SDK compatible | CONFIRMED | [SDKs](https://dev.meta.ai/docs/sdks) (also OpenAI-compatible clients, LiteLLM) |
| `MODEL_API_KEY` env var | CONFIRMED (API calls) | [authentication](https://dev.meta.ai/docs/authentication). Muse Code reads `META_API_KEY` instead: [Muse Code auth](https://dev.meta.ai/docs/muse-code/auth) |
| Key format `LLM\|id\|secret` | CONTRADICTED | Docs say `LLM_{id}_{secret}` with underscores ([authentication](https://dev.meta.ai/docs/authentication), [errors](https://dev.meta.ai/docs/error-handling)). The pipe form is in the cookbook README only ([README](https://github.com/meta-models/meta-model-cookbook)). Treat the key as opaque; never validate its format in code |
| `muse-spark-1.3`, 1M context | CONFIRMED | 1,048,576 tokens ([models](https://dev.meta.ai/docs/models)). Caveat: Muse Code's default is `muse-spark-1.2` ([configuration](https://dev.meta.ai/docs/muse-code/configuration)) |
| "preview is free" | CONTRADICTED by docs | Pricing page lists paid rates ([pricing](https://dev.meta.ai/docs/pricing-rate-limits)); only the cookbook README says "the preview is free". Free-preview terms: Not documented |
| Hosted: Spark, Wonder, Image, Voice Transcribe, SAM 3.1 | CONFIRMED | [models](https://dev.meta.ai/docs/models) |
| Spark Open 816B MoE, 42B active; text, image, audio, video in, text out | CONFIRMED | [overview](https://dev.meta.ai/docs/muse-spark-open) |
| Baseten slug `meta-models/muse-spark-open-1026` | CONFIRMED (hackathon) | The participant guide says: "The docs use meta-models/muse-spark-open. For the hackathon, use meta-models/muse-spark-open-1026 instead." ([Cerebral Valley participant guide](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/details)). The public docs show the plain slug. Use `-1026` and confirm with `GET https://inference.baseten.co/v1/models` |
| Glimmer 30B, Apache 2.0, multimodal, function calling | CONFIRMED | [overview](https://dev.meta.ai/docs/muse-glimmer). Dense (not MoE); text and image in only; 128K context |
| Voice Transcribe: only turn-level timestamps | CONFIRMED | [STT](https://dev.meta.ai/docs/speech-to-text). Also no confidence scores |
| Muse Code `01_append_only_audit_log` to `04_contained_execution` | CONFIRMED | [04_muse_code README](https://github.com/meta-models/meta-model-cookbook/tree/main/04_muse_code) (11 recipes in total) |
| `Muse Code 1.4.13 (1.4.13-R6996.1)` | CONFIRMED | local `muse --version` |
| Fireworks free Glimmer 30B SFT through Nov 30, no card | CONFIRMED | [Fireworks](https://docs.fireworks.ai/fine-tuning/models); LoRA SFT only, deployments and inference not free |
| Voice Transcribe covers Arabic, Spanish, German | CONFIRMED | [STT](https://dev.meta.ai/docs/speech-to-text#language-biasing). Dialect coverage: Not documented |
| $150 Meta API credits | CONFIRMED (hackathon) | $150 per participant, claimed individually by Nov 4 9:00 PM ET. A card on the account is required to make calls. The claim link was "coming soon" on 2026-10-26 ([Cerebral Valley participant guide](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/details)) |
| Prize amounts | CONFIRMED (hackathon) | Indie $400K (150/100/75/50/25K); Startups $550K; bonus: Most Viral $20K, Best Build on Meta Open Weight Models $10K, Community Vote $10K, Best Agentic Use-Case $5K, Best Creative Build $5K ([Cerebral Valley participant guide](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/details)) |
| Spark "Contemplating Mode", visual chain-of-thought, 1,000+ physician health training (LinkedIn) | UNVERIFIED | Not in API docs; the API has `reasoning_effort` up to `max` ([reasoning](https://dev.meta.ai/docs/reasoning)) |
| Design assumes ASR confidence and phonetic candidates | CONTRADICTED | Confidence scores not available ([STT](https://dev.meta.ai/docs/speech-to-text)). Phonetic candidates: Not documented. `keywords` biasing exists |
| Design assumes SAM `polygon_px` | PARTLY | SAM returns box plus raster mask; polygons only via client-library conversion ([client libraries](https://dev.meta.ai/docs/sam/client-libraries)) |
| Glimmer "(Modal)" | CONFIRMED with caveat | Dedicated Endpoint only, not per-token ([Modal](https://modal.com/library/meta/muse-glimmer-30b-bf16)) |

## 2. Wrong-id and endpoint traps

- Spark Open and Glimmer are not on `api.meta.ai`; calling `muse-spark-open` there returns 404 `model_not_found` ([models](https://dev.meta.ai/docs/models), [errors](https://dev.meta.ai/docs/error-handling#404-not-found)).
- Same model, three slugs: `meta-models/muse-spark-open` (Baseten, Together), `accounts/fireworks/models/muse-spark-open` (Fireworks), HF `meta-models/Muse-Spark-Open-816B-A42B[-NVFP4]` ([deploy](https://dev.meta.ai/docs/muse-spark-open/deploy)). Fireworks training uses `...-nvfp4`.
- Glimmer: HF/Together `meta-models/Muse-Glimmer-30B` (capital letters), Fireworks `accounts/fireworks/models/muse-glimmer-30b`, Modal NVFP4 `RadixArk/Muse-Glimmer-NVFP4` (text-only) ([get the model](https://dev.meta.ai/docs/muse-glimmer/get-the-model), [Modal](https://modal.com/library/meta/muse-glimmer-30b-nvfp4)).
- `GET /v1/models` shows what your team can call; Baseten's docs table is JS-rendered, so raw fetches see it empty.
- A 404 on an unknown path has an empty body (no JSON) ([errors](https://dev.meta.ai/docs/error-handling)).

## 3. Unsupported inputs and parameters

- Muse Spark 1.3 audio is degraded: use Voice Transcribe for ASR ([models](https://dev.meta.ai/docs/models#muse-spark)).
- Voice file endpoint takes WAV only (mono, 16-bit PCM, 16 or 24 kHz), at most 10 minutes and 32 MB; convert m4a/mp3 with ffmpeg ([STT](https://dev.meta.ai/docs/speech-to-text)).
- Voice Transcribe has no translation, no word timestamps, no confidence ([STT](https://dev.meta.ai/docs/speech-to-text)).
- SAM: one noun phrase, one concept per request; no OCR; MP4 or MOV only (no WebM); results vary slightly between runs; zero matches is an empty stream, not an error ([segmenting](https://dev.meta.ai/docs/sam/segmenting)).
- `reasoning_effort: "none"` returns 400 on Spark and Wonder; `max` only on `muse-spark-1.3` and `muse-wonder-1.0` ([reasoning](https://dev.meta.ai/docs/reasoning)).
- `tool_choice` accepts only `"auto"`: you cannot force a tool call, so agent loops must handle plain-text replies ([tool calling](https://dev.meta.ai/docs/tool-calling)).
- Tool arguments are not guaranteed to match your schema; validate them. Structured output uses `response_format` on Chat Completions and `text.format` on Responses, not interchangeably; recursive schemas return 400 ([structured output](https://dev.meta.ai/docs/structured-output)).
- `max_output_tokens` minimum 16; reasoning eats the budget, so use 4,000 or more for transcription-like calls; non-streaming calls can 504 ([errors](https://dev.meta.ai/docs/error-handling), [video/audio](https://dev.meta.ai/docs/video-understanding)).
- Spark is tuned for `temperature=1.0`; `temperature=0` is not the intended repeatability mechanism ([Responses](https://dev.meta.ai/docs/protocols/responses)).
- Chat Completions does not carry reasoning between turns; Responses does ([protocols](https://dev.meta.ai/docs/protocols)). Search grounding and tool search exist only on Responses and Messages.
- Baseten Spark Open: no JSON mode or structured outputs, `n=1` only. Fireworks Spark Open: text and images only per Meta's page. Glimmer: no audio or video; structured output Not documented ([Baseten](https://docs.baseten.co/inference/model-apis/overview), [deploy](https://dev.meta.ai/docs/muse-spark-open/deploy#fireworks-ai)).
- Muse Image: do not pass `web_search`; it errors ([image generation](https://dev.meta.ai/docs/image-generation)).
- Self-hosted Spark Open: never stop on `<|eom|>`; default reasoning is `xhigh`, so set it ([settings](https://dev.meta.ai/docs/muse-spark-open/settings)).

## 4. Data and cost traps

- Contributor mode (`*-contributor` model ids, and Muse Code subscriptions by default) lets Meta train on your prompts, files and responses ([pricing](https://dev.meta.ai/docs/pricing-rate-limits#contributor-mode)). Use Standard mode and synthetic data only.
- No hard spend cap; only an email alert. Rate limits are per team, shared by all keys ([spend limit](https://dev.meta.ai/help/billing/spend-limit-alert), [limits](https://dev.meta.ai/docs/pricing-rate-limits)).
- 402 `billing_not_configured` if no payment method; whether hackathon credit changes that is Not documented.
- Modal Dedicated Endpoints and Fireworks on-demand deployments bill while running; Fireworks tuned LoRAs cannot go serverless ([partners.md](partners.md)).
- Hackathon-window deadlines: Fireworks free SFT ends Nov 30, 2026 ([Fireworks](https://docs.fireworks.ai/fine-tuning/models)).
- Availability varies by country; Wonder is unavailable in South Korea ([models](https://dev.meta.ai/docs/models)).

## 5. Doc contradictions and quirks

- Key format: underscore (docs) vs pipe (cookbook README).
- Free preview: cookbook README vs pricing page.
- Muse Code default model is `muse-spark-1.2` while docs call 1.3 "recommended for new work" ([configuration](https://dev.meta.ai/docs/muse-code/configuration), [models](https://dev.meta.ai/docs/models)).
- Install pipe: `| sh` in docs, `| bash` on the landing page ([overview](https://dev.meta.ai/docs/muse-code), [landing](https://dev.meta.ai/lp/muse-code)).
- Glimmer modalities: Meta says text plus image; Modal's BF16 page says "Text" ([overview](https://dev.meta.ai/docs/muse-glimmer), [Modal](https://modal.com/library/meta/muse-glimmer-30b-bf16)).
- Spark Open on Fireworks: "text and images" there vs four modalities on Baseten and Modal ([deploy](https://dev.meta.ai/docs/muse-spark-open/deploy)).

## 6. Still UNVERIFIED (list for the build period)

1. ~~Baseten slug~~: confirmed by the participant guide; check the live `/v1/models` list.
2. $150 Meta credit: amount, scope, expiry; Baseten and Modal hackathon credits.
3. ~~Prize amounts~~: confirmed by the participant guide.
4. Spark structured output combined with image input; Glimmer JSON or schema output.
5. Arabic dialect, medical-term and drug-name accuracy of Voice Transcribe; Spark OCR accuracy on foil blisters; SAM behavior on curved packaging.
6. Spark audio length limits; Spark 1.3 audio quality in practice.
7. Whether Modal's Glimmer endpoint accepts images; Fireworks serverless inference for Glimmer.
8. Meaning of `muse --provider local`; backend of `muse voice transcribe`.
9. Spark 1.3 knowledge cutoff; Spark multilingual coverage statement.
