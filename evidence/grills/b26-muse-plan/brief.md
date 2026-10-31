# Batch 26 design: the tuned Glimmer on Modal and Spark Open on Fireworks, as optional steps

You are planning, not building. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, and use no API key;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The plan is done ONLY when your reply has the five sections in §5, and every point cites a file and line you opened in this session.

## 2. What exists
- **The product's claim extractor** is `MetaClaimExtractor` (`anamnesis/providers/claims.py`:387–461). It runs Spark 1.3 on Meta's API with:
  - the system prompt `_SYSTEM_PROMPT`;
  - the transcript lines built at :401;
  - the strict `CLAIMS_SCHEMA`;
  - `parse_claims_json` and the product's checks;
  - one retry.
- **A LoRA adapter, run "r1",** on Meta's open-weight Muse Glimmer 30B was trained and scored on Modal by `finetune/modal_glimmer.py`.
  - **How the eval runs** (`evaluate`, :229, and `_two_passes`, :190): one vLLM 0.32 engine on one H100 holds the adapter, loaded from the Modal volume `anamnesis-glimmer-runs`. It decodes in two passes: free reasoning until the answer header, then an answer constrained to `CLAIMS_SCHEMA`.
  - **The result:** on 303 generated test notes, r1 was fully right on 290, with 0 harmful claims after the product's checks. Spark 1.3 was fully right on 203.
  - **The training prompt** is `chat_row` in `finetune/common.py` (:161). Its system message is `_SYSTEM_PROMPT` plus "\nReasoning strength: low", and its user message is the same transcript lines (`finetune/common.py`:59).
  - **Settings:** `finetune/glimmer.py`.
- **That model runs only inside the eval.** The product never calls it.
- **The open-weight label reader** `OpenWeightLabelReader` (`anamnesis/providers/openweight.py`) reads pack crops with Meta's Muse Spark Open.
  - `scripts/intake_live.py` offers it only as `--reader baseten` (:168), and Baseten is now barred.
  - On Fireworks (`PRESETS["fireworks"]`), strict JSON mode returned no strength on any of 20 crops. With JSON mode off (the schema in the prompt, as for Baseten), it read 5 of 5 crops correctly, at 16–52 s a read.

## 3. What batch 26 should add (the CEO's draft: challenge it)
1. **A deployed Modal class** that serves the r1 adapter:
   - with the eval's own image, engine settings, sampling and `_two_passes`;
   - behind one POST endpoint with `requires_proxy_auth=True`, where clients send `Authorization: Bearer <token id>.<token secret>`;
   - with `scaledown_window` at 10 minutes and no container kept warm;
   - with a warm-up step, because loading took about 200 s in the eval.
2. **`GlimmerClaimExtractor`,** in a new `anamnesis/providers/glimmer.py`, with `MetaClaimExtractor`'s interface. It:
   - sends the trained prompt;
   - runs `parse_claims_json` and every check unchanged;
   - fails safe on a length stop or a missing answer;
   - records a trace whose model is `muse-glimmer-30b+lora-r1@modal`. The trace's cost is estimated from the call's seconds at Modal's H100 list price (`USD_PER_S` in `finetune/glimmer.py`).
3. **`scripts/intake_live.py` gets two flags:**
   - `--extractor glimmer`, with its token read from the macOS Keychain service MODAL_PROXY_TOKEN through the existing `keychain()` (:56);
   - `--reader fireworks`, with JSON mode off.
   - **Without flags, nothing changes:** Spark 1.3 does both steps.
   - **Before any call,** `--extractor glimmer` refuses any voice note but the staged cases' synthetic ones, as `--reader baseten` refuses non-public photos (:175).

## 4. What to check
- **Decoding:** can the served path reproduce the eval's decoding exactly? What differs in a web endpoint from `evaluate`? For instance: one request at a time, request timeouts, how Modal handles a request longer than its web timeout, and the seed.
- **The interface:** what must `GlimmerClaimExtractor` return so that the agent loop, the spend guards and the brief's timeline work unchanged? Name the functions.
- **Failure modes on the live path:** a cold container, a 401, a 5xx, a slow reply against the product's timeouts, a reply with no answer header, a length stop. For each, say what the extractor should do.
- **The token:** where could it leak (errors, reports, the brief, logs)? How does `MetaClient._safe`, or something like it, already guard against that?
- **The draft itself:** anything in it that is wrong, missing or needless. Say so plainly.

## 5. Reply
1. **Verdict on the draft:** one line.
2. **Design:** the Modal class, the provider and the two flags. Give file and function names, signatures, and the request and response shapes.
3. **Risks:** numbered, each with file:line and what to do about it.
4. **Tests the contract should pin:** a list. The CEO writes them; you don't.
5. **Open questions for the CEO.**

Keep it under 900 words.
