muse: workspace root: <repo>/.muse/worktrees/20261030-e1b8 (cwd default)
muse: warning: rules file at <repo>/CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
1. **Verdict on the draft:** directionally right, but the endpoint will not reproduce the eval unless seed, batching, timeouts and cost path are pinned — fix those before building (`finetune/modal_glimmer.py:190`, `anamnesis/providers/claims.py:397`).

2. **Design**
- Modal class, e.g. `finetune/modal_serve.py:ServeGlimmer`, reusing `eval_image` (`finetune/modal_glimmer.py:63`), `LLM(...enable_lora...)` settings (`finetune/modal_glimmer.py:249`), `SAMPLING`/`MAX_TOKENS`/`MAX_MODEL_LEN` (`finetune/glimmer.py:35`), and `_two_passes` (`finetune/modal_glimmer.py:190`) unmodified.
- One method `@modal.fastapi_endpoint(requires_proxy_auth=True) def extract`; request `{"transcript": str, "seed": int}` built from `format_turns` (`finetune/common.py:57`); response `{"reply": str|null, "opened_answer": bool, "first_finish": str, "answer_finish": str|null, "first_tokens": int, "answer_tokens": int|null, "seconds": float}` mirroring `rows` (`finetune/modal_glimmer.py:208`).
- `scaledown_window=600`, `min_containers=0`, plus `warmup()` that builds the engine once so `load_s` (`finetune/modal_glimmer.py:256`) happens before first request.
- `anamnesis/providers/glimmer.py:GlimmerClaimExtractor(client, guard, endpoint, token)` with `extract(self, turns: list[AudioTurn]) -> tuple[list[PatientClaim], ProviderTrace | None]`, same as `MetaClaimExtractor.extract` (`anamnesis/providers/claims.py:397`), including `[], None` on empty turns (`anamnesis/providers/claims.py:399`).
- Inside `extract`: system `SYSTEM_CONTENT` (`finetune/common.py:19`), user `format_turns(turns)` (`finetune/common.py:57`), `guard.check(estimate)` (`anamnesis/providers/spend.py:32`), POST, `parse_claims_json` + checks (`anamnesis/providers/claims.py:453`), `guard.charge_prechecked(trace)` (`anamnesis/providers/spend.py:42`), wrapped in `with_one_retry` (`anamnesis/providers/base.py:70`); trace `model_id="muse-glimmer-30b+lora-r1@modal"` in `ProviderTrace` (`anamnesis/providers/base.py:38`), cost `glimmer.cost_usd(seconds)` (`finetune/glimmer.py:125`) from `USD_PER_S` (`finetune/glimmer.py:19`).
- Flags in `scripts/intake_live.py:main` (`scripts/intake_live.py:157`): extend `--reader` choices (`scripts/intake_live.py:168`) with `fireworks` using `PRESETS["fireworks"]` (`anamnesis/providers/openweight.py:14`) but `json_mode=False`, i.e. schema-in-prompt (`anamnesis/providers/openweight.py:79`); add `--extractor {spark,glimmer}` defaulting to `MetaClaimExtractor(timed, guard)` (`scripts/intake_live.py:112`) so default path calls `run_intake` (`scripts/intake_live.py:110`) and `render_brief` (`scripts/intake_live.py:119`) unchanged.
- Token from `keychain("MODAL_PROXY_TOKEN")` (`scripts/intake_live.py:56`); voice gate before any call mirroring the Baseten photo gate (`scripts/intake_live.py:175`), refusing non-synthetic voice.

3. **Risks**
1. Batch→single changes decoding: `_two_passes` takes a list (`finetune/modal_glimmer.py:190`) — serve exactly one prompt per call or outputs diverge; pin it.
2. Seed is per-index (`finetune/modal_glimmer.py:200`) from `EVAL_SEED` (`finetune/glimmer.py:38`) — served path must fix one seed rule (e.g. always `EVAL_SEED`) or "exact reproduction" is undefined.
3. Cold load ~200 s vs client timeout `30.0` (`anamnesis/providers/meta.py:104`) and logged `claim requests` (`scripts/intake_live.py:127`) — warm up at deploy and treat first-call timeout as retryable (`anamnesis/providers/meta.py:124`).
4. Modal web timeouts kill long requests unlike `evaluate` (`finetune/modal_glimmer.py:229`) with `EVAL_TIMEOUT_S` (`finetune/glimmer.py:22`) — set endpoint timeout ≥ eval worst-case, never retry inside the deadline.
5. Length stop must fail safe, not retry: Spark raises non-retryable (`anamnesis/providers/claims.py:447`), same in open-weight reader (`anamnesis/providers/openweight.py:123`) — copy that.
6. Missing answer header (`finetune/glimmer.py:115`, recorded `finetune/modal_glimmer.py:207`) has no Spark analogue — raise retryable `ProviderError` with `attempt_trace`, like malformed replies (`anamnesis/providers/claims.py:434`).
7. Token leak via errors/reports/brief: `_safe` redacts (`anamnesis/providers/meta.py:117`), used on parse errors (`anamnesis/providers/claims.py:456`, `anamnesis/providers/openweight.py:134`); key is "never printed or saved" (`scripts/intake_live.py:13`) but reports/runs/briefs are written (`scripts/intake_live.py:118`) — wrap the Modal client in `_safe` and never log headers.
8. Time-based cost breaks `cost_usd` token pricing (`anamnesis/providers/base.py:120`) and `spark_call_estimate` (`anamnesis/providers/meta.py:74`) — needs its own pre-call estimate or `guard.check` (`anamnesis/providers/spend.py:32`) under-caps cold calls.
9. Fireworks preset defaults `json_mode=True` (`anamnesis/providers/openweight.py:14`) and live code hardcodes Baseten preset (`scripts/intake_live.py:106`) — parameterise model/price/json_mode or the flag silently uses the wrong path.

4. **Tests the contract should pin**
- Served single call byte-matches `_two_passes` on one fixed conversation (`finetune/modal_glimmer.py:190`).
- Fixed seed reproduces; differing seed may differ (`finetune/modal_glimmer.py:200`).
- `extract([])` returns `[], None` (`anamnesis/providers/claims.py:397`).
- Length stop raises non-retryable with trace (`anamnesis/providers/claims.py:447`).
- No-header reply raises retryable, fails safe (`finetune/glimmer.py:115`).
- Parse path identical to product checks (`anamnesis/providers/claims.py:453`).
- 401 is non-retryable, no estimate charge; 5xx/timeout retryable with estimate (`anamnesis/providers/meta.py:124`).
- Token never appears in raised messages, reports, or runs lines (`anamnesis/providers/meta.py:117`, `scripts/intake_live.py:121`).
- No-flag run equals Spark-only (`scripts/intake_live.py:112`); `--reader fireworks` sends no `response_format` (`anamnesis/providers/openweight.py:94`).
- Non-synthetic voice refused before any spend (`scripts/intake_live.py:175`).

5. **Open questions for the CEO**
- Exact served seed rule, given per-index eval seeds (`finetune/modal_glimmer.py:200`)?
- Endpoint timeout and max retries given 200 s loads (`finetune/modal_glimmer.py:256`) vs 30 s client (`anamnesis/providers/meta.py:104`)?
- Pre-call estimate formula for time-billed calls for `guard.check` (`anamnesis/providers/spend.py:32`)?
- Should 401/`--extractor glimmer` refusal exit like the Baseten gate (`scripts/intake_live.py:175`) or raise `ProviderError` (`anamnesis/providers/base.py:15`)?
- Keep `price_key` for Fireworks as `muse-spark-open@fireworks` (`anamnesis/providers/base.py:111`)?
