# Batch 16 review: model replies are checked at the parser (code grill C5, C3)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 2 rounds; round 2 driven by the Opus 5.5 supervisor (see supervisor.md, builder.md, round2-brief.md)

CEO: Claude Code (Opus 5.5) wrote the SPEC section, the brief and the contract; Muse wrote all the code. Gate: pass, 518 tests (453 before). Contract lock held. Muse cost, priced from its own billing records: $0.64750 + $0.47323 = **$1.12073** (`usage.json`).

Verdict: PASS (supervisor APPROVE, round 2)

## What changed
- **Numbers:** one parser for model-written amounts: decimal commas parse; "1,000" and "1.000"-style amounts, ranges, words, zero and negatives don't.
- **Optional fields become null instead of failing the reply,** one field at a time, so one bad field never loses the other claims. **A dropped claim amount takes the other with it,** so a claim can never reach `match` on what is left (the supervisor's round-1 blocker).
- **Grounding:** a claim's `name_text` must occur in a turn it cites; all six recorded live claims pass.
- **Country:** ISO-2 or null. **Advice:** `assert_no_advice` runs over every model-written name and ingredient string before parsing; `label_text` is quoted as printed.

## Process note
The supervisor's blocker was a hole in the CEO's SPEC, not a Muse slip: "null instead of failing" removed the retry that had kept a half-parsed claim from matching. Lesson: when a rule turns failures into nulls, check what the remaining fields can still conclude.
