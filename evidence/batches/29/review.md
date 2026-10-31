# Batch 29 review: Spark's claim prompt adds one sentence for combination products (SPEC §2, "Prompts")

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 1 round, audited by a fresh Muse session; no read-only plan (one constant, already tested live in the pilot)

**What the batch changes:** `MetaClaimExtractor` sends Spark 1.3 the trained claim prompt plus one sentence: "A combination product said with one amount per ingredient, such as 'Augmentin 875 and 125 milligrams', is its strength: one ingredient per amount, in the order said, each named for the ingredient it belongs to." `_SYSTEM_PROMPT` is unchanged, so the tuned Glimmer's served prompt and the fine-tune's prompt are too (contract pinned).

**Why:** U2 ("I take Augmentin, 875 and 125 milligrams, twice a day") missed in all three of the day's live runs: Spark wrote no amount, or "875 and 125" as one string (`evidence/diagnostics/u2-claims-2026-10-31/`). Ahmed: "Fix U2 first (~$4)", then raised the Meta stop line to $80 for the full re-measure.

**Who did what:**
- **The CEO** ran a pilot written down before the calls (`pilot-plan.md`, 10 calls, $0.13): with the sentence, 6 of 6 combination calls (English and Egyptian Arabic) gave the strength 875/125, and the one-ingredient and hero controls were unchanged. Then the SPEC line, the contract (5 tests) and a reference build (all 2,699 tests passed).
- **A fresh Muse audit passed it** with no findings (`evidence/grills/b29-muse-audit/`, $0.16).
- **The Opus supervisor approved** (`supervisor.md`), and its scoring note changed the re-measure plan before any call.
- **Muse built it in one round** ($0.56): the constant, Spark's prompt, and four unit tests. It noted that `glimmer.py` imports the trained prompt under the alias `_SPARK_SYSTEM_PROMPT`, which now reads as stale; harmless, and left alone because the brief keeps `glimmer.py` unchanged.

**The gate:** pass, 2,703 tests, ruff clean, contract untouched since `test(contract): batch 29` (`gate.json`).

**The re-measure** (`remeasure-plan.md`, written before any call) runs after the merge: Spark 1.3 with the new prompt on 363 notes, and U2 three times live.

**Cost:** Muse $0.72 in all: round 1 $0.56, audit $0.16.

Verdict: PASS
