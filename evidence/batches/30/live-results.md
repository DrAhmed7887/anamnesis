# Batch 30: the live check (31 Oct, 19:04 CET, on merged `main` 3bbc770)

**Pre-registered** (`live-plan.md`, before the build): U2 three times on the default path, with `match` in at least two of three and 0 harmful.

**Result: 1 of 3 `match`, 0 harmful. The expectation is not met.**

| Run | Transcript (Voice Transcribe) | Claim (Spark 1.3) | Pack (Spark 1.3, after zoom where needed) | Finding |
|---|---|---|---|---|
| r01 | "I take Augmentin, 875 and 125 milligrams, milligrams, twice as a day" | amoxicillin 875 mg + clavulanic acid 125 mg | `inn` "amoxicillin / clavulanic acid", 875/125 mg, immediate | `match` |
| r02 | "I take take Augmentin, 875 875 and 125 milligrams twice a day" | no amounts | `inn` "amoxicillin/clavulanic acid", 875/125 mg, immediate | `insufficient_information` |
| r03 | "I take Augmentin, 875 and 125 milligrams, twice a day," | no amounts | `inn` "amoxicillin/clavulanic acid", 875/125 mg, immediate | `insufficient_information` |

- **The pack side is fixed:** in all three runs the label reader wrote the combined `inn` beside the right strength, and batch 30 read it as that set. Before batch 30, those runs gave `insufficient_information` from the pack side.
- **The two misses are on the claim side:** Spark 1.3's claim came back without its amounts, so there was nothing to compare, and the pair failed safe.
- **The reports:** `evidence/live/2026-10-31/report_U2-b30_r0{1,2,3}.json`. The still of r01's brief is in the git-ignored `evidence/raw/video/stills/2026-10-31/1910_b30_U2_r01_brief.png`.

## Why the claim missed (post-hoc diagnostic, not pre-registered)
- **Our checks keep a correct reply:** a reply with both amounts, replayed offline through `parse_claims_json` on each run's exact transcript, keeps both amounts, including r02's "875 875".
- **What drops them:** a reply that labels both amounts "Augmentin" instead of their ingredients loses its strength, by the batch 24 grounding rule. So does a reply with no amounts.
- **Direct calls:** the same extractor (`MetaClaimExtractor`, batch 29's prompt) was called directly 11 times, with the raw replies kept (`evidence/diagnostics/u2-claims-b30-2026-10-31/`, $0.137 of Meta):
  - 5 calls on the transcript of the first U2 diagnostic;
  - 3 calls on each of r02's and r03's exact transcripts.

  **All 11 kept both amounts.**
- **So the misses are Spark's claim extraction varying between calls,** not the transcript and not our checks. The live script builds the same extractor, with the same prompt and turns.
- **U2's claim across the live checks since batch 29's prompt:** right in 4 of 6 runs (3 of 3 in batch 29's check, 1 of 3 here), and in 11 of 11 direct calls.

**Say it as:** "U2 (Augmentin 875/125): the pack is now read as its two ingredients in 3 of 3 runs. The pair matched in 1 of 3 live runs. In the other two, Spark 1.3's claim came back without its amounts, and the pair failed safe."

**Spend:** live $0.10805 (13 calls) and diagnostic $0.13661 (11 calls), all Meta.
