# Muse Image and Muse Wonder

Verified 2026-10-26

Short note. Neither is in the Anamnesis plan: the plan dropped synthetic pill-pack images because generators garble small print (`MUSE_RESOURCES_PLAN_GRILL_TASTE.md`, Part 2).

## Muse Image (`muse-image-1.0`)

- What: one agentic model for image generation and editing. Input text and optional reference images; output an image ([models](https://dev.meta.ai/docs/models#muse-image), [image generation](https://dev.meta.ai/docs/image-generation)).
- Endpoints: Responses API (multi-turn editing) or `POST /v1/images/generations` and `/v1/images/edits` (OpenAI Images API compatible) ([image generation](https://dev.meta.ai/docs/image-generation)).
- It searches the web and runs code on its own before rendering; passing a `web_search` tool returns an error ([image generation](https://dev.meta.ai/docs/image-generation)).
- Price: $0.01 per generated image, search included; images removed by safety filtering are not billed. Rate limit 150 RPM, no TPM ([pricing](https://dev.meta.ai/docs/pricing-rate-limits)).
- Transient failures return 503 `server_error`; retry ([errors](https://dev.meta.ai/docs/error-handling#503)).
- Text-in-image accuracy for dose strings: Not documented.
- Cookbook: [05_muse_image](https://github.com/meta-models/meta-model-cookbook/tree/main/05_muse_image).

## Muse Wonder (`muse-wonder-1.0`, preview)

- What: Meta's most capable model for long software tasks, sub-agent orchestration and computer use. Same endpoints and request shapes as Muse Spark; switching is a model-id change ([models](https://dev.meta.ai/docs/models#muse-wonder)).
- Inputs text, image, video, audio, PDF; output text; 1,048,576 context; reasoning `minimal` to `max`; computer-use tool ([models](https://dev.meta.ai/docs/models), [computer use](https://dev.meta.ai/docs/computer-use)).
- Price: $4.00 in, $0.20 cached, $20.00 out per 1M tokens; no Contributor mode on pay-as-you-go; limits 3,000 RPM and 4,000,000 TPM ([pricing](https://dev.meta.ai/docs/pricing-rate-limits)).
- Muse Wonder Full is Muse Code subscription only (Power or Maximum plan), not on Model API. Wonder is not available in South Korea ([models](https://dev.meta.ai/docs/models#muse-wonder-availability)).
- It is 3.2x Spark's input price and about 4.7x its output price, so use it only if Spark fails on a task. Whether Wonder beats Spark on medication-label reading: Not documented.
