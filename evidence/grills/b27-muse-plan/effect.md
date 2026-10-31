# Effect of Muse's plan grill on batch 27 (31 Oct, CEO)

Verdict: "Ship with tightened wording". The session's model is `muse-spark-1.3` throughout; the `contributor` count of 4 is the product's own refusal string, read from `claims.py`.

| # | Muse's point | Effect |
|---|---|---|
| R1 | Pin how "don't" tokenizes | Already pinned: SPEC rule 1 names the `t` token after "don"; the contract tests "don't" and "never miss … five". No change. |
| R2, Q1 | A bare number still grounds any unit | Intended: a unit-required gate would drop "Concor five", common in speech. SPEC "Known limits" says it. No change. |
| R3 | Count vs strength: "the 10 ملليجرام tablets" | Already literal: rule 3 applies only with no unit word after the run; contract pins it. No change. |
| R4, Q2 | The walk-back's stop words are undefined | **Accepted.** SPEC rule 4 now says any other word stops the walk, with two examples. |
| R5 | Past with a comma vs "but" | Already pinned: both are clause ends, and the contract has both forms. No change. |
| R6, Q3 | Rule 6's fraction is undefined | **Accepted.** SPEC rule 6: exactly 2, 3 or 4 times, Decimal arithmetic, any unit, another number run in any cited turn. |
| R7 | Hook order | **Accepted.** SPEC says the check sits between the value check and the rule that drops the other amount. |
| R8 | Own names from raw or relabelled labels | **Accepted, further:** amount labels are no longer own names at all, only `name_text`, the catalogue entry's names and the grounded `inn`. A wrong label could otherwise make another medicine's name the claim's own. Measured on the prototype: no note lost and no saved report changed without them. Contract: `test_an_amount_label_alone_doesnt_make_a_name_the_claims_own`. |
| Q4 | Does "now" split "Now I take five"? | Yes, "now" ends a clause; it is in SPEC's list. No change. |
