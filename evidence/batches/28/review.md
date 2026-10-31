# Batch 28 review: a second label reader for a pack the first still can't read after its zoom (SPEC §4 step 5b)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 3 rounds, planned first by a read-only Muse session and audited by a fresh one

**What the batch changes:**
- **A new loop step, `second_read`:** with a `second_reader`, a reading still partial or unreadable after the 2× zoom gets one read of the first read's crop by a second model.
- **When it counts:** the second reading replaces the first only when it is readable, answers for the same region, and keeps everything the first already had, with the same values: the ingredients, the strength with what it is `per`, the release unless the first's is `unknown`, and each ingredient's salt where the first named one. Otherwise the first reading stands, a `conflict: kept the first reading` step is logged, and the pack stays requestable for a re-photo.
- **The re-photo** (`add_photo`) reads the same way.
- **The live script:** `--second-reader fireworks` makes Muse Spark Open on Fireworks (low effort) the second reader. It needs `--reader spark` and a staged case, refuses any non-public photo before a key is read, and shares the first reader's `SessionGuard`.
- **Without a second reader, nothing changes:** the Opus supervisor ran 1,500 random intakes plus `add_photo` and got byte-identical outputs (3,623 sha256 matches), in rounds 1 and 2.

**Why:** in the live U1–U8 columns, Spark 1.3 read four of the eight staged packs as partial in at least one run, even after its zoom, while Spark Open read three of them correctly from the same crops. Ahmed said "Yes, build 28" (31 Oct).

**Who did what:**
- **The CEO** wrote the SPEC lines, the contract and a reference build first; the reference passed every contract test in each round.
- **Muse planned first** (`evidence/grills/b28-muse-plan/`): "Approve with fixes". Its strength-disagreement point became a rule, with tests for the dollar cap, an oversized crop and an unreadable first reading.
- **Muse built it in three rounds,** each passing the gate.
- **The fresh Muse audit** (`evidence/grills/b28-muse-audit/`) and **the Opus supervisor** (`supervisor.md`) both found the first SPEC too loose: a second reading with another release or salt, or one that knew less, could override the first. The supervisor showed a false `match` (a modified-release pack read again as immediate, and in round 2 as `unknown`). Rounds 2 and 3 closed it: the second reading must keep everything the first had.

**The gate:** pass, 2,658 tests, ruff clean, contract untouched since the latest `test(contract): batch 28` (`gate.json`).

**Found, not fixed here:** a second reader that raises a non-`ProviderError` exception crashes the intake, exactly as the first reader's zoom already does (supervisor, info); `OpenWeightLabelReader` turns its own failures into `ProviderError`.

**Cost:** Muse $3.63 in all: plan $0.23, round 1 $1.86, round 2 $0.73, round 3 $0.52, audit $0.28. The rounds are in `evidence/spend/muse_ledger.jsonl`; the grills are in neither ledger.

**The Opus supervisor's round 3 re-check:** APPROVE (`supervisor.md`): the false-match cases conflict and stay requestable, completion works, and a separate coding of 5b agreed on 20,000 random reading pairs.

**Found, not fixed here:** exact salt matching makes bisoprolol "fumarate" against "hemifumarate" a conflict (supervisor, info): safe, costs some reads; an `INN_ALIASES` equivalence after the hackathon.

**The live check** (`live-plan.md`, written before any call) runs after the merge.

Verdict: PASS
