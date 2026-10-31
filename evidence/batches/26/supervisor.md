# Batch 26 supervisor (independent Opus subagent)

## Round 1

SUPERVISOR: APPROVE

Nothing meets a CHANGES criterion. Finding 1 needs your check before the live run.

**Verified**
- **Scope:** only the five in-scope files changed. The extra line in `evidence/spend/muse_ledger.jsonl` comes from `scripts/muse_usage.py`, not the builder. `claims.py`, `meta.py`, `openweight.py`, `finetune/glimmer.py`, `finetune/modal_glimmer.py` and `tests/contract` are untouched. Ruff is clean and the 50 batch-26 tests pass.
- **Prompt:** the request body equals `SYSTEM_CONTENT` plus `format_turns` on 300 random turn lists, with one POST per attempt.
- **Engine:** the `LLM(...)` arguments, `LoRARequest("r1", 1, "/runs/r1/adapter")`, `runs.reload()`, the image, the GPU and `MACHINE` all match r1's `evaluate` (its `max_loras=max(1,1)` is 1). `_two_passes` runs unchanged on `[messages]`, with `max_tokens` 16000 (= `MAX_TOKENS`) and seed `EVAL_SEED`+0. All seven response fields are correct.
- **Failing and charging,** over 28 probed replies:
  - a 4xx is not retried or charged;
  - a 5xx, timeout, transport error, non-JSON or malformed reply is charged as two $0.15274 estimates;
  - a length stop is charged once (real) and not retried;
  - nothing is charged twice, the provider is always `modal`, and the token never appears in a message.
  - Only a reply nested 100,000 levels deep escapes, as a raw `RecursionError`. That comes from the shared parser and is impossible under the schema.
- **Guards** run before any key or client:
  - refused voice notes: `..`, file and folder symlinks, and a `voice2` prefix;
  - refused URLs: `x.modal.run.evil.com`, `x.modal.run@evil.com` and `HTTPS://`.
- Fireworks reuses the Baseten photo-folder check, and `spend_check.py` books `@modal` lines to the modal credit.

**Findings**
1. **Medium, unverified** (`anamnesis/providers/meta.py:108` via `glimmer.py:45`, and `finetune/modal_serve.py:7`): the client sends `Authorization: Bearer <token>`, which the contract pins. As far as I know, Modal's proxy auth expects `Modal-Key` and `Modal-Secret` headers. If so, every live call gets a 401: safe and uncharged, but it returns no claims. Fix: check against your reference call; if it fails, change the contract to send both headers and redact both parts of the token.
2. **Medium, in the contract** (`modal_serve.py:55,90-98`): the client gives up at 120 s, but the server keeps generating, because `_two_passes` is synchronous inside `async def` and the server timeout is 600 s. Up to 480 s of GPU per timed-out attempt gets charged as 120 s. Fix: reconcile from Modal's billing, or match the server timeout to the client's.
3. **Low** (`scripts/intake_live.py:187`): the default `--session-usd 0.25` is less than two $0.15274 estimates, so the retry the SPEC promises never runs live. The first uncertain attempt raises `SessionCapExceeded` and ends the intake, skipping SAM and the reader. This is safe. Fix: raise or document `--session-usd` for glimmer runs.
4. **Low** (`intake_live.py:231-234`): URLs with a username or an odd port pass. `https://evil.com@x.modal.run` goes to `x.modal.run`, and httpx swaps the Bearer header for Basic auth, so no token leaves: not a bypass. Separately, the help text at line 202 says "extract URL", but `/extract` is appended to it. Fix: refuse a username, a password or any port other than 443, and call it the base URL.
5. **Low** (`modal_serve.py:92`): a non-JSON body gets a 500, not the brief's 400. Extra keys in a message also reach the chat template; the eval strips them with `messages_of`. The product sends neither. Fix: catch the parse error and return 400, and rebuild each message as role and content only.
6. **Low** (`tests/unit/test_b26_extra.py:141-148`): Muse's tests are meaningful and weaken nothing. This one token test proves nothing, because the mock never echoes the token, and no test covers symlinks or URL tricks.
7. **Merge** (`scripts/batch.sh:120`): the merge stages only anamnesis, tests, evidence, briefs, SPEC, pyproject and uv.lock. `scripts/intake_live.py` and the untracked `finetune/modal_serve.py` would miss the commit, and the contract tests would fail on a fresh clone. Stage both files explicitly.

**CEO's decisions on round 1:**
1. **Refuted by evidence.** Both live checks (the reference at 20:15 and the batch server at 20:32) sent exactly `Authorization: Bearer <token id>.<token secret>` and got 200s with replies. Modal's proxy-auth page names that single header as one of its two forms. No change.
2. **Accepted as a limit.** The 600 s timeout also bounds the container's start, which took 5.5–5.8 minutes, so it stays. The tuned model never ran to its limit on 363 scored notes. Modal's billing summary is the final word, reconciled into `evidence/spend/modal_ledger.jsonl`.
3. **Handled in the run:** the live columns use `--session-usd 0.50` in all three columns.
4. **Into round 2.**
5. **Into round 2,** together with the Muse audit's #2.
6. **Into round 2:** the token test, and tests for symlinks and URL tricks.
7. **Taken:** the CEO stages `scripts/intake_live.py` and `finetune/modal_serve.py` before the merge.

## Round 2

SUPERVISOR: CHANGES

The product code is correct. The only blocking problem is one test in item 5 that can never fail.

**Findings**
1. **MEDIUM: the symlink test doesn't test symlinks.** `tests/unit/test_b26_extra.py:201–208`.
   - **Evidence:** the link and its target both sit in `tmp_path`, outside `public/voice`, so any guard refuses them. I changed the guard at `intake_live.py:228` to `Path(os.path.abspath(args.voice))`, which handles `..` but doesn't follow links. That mutant passes this test and the contract, and no other test touches this guard.
   - **The guard itself is right:** with `MEDIA` pointed at `tmp_path` and `media/public/voice/link.wav` linking to `tmp_path/outside.wav`, the real code refuses with "may go to Modal".
   - **Fix:** give `_refused` a `media` argument, `monkeypatch.setattr(il, "MEDIA", tmp_path/"media")`, and put the link inside `media/public/voice/`.
2. **LOW: the refusal prints the whole URL.** `scripts/intake_live.py:243`.
   - **Evidence:** `https://u:secret@x.modal.run` prints `secret` to the terminal. It isn't the Modal token, which comes only from the environment or the Keychain, so this doesn't block.
   - **Fix:** print only the host.

**Round 1 checks still hold**
- **Scope:** only `base.py`, `glimmer.py`, `intake_live.py`, `modal_serve.py` and `test_b26_extra.py` differ from HEAD. HEAD moved to 1d1549a while I worked, a Muse-ledger-only commit at 20:50. The contract is untouched.
- **Prompt:** the two messages equal `SYSTEM_CONTENT` and `format_turns`.
- **Engine and cost controls:** I loaded the server with stand-in modal/fastapi/vllm. Its `LLM(...)` arguments, LoRA and runs reload match `evaluate`. Proxy auth is on, `max_containers` 1, timeout and scaledown 600, no `min_containers`.
- **Charging:** each new error carries its charged trace and makes one call.
- **The token:** error bodies that echo it on 400/401/422/500 come back redacted.
- **Tests:** 2,489 passed, ruff is clean, `tests/contract` has no changes.

**Nothing the fixes broke**
- The 10 replies served live in the smoke runs all ended stop/stop, and a valid reply gives claims.
- A reply with no answer still retries, and then succeeds.
- Real-style URLs pass, with a trailing slash, `:443` or uppercase.
- Prompts of 600 and 4,480 tokens plus 16,000 pass the length check.

**Round 2 items**
1. **Stop reasons:** held (`glimmer.py:84–108`; tests caught all four stop-rule mutants).
2. **Server bodies:** held (`modal_serve.py:92–103`):
   - non-JSON, empty and non-UTF-8 bodies get a 400 before generating;
   - extra message keys are stripped before the template and `_two_passes`;
   - 4,481 + 16,000 tokens gets a 400.
3. **URL:** held (`intake_live.py:232–243`):
   - a username, a password, ports `:8443`/`:80`/`:abc` and `.modal.run.evil.com` are refused;
   - the help text says it's the base URL.
4. **Token test:** held. Removing `_safe` makes it fail.
5. **Edge-case tests:** not held for symlinks (finding 1). The `voice2`, URL and stop-rule tests each catch their mutant.

**CEO's decision on round 2:** both findings go into round 3, which changes nothing else. The live check of round 2's server passed before this review came in (`batch_smoke_r2/`): 5 of 5 notes byte-identical to the eval's replies, and three bad bodies refused with 400.

## Round 3

SUPERVISOR: APPROVE

Both round 2 findings are fixed, and round 3 changed nothing else.

1. **Symlink test (was MEDIUM): fixed.** `tests/unit/test_b26_extra.py:201–248`.
   - The test now points `il.MEDIA` at `tmp_path`, so `link.wav` sits inside `media/public/voice/` and points outside it.
   - With my exact round 2 mutant (`Path(os.path.abspath(args.voice))` at `intake_live.py:228`), this test fails. With `.absolute()`, it fails along with the contract's `..` test.
   - The new test for a real file inside the folder fails when the guard refuses every voice note, so it proves something too.
2. **URL in the refusal (was LOW): fixed.** `scripts/intake_live.py:243` now prints only the host, or "missing URL".
   - I tried 9 bad URLs, with a password, a bare username, a bad port, a query string, no scheme or no URL. None showed the secret, and every message still contains `modal.run`.
   - No test pins this: putting the full URL back passes every test. That doesn't block.

**Nothing else changed:**
- Against my round 2 copy, only those two files differ, and only in the places above. That covers `anamnesis/`, `scripts/`, the unit and contract tests, `finetune/*.py` (including `modal_serve.py`) and `pyproject.toml`.
- The Muse ledger shows as modified again; that's the harness logging round 3's spend, not the builder's code.
- 2,490 tests pass, which matches the gate. Ruff is clean, `tests/contract` has no changes, and my runs left the worktree as it was.
