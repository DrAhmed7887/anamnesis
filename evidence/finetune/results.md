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
*Run on 29 Oct, after Ahmed added a payment method to Modal and the section below was committed (7817c35).*

**Training (run r1, `runs/r1/train.json`):** as `plan.md` (12d4a3c) set it, on one H100.
- 150 steps over 2 epochs, 998k tokens with the prompts, in 14 minutes. Peak memory was 61.3 GiB.
- The training loss went from 0.687 at step 1 to about 0.0001.
- The validation loss was 0.0007 after epoch 1 and 0.0002 after epoch 2. The validation set uses the training templates, so this says little about new notes.

**Evaluation (`runs/r1/eval.json`):** base and tuned Glimmer in one vLLM 0.32.0 engine, as pre-registered. Three changes were found in the smoke runs, and none changes a pre-registered setting:
- **The sampler:** vLLM samples through its PyTorch top-k/top-p path (`VLLM_USE_FLASHINFER_SAMPLER=0`), because FlashInfer's sampler needs a CUDA compiler the image lacks. The sampling settings are unchanged.
- **Free whitespace:** base Glimmer's constrained answers sometimes fill the schema's free whitespace until the token limit. vLLM 0.32 can only turn that off for the whole engine, and doing so also drops the spaces in `", "` and `": "`, the separators of the training answers and of Spark's replies. So the scored run keeps vLLM's default, as pre-registered, and those answers count as invalid JSON.
- **A restart:** the first full eval was cancelled 17 minutes in, when the laptop's connection dropped. Nothing from it was saved or read. The eval now saves each system and split as it finishes, and it was run again in full with the same seeds.

### Results
Every number below comes from `summarize.py`. The three systems run on the same 303 test examples.

| Split | n | Spark 1.3 | Glimmer base | Glimmer + LoRA |
|---|---|---|---|---|
| test_iid | 100 | 63 | 20 | 100 |
| test_shift (unseen templates, 10 held-out drugs) | 120 | 79 | 17 | 113 |
| test_codeswitch | 50 | 31 | 6 | 47 |
| test_real (real Voice Transcribe output) | 33 | 20 | 7 | 30 |
| **Fully right, all** | **303** | **193** | **50** | **290** |
| Harmful claims, before / after the product's checks | | 1 / 1 | 104 / 54 | 0 / 0 |
| Valid JSON | | 303 | 267 | 303 |
| Replies dropped by the product's checks | | 0 | 23 | 0 |
| Claims missing / extra | | 0 / 1 | 131 / 2 | 0 / 0 |

Field accuracy, over the 547 answer claims:

| System | name_text | inn | intake | strength | units | per day | as needed | status |
|---|---|---|---|---|---|---|---|---|
| Spark 1.3 | 519 | 547 | 506 | 538 | 547 | 530 | 522 | 520 |
| Glimmer base | 396 | 320 | 294 | 384 | 384 | 362 | 276 | 382 |
| Glimmer + LoRA | 542 | 547 | 541 | 545 | 547 | 547 | 546 | 546 |

### Every miss of the tuned model (13 examples, none harmful)
- **test_shift, 7 of 120:**
  - three cuts of Inzirqo, the brand of hydrochlorothiazide held out of training: "Inzir", "Inzirq" and "Inzirqor" (#13, #63, #85);
  - #34: Naprosyn 550 mg read as the tablet's strength instead of the intake (Spark missed this note too);
  - #59: a 40 mg intake left empty;
  - #24: as-needed left empty where the patient said it;
  - #97: an Arabic note that says the medicine was stopped, read as active.
- **test_codeswitch, 3 of 50:**
  - #10 copies the slip "Arblibli";
  - #24 reads a 600 mg tablet strength as the intake;
  - #41 cuts the Arabic Beloc-Zok name short.
- **test_real, 3 of 33:** #13 to #15, U2's "Augmentin 875 and 125". The model took 875 as the whole intake. The key holds no amount here, because the two ingredients' amounts fit no field.

### Base Glimmer's failures
- **Answers at the token limit:** 36 ran to the 16,000-token limit, filling the schema's free whitespace. The median answer was 208 tokens and the longest 15,811.
- **Misplaced values:** the ingredient fields hold misplaced values and placeholders. Before the product's checks there were 107 unsupported ingredient strings:
  - "unknown" 32 times, "null" 7 and "mg" 7;
  - numbers such as "50" or "100";
  - schema-like text such as "value_text".

  54 claims kept one after the checks, because the checks test the amounts and the name against the transcript, not the ingredient fields.
- **The likely cause:** the replies fit the schema's fixed key order pushing base Glimmer's values one slot off, since the ingredient comes before the amount. A smoke reply wrote `"inn": "5", "amount": "unit_text"`.
- **Dropped replies:** 23 were dropped whole by the product's checks.

### Reading the comparison
- **The counts:** on these 303 examples, the tuned model is fully right on 290, Spark 1.3 on 193 and base Glimmer on 50. They have 0, 1 and 54 harmful claims after the product's checks.
- **Conventions, as the section below said before the results:** the tuned model learned the key's conventions. Spark's misses of that kind are 21 copied slips, 25 false-for-null as-needed values, and 23 intakes the parser dropped after an empty strength object or label. Post-hoc, with only the shapes that trip the parser rewritten, Spark is fully right on 203 (`runs/spark/drops.txt`).
- **Unseen templates and held-out drugs (test_shift):** 113 of 120 for the tuned model. Three of its five name errors fall on one held-out brand.
- **The real transcripts (test_real):** 30 for the tuned model, 20 for Spark and 7 for base Glimmer. That's 33 transcripts from 14 synthetic-voice notes, with U12 repeated.
- **Limits:**
  - the training and test text is generated, and the real slice is small and synthetic-voiced;
  - there is one training run, and one reply per example at temperature 1.0;
  - Glimmer ran on vLLM in bf16, not on the product's serving path, which today serves only Spark 1.3.

### Cost and time
- **Modal's billing summary for 29 Oct:** $7.00 of compute, all from credits, and $0.00 billed. The workspace spend limit is $0 (Ahmed's request, 29 Oct).
- **Our ledger:** its estimates summed to $6.57, and the $0.43 difference is recorded as its own line. Modal also bills each container's idle minute after its last input.
- **By step:**
  - training $1.14 (14 min);
  - the scored eval $2.42 (32 min);
  - the cancelled eval $1.33;
  - the smoke runs $1.57;
  - the download and image builds $0.12.
- **Eval time:**
  - base Glimmer took 1,561 s for the 303 notes, reasoning for a median of 329 tokens before answering, with the runaway answers on top;
  - the tuned model took 35 s: it skips reasoning, writing a 3-token header and then a median 141-token answer;
  - Spark 1.3 took a median of 7.4 to 9.4 s per call, one call at a time.

## Written before any Glimmer result: how to read the comparison
- **The bar on generated speech:** Spark 1.3 gets 193 of 303 transcripts fully right, with 1 harmful claim.
- **Learning the key's conventions:** a model trained on this key learns them. That covers the clean name instead of the copied slip (21 of Spark's misses) and null instead of false for an unsaid as-needed (25). It also covers null instead of an empty strength object, which avoids the parser's drops (23). Any gain on those is reported as the product's format learned, which a parser change would give Spark too, not as better listening.
- **For batch 24, to be pre-registered there:** an empty strength object counts as no strength, and an intake label that is empty or ungrounded becomes the claim's name. On these replies, that keeps 23 intakes, clears the one harmful label and changes nothing else.
