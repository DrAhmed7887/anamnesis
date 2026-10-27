# Batch 19.1 review: the quality manager's M4 fixes (SPEC §2, §3, §7)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 2 rounds, goal pinned with its goal tool in each

**Who did what:**
- Claude Code (Opus 5.5), as CEO, wrote the SPEC lines, the brief, the contract (from the M4 triage, `evidence/grills/m4-muse-brief/effect.md`) and the round-2 brief.
- Before Muse started each round, the CEO ran the contract against a throwaway reference build: the whole suite passed (674, then 707). The Node playback test caught all four script mutants.
- Muse wrote all the code.

**Gate:** pass, 707 tests (638 before). The contract lock held in both rounds.

**Goal (`goal.md`):** in each round, `create_goal` with the batch's check, then closed complete. 27 of 28 main-agent model calls were under it in each round.

**Muse cost:** **$1.49567** for the batch, priced from Muse's own billing records (`usage.json`):
- round 1: $0.78363, from 2,657,634 input tokens (2,438,019 cached) and 33,744 output;
- round 2: $0.71204, from 2,628,185 input (2,444,803 cached) and 27,315 output.

Verdict: PASS (supervisor APPROVE, round 2)

## What changed
- **Arabic numbers:** the Arabic decimal sign `٫` reads as a dot under the same rules (`٢٫٥` is 2.5).
- **Arabic advice words** are caught with attached clitics (`وتناول`, `فيجب`) and after diacritics and tatweel, still as whole words (`يتناول`, `تناولت` and `أخذ` pass). The clitic list is now one shared constant.
- **Feminine release words** (`ممتدة`, `بطيئة`) count as said.
- **The formulation note** names both causes: "Reported and pack formulations differ (salt or release form)."
- **Salts on the brief:** they show on both sides, from the strength, the intake and the scalar `inn`, so a salt-only mismatch is visible.
- **No model-written salt:** a label strength with a key beyond `LABEL_SCHEMA`'s is a malformed reply. Before round 2, a model's salt text could reach the brief unchecked.
- **Overlaps from conflicted claims:** such a claim counts only by what its readings share. "Concor" with a metoprolol strength is no longer listed as metoprolol; "Panadol" with paracetamol + caffeine still overlaps with Gelocatil.
- **A fourth scope line** says what the checks across medicines cover.
- **A region whose photo is missing** is refused rather than skipped.
- **Turn playback is now tested:** the page's script runs in Node in the contract (one listener, a turn switch mid-play, an evidence link).

## Follow-ups (from the supervisor; none blocking)
- Next contract: pin escaping and `dir="auto"` on the Ingredient rows.
- A later SPEC follow-up: suffixed and negated Arabic advice forms, NFKC presentation forms, and the "فخذ" false positive. Each fails safe today.
