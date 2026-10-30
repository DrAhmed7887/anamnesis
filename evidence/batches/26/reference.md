# Batch 26 reference build (CEO), before Muse builds

**Order of work, 30 Oct:**
1. Muse planned the batch, read-only (`evidence/grills/b26-muse-plan/`, triage in `effect.md`).
2. The CEO wrote SPEC §4's paragraph, the `DATA_HANDLING.md` line, the contract (`tests/contract/test_b26_open_weight_path.py`) and the brief. That is contract commit 9c83e52.
3. The CEO built a reference in a scratch clone. It was never shown to Muse.

## The reference passes the contract
- **Tests:** 33 contract tests pass, and 2,461 tests in all. Ruff is clean.
- **Files:**
  - the price and `gpu_ms` in `anamnesis/providers/base.py`;
  - a new `anamnesis/providers/glimmer.py`;
  - the options and guards in `scripts/intake_live.py`;
  - a new `finetune/modal_serve.py`.

## Mutants: 20 of 20 caught
Each mutant breaks one rule in the reference build, and the contract fails on every one:
- **The prompt:** the system prompt without the reasoning line, and `max_tokens` 8000.
- **Failing safe:**
  - a length stop retried, and a missing answer not retried;
  - no turns still calling;
  - errors naming `glimmer` instead of `modal`.
- **Spend:**
  - the guard checked after the request;
  - a string token count accepted;
  - the H100's rate alone, without the cores and memory, and seconds not rounded up.
- **The live script:**
  - Fireworks reading with JSON mode on;
  - any voice note allowed to Modal;
  - http accepted, or any host that contains `modal.run`;
  - Fireworks skipping the photo guard;
  - the glimmer flag still building Spark.
- **The server:** no auth, two containers, an hour of idle time, or one container kept warm.

The script is `scratchpad/b26/mutants26.py`.

## The live check (30 Oct, 20:09–20:16 CET)
- **Deploy:** the reference server deployed to Modal as `anamnesis-glimmer-serve`, behind proxy auth, in 6 s. The eval's image was cached.
- **Cold start, about 5.5 minutes:**
  - the weights loaded in 32 s, and vLLM's compile and CUDA-graph capture took the rest;
  - two health requests during start-up were cut off after about 61 s, first by an HTTP/2 framing error, then by an empty reply;
  - a third got 200 at 20:15:02.
  - So the warm-up must retry until it gets an answer.
- **test_iid's first 5 notes,** sent exactly as the product sends them:
  - 5 of 5 fully right, with 0 harmful claims, scored by `finetune/score.py` (`served_test_iid_0-4.score.txt`);
  - **all 5 replies are byte-identical to the replies the eval saved on 29 Oct.** Notes 1–4 were drawn with a different seed this time (the eval seeded note i with `EVAL_SEED + i`; the server seeds every call with `EVAL_SEED`). So the tuned model's choices don't depend on the draw here;
  - 2.2 to 10.9 s a note.
- **The product's own path:** `GlimmerClaimExtractor` on note 0 returned 2 claims in 6.6 s, at an estimated $0.0089 (`product_path_test_iid_0.json`).
- **What went to Modal:** only generated fine-tune notes, which `docs/DATA_HANDLING.md` already allowed.
- **Cost:** one container from about 20:09:30 until it scaled down about 20:26, so about 16 minutes. That is about $1.25 at list price, and it will be reconciled from Modal's billing summary.

## Problems found in the CEO's own work, fixed before Muse built
- **A length-stop assertion:** it required a cost above $0, which a fake call taking 0 ms can't produce. It now counts the ledger line instead.
- **A contributor-model test:** it hit a missing price, not the refusal it meant to test. It was dropped, because `ProviderTrace` already refuses such ids.
- **The load time:** the plan said about 200 s, from the eval's load. Serving cold took about 5.5 minutes, so the brief's warm-up waits up to 10.
