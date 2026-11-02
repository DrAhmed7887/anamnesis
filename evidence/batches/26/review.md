# Batch 26 review: the open weights inside the product, both optional (SPEC §4)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 3 rounds, planned first by a read-only Muse session and audited by a fresh one

**What the batch changes:** two optional steps, each behind a flag of `scripts/intake_live.py`. Without a flag, nothing changes: Spark 1.3 extracts the claims and reads the labels.
- **`--extractor glimmer`:** the tuned Muse Glimmer 30B (LoRA r1) extracts the claims.
  - It is served on Modal by `finetune/modal_serve.py`, with the eval's own engine and decoding: one H100, at most one container, scaled to zero after 10 idle minutes, behind proxy auth.
  - `GlimmerClaimExtractor` (`anamnesis/providers/glimmer.py`) sends the trained prompt and runs every product check on the answer.
  - Its cost is the call's seconds at Modal's list price (`cost_usd(..., gpu_ms=)`).
- **`--reader fireworks`:** Muse Spark Open on Fireworks reads the labels, with JSON mode off.
- **The guards** run before any key is read:
  - only the staged cases' synthetic voice notes, and only on an https `.modal.run` host with no username, password or odd port;
  - only the public photos go to Fireworks.
- **Why:** Ahmed's go, 30 Oct. Both open-weight models had been evaluated, but neither ran in the product. The batch lands before the freeze (Sat 31 Oct 23:59).

**Who did what:**
- **Muse planned first,** read-only (`evidence/grills/b26-muse-plan/`, $0.21), because Ahmed asked for it. Its 9 risks went into the contract, including four the CEO's draft lacked: the seed rule, one conversation per request, the timeouts, and an estimate for time-billed calls.
- **The CEO** wrote the SPEC paragraph, the `DATA_HANDLING.md` line, the contract and the brief (7f79c23).
  - **The reference build** passed and caught 20 of 20 mutants (`reference.md`).
  - **The CEO's reference server on Modal** returned 5 of 5 test notes fully right and byte-identical to the eval's replies.
  - **Two problems in the CEO's own contract** were fixed before the build.
- **Muse wrote all the code:**
  - **Round 1** ($1.54): the price, the extractor, the options and guards, the server, and 17 unit tests.
  - **Round 2** ($0.94): five fail-safe fixes from the reviews.
    - Only a `"stop"` ends a usable reply.
    - The server answers a bad body with 400 and passes on only role and content.
    - The URL guard refuses a username, a password or a port other than 443.
    - There is a token test that can fail, and tests for the guards' edge cases.
  - **Round 3** ($0.34): a symlink test that really puts the link inside the voice folder, and a URL refusal that names only the host.
- **Independent checks:**
  - **The Opus supervisor** (`supervisor.md`):
    - Round 1 approved, after probing 28 replies and every guard. Its "Modal expects other auth headers" was refuted by two live 200s and by Modal's docs.
    - Round 2 asked for changes: the symlink test couldn't fail.
    - Round 3 approved.
  - **A fresh Muse session audited round 1** read-only (`evidence/grills/b26-muse-audit/`, $0.36): "Sound build", with six findings and none blocking. Two of them went into round 2.
  - **The batch's own server on Modal,** after rounds 1 and 2, each time:
    - 5 of 5 test notes fully right and byte-identical to the eval's replies, with 0 harmful claims;
    - the product's own extractor returned its claims in 6.4–6.7 s;
    - three bad bodies got a 400 without generating (round 2).

    Round 3 changed no server code (`batch_smoke/`, `batch_smoke_r2/`).
- **The held-out guard:** the goal check flagged none in rounds 1 and 2. In round 3 it flagged `evidence/raw/media/public/voice/U1.wav`. That was a path Muse passed to the script's `main()` with every client stubbed out, to probe the voice guard. Nothing read the file, and it's a synthetic voice note, not an expected result.

**The gate:** pass, 2,490 tests, ruff clean, contract untouched since 7f79c23 (`gate.json`).

**Found, not fixed here:**
- **A client timeout doesn't stop the server's generation.** The 600 s server timeout also bounds the 5–6 minute start, so it stays. Modal's billing is the final word on cost.
- **The server takes the schema from the caller,** as `evaluate` takes it as an argument. Only proxy-token holders can call it.
- **The URL refusal's wording isn't pinned by a test.**
- **The per-intake cap of $0.25 is below two Glimmer estimates,** so a retry would stop the intake instead (fail safe). Live Glimmer runs pass `--session-usd 0.50`.

**Cost:** Muse $3.39 in all: plan $0.21, round 1 $1.54, audit $0.36, round 2 $0.94, round 3 $0.34. The rounds are in `evidence/spend/muse_ledger.jsonl`; the two grills are in neither ledger, as before. Modal: three cold starts and three 5-note checks, about $3.60 at list price, to be reconciled from Modal's billing.

Verdict: PASS
