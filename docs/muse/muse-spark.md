# Muse Spark (hosted on Meta Model API)

Verified 2026-10-26

Meta's model for agentic and coding work, also a vision-language model ([models](https://dev.meta.ai/docs/models#muse-spark)). Base URL, auth, errors: [meta-model-api.md](meta-model-api.md). Open-weight sibling: [muse-spark-open.md](muse-spark-open.md).

## Model ids

| Id | Notes | Source |
|---|---|---|
| `muse-spark-1.3` | Latest, "recommended for new work", all reasoning levels incl. `max` | [models](https://dev.meta.ai/docs/models) |
| `muse-spark-1.3-contributor` | Cheaper, trains on your data, no `max` | [pricing](https://dev.meta.ai/docs/pricing-rate-limits) |
| `muse-spark-1.2`, `muse-spark-1.2-contributor` | Previous version; the one the docs use for audio examples | [video/audio](https://dev.meta.ai/docs/video-understanding) |
| `muse-spark-1.1` | Original, Standard mode only, not in Muse Code | [models](https://dev.meta.ai/docs/models) |

Wrong-slug trap: the open-weight model is `muse-spark-open` on other hosts and is not callable on Meta API; see [gotchas.md](gotchas.md).

## Capabilities

- Context window: 1,048,576 tokens for every version ([models](https://dev.meta.ai/docs/models)). The docs' agent config sets an output limit of 131,072 ([quickstart](https://dev.meta.ai/docs/quickstart)); no separate hard maximum is stated.
- Inputs: text, image, video, audio, PDF. Output: text only ([models](https://dev.meta.ai/docs/models)).
- Images: URL, base64 data URL, or `file_id`. JPEG, PNG, GIF, WebP, ICO. Up to 50 images and 50 MB per image inline (1 GiB via Files API). Images only in `user` messages ([image understanding](https://dev.meta.ai/docs/image-understanding)).
- Video: MP4 only; embedded audio is read too ([video understanding](https://dev.meta.ai/docs/video-understanding)).
- PDF: text of the first 100 pages and images of the first 50 ([file handling](https://dev.meta.ai/docs/file-handling)).
- Audio: `input_audio` part, MP3 or WAV, on Chat Completions or Responses ([video understanding](https://dev.meta.ai/docs/video-understanding#audio)). **Spark 1.3 audio is "not fully supported" and may be degraded; use Spark 1.2 or Muse Voice Transcribe** ([models](https://dev.meta.ai/docs/models#muse-spark)). So: Spark can take audio directly, but for ASR use [muse-voice-transcribe.md](muse-voice-transcribe.md). Audio length limits: Not documented.
- Grounding: it can return boxes and points as JSON on a normalized 0 to 1000 grid when prompted, for example `[x_min, y_min, x_max, y_max]` ([perception grounding](https://dev.meta.ai/docs/image-understanding)). This is prompted JSON, not pixel masks (use [sam-3-1.md](sam-3-1.md) for masks).
- Reading text in images (OCR, drug names, doses): supported as "extracting information ... pull text, data" ([image understanding](https://dev.meta.ai/docs/image-understanding)). No accuracy figures or per-token confidence are documented.
- Languages for Spark: Not documented on the Spark pages (Spark Open is stated as trained on 100+ languages: [overview](https://dev.meta.ai/docs/muse-spark-open)).

## Reasoning effort

`reasoning_effort` (Chat Completions, top level) or `reasoning.effort` (Responses): `minimal`, `low`, `medium`, `high`, `xhigh`, `max` ([reasoning](https://dev.meta.ai/docs/reasoning)).

- `"none"` is NOT supported and returns HTTP 400. If omitted, the model still reasons at a model-chosen level.
- `max` only on `muse-spark-1.3` (not the contributor variant).
- Reasoning tokens count toward `max_output_tokens` and billed output. Give at least 4,000 output tokens on transcription-like calls or the text can come back empty with `finish_reason: length` ([video/audio tips](https://dev.meta.ai/docs/video-understanding#audio)). `max_output_tokens` minimum is 16 ([Responses](https://dev.meta.ai/docs/protocols/responses)).
- `temperature` and `top_p` are accepted, but the model is tuned for defaults (1.0 and 1.0) ([Responses](https://dev.meta.ai/docs/protocols/responses)). So `temperature=0` is not the intended mode; use schema constraints for repeatability instead.
- Responses API carries reasoning across turns (encrypted replay with `include: ["reasoning.encrypted_content"]`, or `previous_response_id`). Chat Completions does not ([protocols](https://dev.meta.ai/docs/protocols)).
- There is no separate "Contemplating mode" in the API docs; Not documented (the existing notes mention it from a LinkedIn bio).

## Tool calling

Supported on Responses, Chat Completions and Messages ([tool calling](https://dev.meta.ai/docs/tool-calling)).

- `tool_choice` must be `"auto"`. `"none"`, `"required"` and named-function choices return HTTP 400. Your loop must cope with the model answering in text instead of calling a tool.
- Parallel calls on by default; set `parallel_tool_calls: false` to limit to one.
- Arguments stream (`response.function_call_arguments.delta` on Responses).
- `strict` defaults to false and only controls schema validation. Generated arguments are NOT guaranteed to validate; validate them yourself.
- `max_tool_calls` limits built-in tools only (e.g. `web_search`).

## Structured (JSON) output

- Chat Completions: `response_format={"type": "json_schema", "json_schema": {"name": "...", "schema": {...}}}`. Responses: `text.format`. A parameter from the other endpoint does nothing ([structured output](https://dev.meta.ai/docs/structured-output)).
- Decoding is constrained, so output conforms to the schema. Recursive schemas return 400. Limits: nesting depth 10, 5,000 properties total, 120,000 characters of names and enums, 1,000 enum values.
- JSON mode (valid JSON only, no schema) also exists ([Responses schemas](https://dev.meta.ai/docs/api-reference/responses/schemas)).
- Structured output together with image input: the vision cookbook describes "structured analysis" from images ([README](https://github.com/meta-models/meta-model-cookbook)); an explicit statement that the two combine is Not documented in the guide pages. Test it early.

## Streaming

`stream: true` on all three protocols. Non-streaming requests have a server time limit and return 504 `gateway_timeout`; stream long or high-effort calls ([errors](https://dev.meta.ai/docs/error-handling#504)).

## Other documented features

Search grounding (Responses and Messages only), prompt caching, token counting (`POST /v1/responses/input_tokens`), tool search, background responses ([protocols](https://dev.meta.ai/docs/protocols), [pricing](https://dev.meta.ai/docs/pricing-rate-limits)).

## Known limits and traps

See [gotchas.md](gotchas.md). Highlights: audio on 1.3, `reasoning_effort: "none"`, `tool_choice`, Contributor mode trains on your data, no Muse Spark knowledge-cutoff date documented.
