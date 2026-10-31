# Handoff: how to run the Anamnesis engine

For a fresh engine session, or for Ahmed. This covers the state on 28 Oct 2026. For everything since (batches 24–30, the opt-in open-weight paths, `demo-freeze` at 710b453), read `evidence/decisions.md` and the last section of `evidence/grills/m9-freeze/clean_checkout.md`.

## Roles
- **Claude Code (CEO, engine session):**
  - writes `SPEC.md`, the briefs and the contract tests;
  - proves each contract with a throwaway reference build;
  - runs Muse, the gate, the live runs and the merges.
- **Muse Code (`muse-spark-1.3`, contributor mode off)** writes the product code in `anamnesis/` and the unit tests.
- **An independent Opus supervisor** reviews every batch round (`evidence/grills/BATCH_SUPERVISOR_PROMPT.md`).
- **Gemini 4 Argon** is the quality manager at milestones: `QM_VIA=vertex scripts/qm.sh`, on the Google credit.
- **A judge-facing session** owns the claims table, the storyboard, the video and the README draft. It works on its own branch, merged once on Tue 3 Nov.

## One batch
```
scripts/batch.sh run <n>          # Muse builds from briefs/<n>.md; goal check; gate
scripts/batch.sh round <n> <r>    # a fix round from evidence/batches/<n>/round<r>-brief.md
scripts/batch.sh gate <n>         # ruff + pytest + the lock
scripts/batch.sh merge <n>        # needs "Verdict: PASS" in evidence/batches/<n>/review.md; pushes main
```

**Steps:**
1. Branch from main.
2. Write the SPEC lines, `briefs/<n>.md` and `tests/contract/test_b<n>_*.py`.
3. Prove them on a scratch copy, and record that in `evidence/batches/<n>/reference.md`.
4. Commit with the exact subject `test(contract): batch <n>`. That commit is the lock; repeat it for each round's new tests.
5. Run Muse, then the supervisor, then fix rounds, then `review.md`, then merge.
6. Commit each Muse ledger line apart: `chore(spend): Muse ledger, batch <n> ($X est.)`.

**What the gate checks:**
- It fails if anything changed since the lock under `tests/contract/`, in any `conftest.py`, or in `pyproject.toml` or `uv.lock`.
- It fails if a contract test was skipped or xfailed.
- Ruff and pytest must pass.

**The engine builds in its own worktree** (`~/Projects/anamnesis-b21`, whose `evidence/raw` links to the main checkout's). Live runs go from the main checkout, so there is one ledger.

## Money: pause at 50% of any credit
- **Before anything that spends,** run `uv run python scripts/spend_check.py --next <provider>=<usd>`. It exits 1 at 50% of Meta's, Fireworks', Baseten's, Google's or Modal's credit, or if the next step would cross that line.
- **`batch.sh`** (each Muse round) and **`qm.sh`** (each Vertex review) call it themselves.
- **The ledgers:**
  - `evidence/spend/muse_ledger.jsonl` (Muse, estimated);
  - `evidence/spend/ledger.jsonl` (the adapters; open-weight lines are named `muse-spark-open@<provider>`);
  - `evidence/spend/google_ledger.jsonl` (Vertex).
- They are estimates. Each provider's dashboard is the final word.

## Live runs
- **One intake:** `PYTHONPATH=. uv run python scripts/intake_live.py --case X --voice <wav> --photo <jpg> --lang en|ar [--repeat N]`. It writes `evidence/live/<date>/` and briefs to `evidence/raw/briefs/`.
- **The comparison:** `PYTHONPATH=. uv run python scripts/reader_eval.py --key ... --readers spark,baseten,fireworks`. It refuses any photo outside `media/public/` and `media/real-public/`. Keys come from the environment or the Keychain (`META_API_KEY`, `FIREWORKS_API_KEY`, `BASETEN_API_KEY`).
- **Pre-registration:** expected results are committed before the first call, and every miss is reported.

## Data rules (`docs/DATA_HANDLING.md`)
- **Ahmed's own photos and voice** go only to Meta's Model API.
- **Raw media, crops and briefs that embed them** stay in `evidence/raw/`, which is git-ignored.
- **Reviewers never see media.**
- **Never a `*-contributor` model.**
- **No patient data,** and no third-party human voices.
- **Video stills:** `uv run python scripts/still.py <name> --text <file|->` or `--html <page>`. It renders records, never the desktop.

## State on 28 Oct, afternoon
- **Merged:** batches 1–22. The Gemini 4 M5 review (batches 19.1–22) is triaged in `evidence/grills/m5-openweight/effect.md`.
- **The comparison** is in `evidence/batches/22/comparison.md`:
  - Spark 1.3 and Muse Spark Open on Baseten each read 14 of the 20 cropped photos right;
  - Fireworks' strict JSON mode returned no strengths;
  - SAM's "package" concept found packs in the 19 phone photos the loop missed.
- **Batch 23**, in progress:
  - the "how it got here" timeline;
  - the M5 fixes;
  - "package" as SAM's third concept;
  - strengths printed per a volume other than 1 ml are dropped.
- **Next, needing Ahmed:**
  - record his media (V1–V3, P1–P7) and fill `evidence/batches/21/manifest.md` first;
  - raise the staged-run cap for the hero's 10 runs;
  - the video voiceover;
  - the publish decisions: a filtered public repo, `LICENSE`, YouTube.
- **Dates:** feature freeze Sat 31 Oct 23:59 CET (tag `demo-freeze`). Submission Wed 4 Nov, by 15:00–16:00 CET.
