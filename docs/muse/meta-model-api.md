# Meta Model API

Verified 2026-10-26

Hosted API for Muse Spark, Muse Wonder, Muse Image, Muse Voice Transcribe and SAM 3.1. Muse Spark Open and Muse Glimmer are NOT served here ([models](https://dev.meta.ai/docs/models)).

## Base URL and auth

- OpenAI-style base URL: `https://api.meta.ai/v1` ([quickstart](https://dev.meta.ai/docs/quickstart)).
- Anthropic-style base URL (Anthropic SDK, Claude Code): `https://api.meta.ai` with no `/v1`; the SDK appends `/v1/messages`; pass the key as `auth_token` ([SDKs](https://dev.meta.ai/docs/sdks)).
- Auth: `Authorization: Bearer $MODEL_API_KEY`. Create keys in the dashboard at https://dev.meta.ai/ under API keys; the key is shown once ([authentication](https://dev.meta.ai/docs/authentication)).
- Key format per docs: `LLM_{id}_{secret}` with underscores ([authentication](https://dev.meta.ai/docs/authentication), [errors](https://dev.meta.ai/docs/error-handling)). The cookbook README shows `LLM|{numeric_id}|{secret}` with pipes ([README](https://github.com/meta-models/meta-model-cookbook)). Treat the key as an opaque string.
- No SDK reads `MODEL_API_KEY` by itself. Pass it explicitly or set `OPENAI_API_KEY` ([SDKs](https://dev.meta.ai/docs/sdks#authentication)).
- Muse Code uses a different variable, `META_API_KEY` ([Muse Code auth](https://dev.meta.ai/docs/muse-code/auth)).
- Never write a key into a file in this repo.

## SDK compatibility

OpenAI SDK (Responses and Chat Completions), Anthropic SDK (Messages), and OpenAI-compatible clients (LangChain, LlamaIndex, Vercel AI SDK, LiteLLM with `openai/` model prefix) ([SDKs](https://dev.meta.ai/docs/sdks)). Three request formats run the same models at the same price; Responses is the default for agents because it carries reasoning across turns ([protocols](https://dev.meta.ai/docs/protocols)).

Minimal Python, from [quickstart](https://dev.meta.ai/docs/quickstart):

```python
import os
from openai import OpenAI
client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.environ["MODEL_API_KEY"])
response = client.responses.create(model="muse-spark-1.3", input="What is the capital of France?")
print(response.output_text)
```

Minimal curl, from [authentication](https://dev.meta.ai/docs/authentication):

```shell
curl https://api.meta.ai/v1/chat/completions \
  -H "Authorization: Bearer $MODEL_API_KEY" -H "Content-Type: application/json" \
  -d '{"model": "muse-spark-1.3", "messages": [{"role": "user", "content": "Hello"}]}'
```

Anthropic SDK, from [SDKs](https://dev.meta.ai/docs/sdks): `Anthropic(base_url="https://api.meta.ai", auth_token=os.environ["MODEL_API_KEY"])`. The first content block is `redacted_thinking`, so read the `text` blocks, not `content[0]`.

## Endpoints

| Endpoint | Used for | Source |
|---|---|---|
| `POST /v1/responses` (+ retrieve, cancel, delete, `/v1/responses/input_tokens`) | Spark, Wonder, Image, SAM 3.1 | [protocols](https://dev.meta.ai/docs/protocols/responses), [API ref](https://dev.meta.ai/docs/api-reference) |
| `POST /v1/chat/completions` | Spark, Wonder | [protocols](https://dev.meta.ai/docs/protocols/chat-completions) |
| `POST /v1/messages` (+ count tokens) | Anthropic-format clients | [protocols](https://dev.meta.ai/docs/protocols/messages) |
| `POST /v1/files`, list, retrieve, content, delete | Upload media once, reference by `file_id` | [files](https://dev.meta.ai/docs/file-handling) |
| `POST /v1/images/generations`, `/v1/images/edits` | Muse Image | [image generation](https://dev.meta.ai/docs/image-generation) |
| `GET /v1/models`, `GET /v1/models/{model}` | List what your team can call | [models](https://dev.meta.ai/docs/models) |
| `POST /v1/asr/transcribe`, `wss://api.meta.ai/v1/asr/realtime` | Muse Voice Transcribe | [STT](https://dev.meta.ai/docs/speech-to-text) |

Files: 50 MB inline limit, 1 GiB via the Files API, 100 GiB team storage; MP4 video, MP3 and WAV audio, PDF, images ([file handling](https://dev.meta.ai/docs/file-handling)).

## Rate limits (per team, not per key)

| Model | RPM | TPM | Source |
|---|---|---|---|
| `muse-spark-1.3`, `-1.2`, `-1.1`, `muse-wonder-1.0` | 3,000 | 4,000,000 | [limits](https://dev.meta.ai/docs/pricing-rate-limits#rate-limits) |
| `muse-spark-1.3-contributor`, `-1.2-contributor` | 150 | 3,000,000 | same |
| `sam-3.1` | 3,000 | none | same |
| `muse-image-1.0` | 150 | none | same |
| `muse-voice-transcribe-1.0` | none | none; 256 concurrent streams, 16,000 streams per hour | same |

Background responses: 600 submissions per minute per team. On 429 use exponential backoff with jitter (start about 500 ms) and honor `Retry-After`. Headers: `x-ratelimit-{limit,remaining}-{tokens,requests}`; transcription responses do not carry them ([limits](https://dev.meta.ai/docs/pricing-rate-limits)).

## Pricing and "free preview"

- Pay-as-you-go, per token / image / frame / audio hour, no minimums ([pricing](https://dev.meta.ai/docs/pricing-rate-limits)). Figures are in [README.md](README.md).
- Search grounding (`web_search` tool): $2.50 per 1,000 queries on top of tokens. No long-context premium. Cached input is cheaper ([pricing](https://dev.meta.ai/docs/pricing-rate-limits)).
- Contributor mode (model id suffix `-contributor`) is cheaper but lets Meta train on your prompts, files and responses. Do not use it for anything patient-like ([pricing](https://dev.meta.ai/docs/pricing-rate-limits#contributor-mode)).
- Free preview: the cookbook README says "the preview is free" for Muse Spark ([README](https://github.com/meta-models/meta-model-cookbook)). The pricing docs list paid rates and call only Muse Wonder "in preview" ([models](https://dev.meta.ai/docs/models)). No free-preview terms are documented. Assume billable.
- Billing needs a payment method: without it you get `402 billing_not_configured` ([errors](https://dev.meta.ai/docs/error-handling#402-payment-required), [setup](https://dev.meta.ai/help/billing/set-up-billing)).
- No hard spend cap exists, only an email alert ([spend limit](https://dev.meta.ai/help/billing/spend-limit-alert)).

## Hackathon $150 credits

Not documented. No public page describes the $150 credit, how it is applied, or whether it bypasses the payment-method requirement. After claiming, check the dashboard Billing and Usage pages (https://dev.meta.ai/billing, https://dev.meta.ai/usage, both linked from [Muse Code auth](https://dev.meta.ai/docs/muse-code/auth)) before running batch evals.

## Error codes ([error handling](https://dev.meta.ai/docs/error-handling))

Body: `{"error": {"message", "type", "param", "code"}}`. Unknown paths give 404 with an empty body.

| HTTP | type / code | Meaning and action |
|---|---|---|
| 400 | `invalid_request_error`; `content_policy_violation`, `payload_too_large` | Bad parameter (e.g. `reasoning_effort: "none"`, `max_output_tokens` under 16, over 50 images). Do not retry unchanged |
| 401 | `authentication_error` / `invalid_api_key` | Missing or bad key |
| 402 | `billing_error` / `billing_not_configured` | Add payment method |
| 403 | | Key or team lacks access to model or feature |
| 404 | `model_not_found`, `file_not_found` | Wrong model id (check against `GET /v1/models`) |
| 413 | `payload_too_large` | Background body over 1 MiB, or `store=true` with huge inline base64: use Files API or `store=false` |
| 429 | `rate_limit_error` / `rate_limit_exceeded` | Back off, honor `Retry-After` |
| 500 | `server_error` | Retry with backoff (includes malformed model output) |
| 503 | `server_shutting_down`, `service_overloaded`, `backend_unavailable` | Always retryable, honor `Retry-After` (60 s for overload) |
| 504 | `gateway_timeout` | Non-stream request ran too long: use `stream: true` or `background: true` |

## Not documented

Hackathon credit mechanics; guaranteed region or data-residency options; the Spark 1.3 knowledge cutoff (the help page defers to the Models page, which lists none) ([help](https://dev.meta.ai/help/about-model-api/knowledge-cutoff)).
