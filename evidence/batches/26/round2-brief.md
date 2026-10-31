# Batch 26, round 2: five small fail-safe fixes

You are the builder for round 2 of batch 26 of Anamnesis. Round 1's code is in the working tree, uncommitted. Build on it: change only what this brief lists. Everything round 1's brief said still holds, including the hard rules.

Round 1 was reviewed three ways, and all three approved it:
- an independent supervisor probed 28 replies and every guard;
- a fresh Muse session audited it, read-only;
- the CEO deployed your server to Modal. Five test notes came back fully right and byte-identical to the eval's replies.

Five small things need fixing.

## 1. Only the expected stop reasons count as a reply (`anamnesis/providers/glimmer.py`)
**The gap:** only `"length"` is special-cased. A first pass that ended any other way (an `"abort"`, say) with an answer would be parsed as a clean reply.

**The fix:** after the trace is charged, and keeping the length check where it is:
- `first_finish` must be `"stop"`;
- with a reply, `answer_finish` must be `"stop"`;
- with no reply (`reply` null), `answer_finish` must be null.

Anything else raises a non-retryable `ProviderError("modal", ...)` with `attempt_trace=trace`, so no claim comes from it. The no-answer case (`reply` null, `first_finish` `"stop"`, `answer_finish` null) stays retryable, as now.

## 2. The server answers a bad body with 400, and passes on only role and content (`finetune/modal_serve.py`)
**The gaps:**
- a body that isn't JSON makes `await request.json()` raise, so the server answers 500. The client then retries and charges two estimates for a request that never ran;
- extra keys in a message reach the chat template. The eval passes only role and content.

**The fix:**
- catch the parse error and return the same 400 as any other bad body;
- rebuild each message as `{"role": ..., "content": ...}` before it reaches `_two_passes` and `glimmer.prompt_ids`;
- if the prompt's ids, plus `max_tokens`, exceed `glimmer.MAX_MODEL_LEN`, return a 400 before generating. The client doesn't retry a 4xx and doesn't charge it.

## 3. The Glimmer URL: no username, no password, no other port (`scripts/intake_live.py`)
**The gap:** `https://user@x.modal.run` and `https://x.modal.run:8443` pass the guard.

**The fix:**
- also refuse a URL with a username, a password, or a port other than 443 (an absent port is fine). The message still contains `modal.run`;
- the `--glimmer-url` help text says it is the server's base URL, because `/extract` is added to it.

## 4. A token test that proves something (`tests/unit/test_b26_extra.py`)
**The gap:** the test at about line 141 can't fail, because its mock never echoes the token.

**The fix:** make the mock put the token into the error body or the reply, then assert that the token appears in no raised message.

## 5. Tests for the guards' edge cases (`tests/unit/test_b26_extra.py`)
Add tests for each of these, all refused before any key is read or any client is built:
- a voice note reached through a symlink that points outside `evidence/raw/media/public/voice/` (make it under `tmp_path`);
- a folder named `voice2` next to `voice`;
- the URLs `https://user@x.modal.run`, `https://x.modal.run:8443` and `https://x.modal.run.evil.com`;
- the new stop-reason rules from item 1.

## Rules
- **Locked files:** never create, modify or delete anything under `tests/contract/`, any `conftest.py`, `pyproject.toml` or `uv.lock`.
- **Off limits:** don't edit `SPEC.md`, `docs/`, `evidence/`, `briefs/`, `NOTICE`, `scripts/batch.sh` or `scripts/goal_check.py`, and change nothing in `finetune/` but `modal_serve.py`. Don't open anything under `evidence/` or `finetune/data*`.
- **No outside contact:** no network, no API keys, no `modal` commands, no git commits.
- **Tools:** run them as `.venv/bin/ruff` and `.venv/bin/python -m pytest`. One test needs a local network socket that your sandbox forbids; if it is the only failure, say so and close your goal.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass from the repo root, and `git status --porcelain tests/contract` prints nothing.

Reply with a short report: what you changed for each numbered item, and the final test count.
