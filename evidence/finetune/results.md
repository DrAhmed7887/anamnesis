# The fine-tune's evaluation: results as they come in

Pre-registered in `plan.md` (53fc023, amended in 12d4a3c before any training or evaluation call). Every system is scored by `finetune/score.py`, unchanged. Every miss is listed per split and system in `runs/<system>/<split>.score.txt`.

## Spark 1.3, the product's extractor today (29 Oct)
**How:** `finetune/spark_eval.py`, run on `main` at 12d4a3c. Each example's turns went through `MetaClaimExtractor`: reasoning effort low, 16,000 max tokens, the strict claims schema. The first reply was scored. All 303 examples replied, none needed the product's second attempt, and none errored.

| Split | n | Valid JSON | Transcripts fully right | Claims missing / extra | Harmful, before / after the product's checks |
|---|---|---|---|---|---|
| test_iid | 100 | 100 | 63 | 0 / 0 | 1 / 1 |
| test_shift | 120 | 120 | 79 | 0 / 0 | 0 / 0 |
| test_codeswitch | 50 | 50 | 31 | 0 / 0 | 0 / 0 |
| test_real | 33 | 33 | 20 | 0 / 1 | 0 / 0 |
| **All** | **303** | **303** | **193** | **0 / 1** | **1 / 1** |

Field accuracy per claim:

| Split (claims) | name_text | inn | intake | strength | units | per day | as needed | status |
|---|---|---|---|---|---|---|---|---|
| test_iid (185) | 176 | 185 | 164 | 182 | 185 | 181 | 174 | 174 |
| test_shift (217) | 206 | 217 | 209 | 214 | 217 | 210 | 209 | 203 |
| test_codeswitch (95) | 91 | 95 | 91 | 92 | 95 | 90 | 90 | 93 |
| test_real (50) | 46 | 50 | 42 | 50 | 50 | 49 | 49 | 50 |

### Where the 147 field misses fall (all splits)
- **intake: 41.** In 40 the intake is empty where the key has an amount. In 1, an amount the key holds as the tablet's strength was given as the intake (test_shift #34, Zyloprim 200 mg).
- **name_text: 28.**
  - 21 copy a speech-to-text slip that the generator injected, such as "Lipitortor" or "BelocZok BelocZok", where the key holds the intended name. The prompt says "Copy name_text exactly as spoken", so these misses partly measure the key's convention.
  - 6 glue the spoken amount onto the name, as in "Concor ten".
  - 1 adds "tablets".
- **status: 27,** "unknown" where the key says active.
- **as_needed: 25,** false where the key says null, meaning nothing was said.
- **intakes_per_day: 17,** empty where the key has a count.
- **strength: 9.** 4 are an amount the key holds as the intake, and 5 a tablet strength left empty.

### The one harmful claim
test_iid #79: "I'm also on Farxiga. Five milligrams three times a day." Spark labelled the 5 mg intake with the ingredient "string", the schema's type name. The product's checks kept it: they test the amount against the transcript, not the amount's label.

### Post-hoc diagnostic, not pre-registered: amounts the parser dropped
The script is `spark_drops.py`, and its output is `runs/spark/drops.txt`.

`parse_claims_json` drops both of a claim's amounts when one is dropped (SPEC §2). Two shapes of Spark's reply set that rule off with no unverified amount in them:
- an empty strength object, `"ingredients": []` (30 claims);
- an intake whose ingredient label is empty (6 claims), or is neither the claim's name nor anywhere in the transcript (1 claim, the "string" above).

I scored the replies again with only those shapes rewritten: the strength set to null, and the label set to the claim's name.
- **The result:** 23 more intakes are right and none are lost. Fully right transcripts go from 193 to 203, and the harmful count from 1 to 0.
- **Units ranges:** I also rewrote ranges such as "1-2" (31 claims). That gains nothing more, and loses 6 intakes and 4 strengths, so the rule earns its keep there.
- **The hero's transcript:** test_real #9 and #10 are U12 transcripts, and each lost both amounts this way: Spark sent empty strength objects and empty labels in #9, and empty labels in #10. The hero's live runs didn't keep their replies, so it can't be told whether r01, r05 and r09 failed the same way.

### Against the live runs
The claims saved from the live runs scored 24 of 33 on test_real (7d1fe26). This draw scores 20 of 33 on the same transcripts. Spark's replies vary between calls, as U12's 10 runs showed, so one draw per system is a limit on every number here.

### Cost and time
- **Cost:** $3.495 for the 303 calls, about $0.0115 a call, plus $0.026 for a 2-example check before them.
- **Against the estimate:** the plan estimated about $1, but Spark 1.3 reasoned for a median of 2,100 to 2,440 tokens a call at low effort, and up to 6,318.
- **Latency:** the median was 7.4 to 9.4 s per split, and the longest 23.7 s, inside the extractor's 30 s timeout.

## Base and tuned Glimmer
Not run yet. Modal asks for a payment method before it runs a GPU big enough for Glimmer (`plan.md`, 29 Oct). The smoke runs, the training and the evaluation will follow the plan as committed in 12d4a3c.

## Written before any Glimmer result: how to read the comparison
- **The bar on generated speech:** Spark 1.3 gets 193 of 303 transcripts fully right, with 1 harmful claim.
- **Learning the key's conventions:** a model trained on this key learns them. That covers the clean name instead of the copied slip (21 of Spark's misses) and null instead of false for an unsaid as-needed (25). It also covers null instead of an empty strength object, which avoids the parser's drops (23). Any gain on those is reported as the product's format learned, which a parser change would give Spark too, not as better listening.
- **For batch 24, to be pre-registered there:** an empty strength object counts as no strength, and an intake label that is empty or ungrounded becomes the claim's name. On these replies, that keeps 23 intakes, clears the one harmful label and changes nothing else.
