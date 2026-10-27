# Batch 17 review: the reconciler's remaining false agreements (code grill C1, C4, C8; QM M3 r2 #2, #3, #5)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 2 rounds; round 2 driven by the Opus 5.5 supervisor (see supervisor.md, builder.md, round2-brief.md)

CEO: Claude Code (Opus 5.5) wrote the SPEC lines, the brief and the contract; Muse wrote all the code. Gate: pass, 558 tests (518 before). Contract lock held. Muse cost, priced from its own billing records: $0.70279 + $0.55817 = **$1.26096** (`usage.json`).

Verdict: PASS (supervisor APPROVE, round 2)

## What changed (every case was a false `match` before)
- **C1, tablets per intake:** "half of the 20 mg Lipitor" (not splittable) → `strength_mismatch`; "two of the Concor 5" → `intake_differs_from_unit_strength`; also when the model copied the tablet strength into the intake. Units never produce `match`. A dropped `units_per_intake` nulls the claim's amounts.
- **C4:** a label or claim that names two products is an extraction conflict (`insufficient_information`); one product named by brand and ingredient is not.
- **C8:** a release the patient didn't say can't make a `match`; one that disagrees still flags `formulation_mismatch` (Muse found that the literal rule contradicted two older contracts, and its asymmetric version became the SPEC).
- **Match wording:** "The compared identity and strength details agree."
- QM M3 r2 #2 and #3 needed no code: they are now pinned in the contract as regression guards.

## Process note
Both rounds' blockers came from the SPEC, not from Muse, and both were caught by the independent supervisor: first a rule that ignored the intake field, then the order in which Muse's own improvement had to be written down. Muse also corrected the CEO once (C8). Lesson: test each new rule against what the extraction prompt actually tells the model to output.
