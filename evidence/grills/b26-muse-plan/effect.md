# Muse's plan for batch 26: what it changed

**What ran:** Muse Code (muse-spark-1.3, standard mode) planned batch 26 in its own worktree copy (`scripts/grill.sh b26-muse-plan`), read-only, on 30 Oct at 19:56 CET, before the CEO wrote the contract. Ahmed asked for it: "dont you think muse should plan and double check?"

**Verdict:** "directionally right, but the endpoint will not reproduce the eval unless seed, batching, timeouts and cost path are pinned". All 9 of its risks were checked against the code it cited, and each is now in the contract or the brief (contract commit 7f79c23).

| # | Muse's risk | Outcome |
|---|---|---|
| 1 | Batch to single changes decoding | Taken. The server runs `_two_passes` on one conversation per request (SPEC §4), and `max_containers=1` with Modal's default of one input at a time serialises requests |
| 2 | The seed is per index | Taken as a rule: every served call is seeded with `EVAL_SEED`. The CEO's live check then found the five served replies byte-identical to the eval's, for notes 1–4 as well, whose eval seeds differed (`evidence/batches/26/reference.md`) |
| 3 | A cold load of about 200 s against the 30 s client timeout | Taken. `GLIMMER_TIMEOUT_S` is 120 s, and the server is warmed through `GET /health` before timed intakes. The live cold start took about 5.5 minutes, so the warm-up waits up to 10 |
| 4 | Modal's web timeout kills long requests | Taken. The function timeout is 600 s and the client gives up at 120 s, so a stuck call fails safe and is charged as an estimate |
| 5 | A length stop must fail safe, not retry | Pinned: non-retryable, charged from its trace (two contract cases) |
| 6 | A missing answer header has no Spark analogue | Pinned: retryable, with its trace |
| 7 | Token leaks | Pinned: the token never appears in an error, through `MetaClient._safe` (the 401, 5xx and parse-error cases) |
| 8 | Time-based cost breaks token pricing and the pre-call estimate | Taken. `cost_usd` gains `gpu_ms`, priced at the eval's list price. The guard checks the whole timeout at that price before the request |
| 9 | The Fireworks preset defaults to JSON mode on, and the script hardcodes Baseten | Taken. The reader is built from `PRESETS[provider]` with JSON mode off; `PRESETS` itself is unchanged and pinned |

**Its open questions, answered in the SPEC:** the seed rule (always `EVAL_SEED`), the timeouts (120 s client, 600 s function), the pre-call estimate (the timeout at the per-second price), that guards exit before any call while a 401 at run time raises `ProviderError`, and the price key `muse-spark-open@fireworks`.

**Not taken:** sending only the transcript and building the prompt on the server. The server would then need the product's package in its image. The product sends both messages instead, and a contract test pins them to the training prompt (`SYSTEM_CONTENT` and `format_turns`).

**Muse's tests list:** all but one became contract tests. "Served single call byte-matches `_two_passes`" needs a GPU, so it became the CEO's live check.
