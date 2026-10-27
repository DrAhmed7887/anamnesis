# Partners: Baseten, Modal, Fireworks

Verified 2026-10-26

Partner credits for the hackathon are NOT described in any public doc I read. The only record is Ahmed's own `credit-requests.md` (requests: Baseten $100 plus 2M TPM, Modal $100), which is a request, not a confirmed grant. Check each dashboard before relying on credit.

## Baseten

- Gives (public): serverless Model APIs per token, OpenAI Chat Completions and Anthropic Messages (beta) compatible; dedicated deployments for other models ([Model APIs](https://docs.baseten.co/inference/model-apis/overview), [quickstart](https://docs.baseten.co/quickstart)). Hackathon credit: Not documented publicly.
- Call Muse Spark Open:

```python
import os
from openai import OpenAI
client = OpenAI(api_key=os.environ["BASETEN_API_KEY"], base_url="https://inference.baseten.co/v1")
r = client.chat.completions.create(model="meta-models/muse-spark-open",
    messages=[{"role": "user", "content": "Explain what a stack trace is in two sentences."}])
```

  Source: [Meta deploy guide](https://dev.meta.ai/docs/muse-spark-open/deploy#baseten). Hackathon slug `meta-models/muse-spark-open-1026` is UNVERIFIED; list slugs with `GET https://inference.baseten.co/v1/models` (needs a key). Price $1.25 in, $0.15 cached, $4.25 out per 1M ([Baseten library](https://www.baseten.co/library/muse-spark-open)).
- Gotchas:
  - Spark Open on Baseten does NOT support structured outputs or JSON mode; tool calling yes. `n>1` returns 400; `logprobs` are ignored; neither `seed` nor `temperature: 0` guarantees reproducibility ([Model APIs](https://docs.baseten.co/inference/model-apis/overview)).
  - Default limits by account tier: Basic unverified 15 RPM / 100K TPM; Basic verified 120 / 500K; Pro 120 / 1M. Ask for a raise (the 2M TPM request) ([pricing and limits](https://docs.baseten.co/inference/model-apis/pricing-and-limits)).
  - 429 means rate limited; 529 means no capacity, retry with backoff even within limits. Headers `x-ratelimit-*`. Reuse an `x-session-affinity` header to improve cache hits ([Model APIs](https://docs.baseten.co/inference/model-apis/overview)).
  - Video: at most 96 frames sampled; send media over about 74 MB by URL ([Meta deploy guide](https://dev.meta.ai/docs/muse-spark-open/deploy#baseten)).
  - Synchronous Model API calls are not stored under Baseten's zero data retention policy ([Model APIs](https://docs.baseten.co/inference/model-apis/overview)). Still use synthetic data only.

## Modal

- Gives (public): serverless GPUs billed per second, $30 per month free compute on signup, GPU use needs a valid payment method on file ([llms.txt](https://modal.com/llms.txt), [intro](https://modal.com/docs/guide/intro)). Hackathon credit: Not documented publicly.
- Endpoints ([endpoints](https://modal.com/docs/guide/endpoints)): **Shared Endpoints** are managed, per token, selected models (Muse Spark Open lives here, $1.25 / $0.15 / $4.25 per 1M: [library](https://modal.com/library/meta/muse-spark-open)). **Dedicated Endpoints** run any library model or your own weights on configurable autoscaling including scale-to-zero, billed on compute. Muse Glimmer is dedicated-only: `modal endpoint create --model meta-models/Muse-Glimmer-30B` ([BF16 page](https://modal.com/library/meta/muse-glimmer-30b-bf16)).
- Calling: OpenAI Chat Completions and Responses, or Anthropic Messages. Auth is a Proxy Token: `modal workspace proxy-tokens create`, then `Authorization: Bearer wk-<id>.ws-<secret>` (usable as an OpenAI API key). Get the `model` value from the dashboard or `GET <endpoint-url>/v1/models`. Optional header `Modal-Routing-Affinity-Key` keeps one conversation on one container ([endpoints](https://modal.com/docs/guide/endpoints)).

```shell
curl "<your-endpoint-url>/v1/chat/completions" \
  -H "Authorization: Bearer $MODAL_PROXY_TOKEN_ID.$MODAL_PROXY_TOKEN_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"model": "<model-name>", "messages": [{ "role": "user", "content": "Hello!" }]}'
```

- Sandboxes: secure containers for untrusted or LLM-generated code. `sb_app = modal.App.lookup("my-app", create_if_missing=True); sb = modal.Sandbox.create(app=sb_app); p = sb.exec("python", "-c", "print('hello')", timeout=3); sb.terminate()` ([sandboxes](https://modal.com/docs/guide/sandboxes)). Fit for isolated eval harness runs; sandbox pricing is on a separate page not read here ([sandbox pricing](https://modal.com/docs/guide/sandbox-resources)).
- Gotchas: setup is `pip install modal` then `modal setup` ([intro](https://modal.com/docs/guide/intro)). Dedicated endpoints cost money while replicas run, so set scale-to-zero and delete them after evals. Modal lists the Glimmer BF16 endpoint's modality as "Text" and NVFP4 as text-only, so test image input before planning around it. Dedicated Endpoint cold-start time and exact price: Not documented in pages read.

## Fireworks

- Gives (public): serverless per-token inference for Muse Spark Open, and training: free LoRA SFT on Muse Glimmer 30B through Nov 30, 2026, no credit card ([models](https://docs.fireworks.ai/fine-tuning/models), [blog](https://fireworks.ai/blog/train-muse-glimmer-for-free)). Hackathon credit: Not documented.
- Call Spark Open: `https://api.fireworks.ai/inference/v1/chat/completions`, `Authorization: Bearer $FIREWORKS_API_KEY`, model `accounts/fireworks/models/muse-spark-open`, `max_tokens` set; JSON mode (`response_format={"type": "json_object"}`) and streaming work; Anthropic-compatible Messages API also exists ([Meta deploy guide](https://dev.meta.ai/docs/muse-spark-open/deploy#fireworks-ai)). Meta's page says it accepts text and images (not audio or video). Prices on the [model page](https://fireworks.ai/models/fireworks/muse-spark-open) (not captured).
- Glimmer fine-tune: base `accounts/fireworks/models/muse-glimmer-30b`; clone `fw-ai/cookbook`, Python 3.11+, `python -m examples.sft.muse_glimmer_starter plan|launch|watch`; surfaces Managed SFT and Serverless Training ([cookbook](https://docs.fireworks.ai/fine-tuning/training-api/cookbook/muse-glimmer)).
- Gotchas:
  - **Fine-tuned models are served only on paid on-demand (dedicated) deployments** billed per GPU-hour; trained LoRAs cannot be served on serverless inference ([fine-tuning models](https://docs.fireworks.ai/fine-tuning/fine-tuning-models), [cookbook](https://docs.fireworks.ai/fine-tuning/training-api/cookbook/muse-glimmer)). The free promotion covers LoRA SFT only, not RL, DPO, full-parameter, deployments or inference, and the starter refuses jobs started after 2026-12-01 PT without `--allow-paid`.
  - Managed SFT reports loss, not task accuracy; low loss on templated answers mostly shows format learning. Evaluate on held-out rows yourself.
  - Deploy command: `firectl deployment create <FINE_TUNED_MODEL_ID> --deployment-shape default` ([fine-tuning models](https://docs.fireworks.ai/fine-tuning/fine-tuning-models)).
  - Spark Open serverless training: LoRA only, rank up to 64, sequences up to 262,144 tokens; if the account lacks access, contact Fireworks ([post-training](https://dev.meta.ai/docs/muse-spark-open/post-training#fireworks-ai)).
