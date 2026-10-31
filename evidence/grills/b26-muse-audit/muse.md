muse: workspace root: <repo>/.muse/worktrees/20261030-be39 (cwd default)
muse: warning: rules file at <repo>/CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
## 1. Verdict

Sound build: served engine/decoding match the eval, charging and guards fail closed; six findings, all low/medium, none blocking.

## 2. Findings

1. **Medium — server accepts any schema/max_tokens, so served decoding can diverge from the eval's.** The server passes the client-supplied `schema` to `StructuredOutputsParams` and client `max_tokens` (1–16000) to `_two_passes` (`finetune/modal_serve.py`, provided copy, `extract` handler), while the eval pins the product's `CLAIMS_SCHEMA` ([modal_glimmer.py](<repo>/.muse/worktrees/20261030-be39/finetune/modal_glimmer.py:288)) and `MAX_TOKENS=16000` ([modal_glimmer.py](<repo>/.muse/worktrees/20261030-be39/finetune/modal_glimmer.py:339), [glimmer.py](<repo>/.muse/worktrees/20261030-be39/finetune/glimmer.py:36)). Today's client sends the same values (pinned by [test_b26_open_weight_path.py](<repo>/.muse/worktrees/20261030-be39/tests/contract/test_b26_open_weight_path.py:61)), but any proxy-token holder can request otherwise. Fix: server-side, accept only `schema == CLAIMS_SCHEMA` (400 otherwise) and fix `max_tokens=16000`.

2. **Low — malformed-JSON bodies likely 500, and the client then bills two full-timeout estimates for a request the server never ran.** `extract` has no guard around `await request.json()` (provided `modal_serve.py`); the client treats 5xx as retryable + uncertain, charging 2× estimate ([test_b26_open_weight_path.py](<repo>/.muse/worktrees/20261030-be39/tests/contract/test_b26_open_weight_path.py:140), [base.py](<repo>/.muse/worktrees/20261030-be39/anamnesis/providers/base.py:64)). Same for over-long prompts that die inside vLLM. Fix: `try/except` → 400 `{"error":...}`; optionally pre-reject prompts over `MAX_MODEL_LEN` ([glimmer.py](<repo>/.muse/worktrees/20261030-be39/finetune/glimmer.py:37)).

3. **Low — unknown finish reasons fail open.** The client only special-cases `"length"` (diff `glimmer.py`, `attempt()`); `_two_passes` passes vLLM's `finish_reason` through verbatim ([modal_glimmer.py](<repo>/.muse/worktrees/20261030-be39/finetune/modal_glimmer.py:206)), and the contract pins only stop/length/None ([test_b26_open_weight_path.py](<repo>/.muse/worktrees/20261030-be39/tests/contract/test_b26_open_weight_path.py:103)). An `"abort"`/`"error"` first pass with an opened answer would be parsed as a clean reply. Fix: allowlist finishes (`stop`, plus today's None-answer path) and raise a traced non-retryable `ProviderError` otherwise.

4. **Low — served prompt/transcript are hand-duplicated from the trained prompt, not shared.** Diff `glimmer.py` rebuilds `SYSTEM_CONTENT` ([common.py](<repo>/.muse/worktrees/20261030-be39/finetune/common.py:19)) and `format_turns` ([common.py](<repo>/.muse/worktrees/20261030-be39/finetune/common.py:57)) by hand; a future training-prompt edit silently diverges serving. Equality holds today ([test_b26_open_weight_path.py](<repo>/.muse/worktrees/20261030-be39/tests/contract/test_b26_open_weight_path.py:61)). Fix: import the shared builders or add a comment linking both sites to `finetune/common.py`.

5. **Low — `completion_tokens` includes first-pass reasoning tokens** (server: `first_tokens + answer_tokens`), while the trace field elsewhere means completion output ([base.py](<repo>/.muse/worktrees/20261030-be39/anamnesis/providers/base.py:38)); cost is latency-based so billing is unaffected, but trace readers will misread it. Fix: one comment at the server line.

6. **Info — one GPU is kept warm up to 10 min after the last request.** `scaledown_window=600`, `max_containers=1`, no `min_containers` (pinned by [test_b26_open_weight_path.py](<repo>/.muse/worktrees/20261030-be39/tests/contract/test_b26_open_weight_path.py:270)) bounds serving to a single GPU but bills idle time; also, the new `anamnesis-glimmer-serve` app can hold a GPU while an eval runs in `anamnesis-glimmer-lora`. No code fix; avoid overlapping evals with serving.

## 3. What you checked and found fine

- Engine identical: same `LLM` args incl. seed ([modal_glimmer.py](<repo>/.muse/worktrees/20261030-be39/finetune/modal_glimmer.py:248)), LoRA id 1 ([modal_glimmer.py](<repo>/.muse/worktrees/20261030-be39/finetune/modal_glimmer.py:253)), sampling/seed ([glimmer.py](<repo>/.muse/worktrees/20261030-be39/finetune/glimmer.py:35)), FlashInfer env inherited via `eval_image`, same `_two_passes` call shape with per-index seed.
- Charging: length → 1 actual + trace; malformed/no-answer/parse-reject/5xx → retried with trace or estimate per [base.py](<repo>/.muse/worktrees/20261030-be39/anamnesis/providers/base.py:58); 401 free; pre-check before each attempt; no double-charge path (trace-carrying failures skip the estimate charge).
- No token leak: `_safe` redaction follows the existing [openweight.py](<repo>/.muse/worktrees/20261030-be39/anamnesis/providers/openweight.py:134) pattern, `TimedClient` proxies it ([intake_live.py](<repo>/.muse/worktrees/20261030-be39/scripts/intake_live.py:77)); `runs.jsonl`/prints carry no tokens.
- Guards: voice check resolves symlinks/`..` and `--voice` is singular ([intake_live.py](<repo>/.muse/worktrees/20261030-be39/scripts/intake_live.py:162)); URL check uses `hostname` suffix on https, defeating userinfo/suffix tricks; photos reuse the existing allowlist ([intake_live.py](<repo>/.muse/worktrees/20261030-be39/scripts/intake_live.py:49)); `json_mode=False` override is contract-pinned despite the fireworks preset ([openweight.py](<repo>/.muse/worktrees/20261030-be39/anamnesis/providers/openweight.py:14)).

## 4. Open questions

- SPEC §4 itself wasn't verified: my section search returned nothing this session, so the 600 s scaledown, `json_mode=false` override, and GPU price are confirmed against the contract tests, not the spec text.
- The 120 s client-timeout path (cold container) is untested — `MetaClient.post` wasn't opened; what error/charge does a timeout produce?
- Should finding 1's foreign-schema requests be 400s, or is serving them intended?
- Did the five byte-match replies cover an unopened answer and a length stop, or only clean replies?
