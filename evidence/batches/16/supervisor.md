# Batch 16 supervisor (Claude Opus 5.5, high effort, read-only)

Prompt: `evidence/grills/BATCH_SUPERVISOR_PROMPT.md`. The builder was Muse Code (`muse-spark-1.3`); the supervisor is a different model family and was not told the CEO's opinion.

## Round 1: SUPERVISOR: CHANGES

1. **blocker** `anamnesis/providers/claims.py`, `anamnesis/providers/numbers.py`: when one claim amount field doesn't parse it is dropped alone, and the claim can then reach `match` with no clinician review; before this batch the same reply failed and was retried. Ran both probes:
   - a claim of Panadol with strength paracetamol 500 + caffeine "65 mg" and intake paracetamol 500, against plain Panadol 500 mg: the strength (and the caffeine with it) is dropped, and the result is `match` (with caffeine "65" it is `insufficient_information`);
   - Concor strength 5 mg with intake "5-10", against Concor 5 mg: the intake is dropped, and the result is `match` (intake "10" gives `intake_differs_from_unit_strength`).
   The builder followed the brief and SPEC literally: a hole in SPEC §2, not a builder slip. Fix: a dropped claim amount takes the other with it; SPEC line; tests.
2. **minor** test gap: nothing pins that the advice check runs on raw strings before fields are dropped (`{"inn": "bisoprolol; take two", "amount": "five"}`).
3. **minor** `"1.000"` parses as 1, though on a European pack it means 1000 (fails safe today, as a false `strength_mismatch`); the mirror of the `"1,000"` rule. Orchestrator decision.
4. **minor** maintainability: the ingredient-`inn` advice walk is written twice; `parse_label_json` mutates the parsed dict in place.
5. **minor** scope: `intake_amount` is also nulled when it fails validation for other reasons; harmless once #1 is in; document it in SPEC.
6. **minor**, orchestrator scope: the contract commit's SPEC also described crop-first reads (Z8) and Spark estimates and length stops (C6, C7) as batch 16, with no brief or contract.

**CEO triage:** all accepted. #1, #3 and #5 went into SPEC §2 and #1 and #3 into the contract (second `test(contract): batch 16` commit, `9152fae`); #6 relabelled to batch 18 in SPEC with the current behaviour stated; #1–#4 sent back to Muse as round 2 (`round2-brief.md`).

## Round 2: SUPERVISOR: APPROVE
All four round-1 fixes check out; the full suite passes (518).
- **#1:** the Panadol claim whose caffeine amount is "65 mg" or "sixty-five" now gives `insufficient_information` with review (round 1: `match`); the parseable "65" case is unchanged. Concor 5 mg with intake "5-10" now gives `insufficient_information` with review (round 1: `match`); intake "10" still gives `intake_differs_from_unit_strength`.
- **#3:** "1.000", "2.500" and "٢.٥٠٠" return null; "0.125", "00.125", "12.5", "1.25", "1.0000" and "1000" still parse.
- **#4:** `parse_label_json` builds one new dict; the ingredient advice walk lives once, in `guardrails.assert_no_advice_in_ingredients`.
- The new advice-order unit tests fail against a mutated copy where the check sees only what's left after a field is dropped.
- Nothing worse: the both-null rule only runs when a claim sent an amount that was dropped; the recorded live replies still match.
- Minor, not required: the single-field advice checks still have a small wrapper in both parsers.
