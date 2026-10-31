# Batch 27 design: relation checks on claim amounts

You are planning, not building. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, and use no API key;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The plan is done ONLY when your reply has the four sections in §4, and every point cites a file and line you opened in this session.

## 2. What happened (31 Oct)
- **The gap:** `parse_claims_json` (`anamnesis/providers/claims.py`, around line 349) keeps a claim amount when its value is anywhere in `stated_amounts` of a cited turn. A reply that takes "ten, not five" as 5 mg, "five micrograms" as 5 mg, "two Panadol tablets" as 2 mg, another medicine's amount, a past dose or a split daily total passes. Three of those would be a false `match`.
- **Live, Spark 1.3 and the tuned Glimmer made one such error in 20 calls:** Glimmer read "ten milligrams a day, five in the morning and five at night" as a 10 mg intake.
- **The CEO prototyped six word rules** outside the product and measured them: the ten invented traps all fail safe, no claim changes in 97 saved live reports, and no fully-right reply is lost among about 1,575 committed replies on the fine-tune's test splits. The word lists were corrected twice on those replies.

## 3. The CEO's design (challenge it)
- **The specification:** SPEC.md §2, "Relation checks (batch 27)": mentions, clauses, and rules 1–6 (negation, unit, count, another medicine's, past, split daily total).
- **The contract:** `tests/contract/test_b27_relations.py`, 58 tests.
- **The build brief:** `briefs/27.md`.

## 4. Reply
1. **Verdict on the design:** one line.
2. **Risks:** numbered, each with file:line and what to do. For instance: phrasings the rules would drop wrongly; places where the SPEC is ambiguous enough for two builds to differ; interactions with the existing value check, `_grounded_label`, the dropped-amount rule or Arabic clitics; and anything the contract fails to pin.
3. **The implementation plan:** the module and functions, where the hook goes in `parse_claims_json`, and the order you'd build and test them.
4. **Open questions for the CEO.**

Keep it under 600 words.
