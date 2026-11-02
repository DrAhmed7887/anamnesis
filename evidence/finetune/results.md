# The fine-tune's evaluation: results as they come in

Pre-registered in `plan.md` (973e106, amended in 5a8f13e before any training or evaluation call). Every system is scored by `finetune/score.py`, unchanged. Every miss is listed per split and system in `runs/<system>/<split>.score.txt`.

## Spark 1.3, the product's extractor today (29 Oct)
**How:** `finetune/spark_eval.py`, run on `main` at 5a8f13e. Each example's turns went through `MetaClaimExtractor`: reasoning effort low, 16,000 max tokens, the strict claims schema. The first reply was scored. All 303 examples replied, none needed the product's second attempt, and none errored.

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
The claims saved from the live runs scored 24 of 33 on test_real (3ea9b60). This draw scores 20 of 33 on the same transcripts. Spark's replies vary between calls, as U12's 10 runs showed, so one draw per system is a limit on every number here.

### Cost and time
- **Cost:** $3.495 for the 303 calls, about $0.0115 a call, plus $0.026 for a 2-example check before them.
- **Against the estimate:** the plan estimated about $1, but Spark 1.3 reasoned for a median of 2,100 to 2,440 tokens a call at low effort, and up to 6,318.
- **Latency:** the median was 7.4 to 9.4 s per split, and the longest 23.7 s, inside the extractor's 30 s timeout.

## Base and tuned Glimmer
*Run on 29 Oct, after Ahmed added a payment method to Modal and the section below was committed (66075ab).*

**Training (run r1, `runs/r1/train.json`):** as `plan.md` (5a8f13e) set it, on one H100.
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

## r2: r1's recipe on Spain's verified vocabulary (29 Oct)
Pre-registered in `plan.md`, amendment 2 (2b0415a), before any r2 call. The tables come from `PYTHONPATH=. .venv/bin/python evidence/finetune/summarize.py --table r2`. Every miss is in `runs/r2/<system>/<split>.score.txt` and `runs/spark/test_spain.score.txt`.
- **Training (`runs/r2/train.json`):** r1's settings on data_v2's 1,200 examples, on one H100: 830 s of training and 1,005,956 tokens seen. The validation loss was 0.0005 after each epoch (r1's was 0.0007, then 0.0002).
- **Evaluation (`runs/r2/eval.json`):** one vLLM 0.32.0 engine held both adapters. It scored base Glimmer, r1 and r2 on test_spain, then r2 on r1's four test splits. Spark 1.3 read test_spain through the product's extractor, in 60 calls.
- **The brands are unseen:** none of test_spain's 19 brands is in r2's training or validation data, by whole word (`tests/unit/test_finetune_v2.py::test_the_committed_v2_data_holds_the_split`). r1 never saw them either.

### test_spain: 19 Spanish brands neither run trained on
| System | Split | n | Valid JSON | Dropped by checks | Invalid JSON | No reply | Fully right | Missing / extra | Harmful before / after |
|---|---|---|---|---|---|---|---|---|---|
| Spark 1.3 | test_spain | 60 | 60 | 0 | 0 | 0 | 38 | 1 / 0 | 1 / 0 |
| Glimmer base | test_spain | 60 | 52 | 7 | 8 | 0 | 11 | 31 / 0 | 23 / 9 |
| Glimmer + LoRA r1 | test_spain | 60 | 60 | 1 | 0 | 0 | 55 | 4 / 0 | 0 / 0 |
| Glimmer + LoRA r2 | test_spain | 60 | 60 | 2 | 0 | 0 | 56 | 5 / 0 | 1 / 0 |

| System | name_text | inn | intake | strength | units_per_intake | intakes_per_day | as_needed | status |
|---|---|---|---|---|---|---|---|---|
| Spark 1.3 | 99/108 | 107/108 | 93/108 | 105/108 | 107/108 | 105/108 | 103/108 | 104/108 |
| Glimmer base | 72/108 | 77/108 | 56/108 | 62/108 | 64/108 | 61/108 | 51/108 | 74/108 |
| Glimmer + LoRA r1 | 103/108 | 104/108 | 102/108 | 104/108 | 104/108 | 103/108 | 103/108 | 104/108 |
| Glimmer + LoRA r2 | 102/108 | 103/108 | 102/108 | 103/108 | 103/108 | 102/108 | 103/108 | 103/108 |

### Every miss on test_spain
- **r2, 4 of 60, none harmful after the checks:**
  - **#6:** "So I also take Aldocumar Plus Thervan four times a day". The generator ran two sentences together with no stop, so "Aldocumar Plus" reads as a product name. r2 named "Aldocumar Plus" with the four times a day, and lost Thervan. r1 and Spark named one medicine, "Aldocumar Plus Thervan".
  - **#24:** the Arabic "الف ملي جرام" (a thousand milligrams) for Clamoxyl came out as 1 mg. The product's stated-amount check dropped it, so the intake is empty. r1 did the same.
  - **#34 and #44:** Thervan spelled "Theravan", a spelling found nowhere in the training data. The name then no longer occurs in the turn, so the product's check rejected the whole reply: #34 lost its three claims and #44 its one. #44's "Theravan" ingredient label is the one harmful string before the checks. r1 cut #34's name to "Therav", with the same rejection, and had #44 right.
- **r1, 5 of 60, none harmful:** #6, #24 and #34 as above. In #26 it kept a 10 mg intake where the patient took one or two tablets, which the key leaves empty. In #39 it wrote false for an unsaid as-needed. r2 had both right.
- **Spark 1.3, 22 of 60, none harmful after the checks:**
  - 7 names copied with the speech slip in them, such as "Cipralexlex", "Thervan Thervan" and "Tioner 150" from "Tioner 150 150 mg" (#0, #21, #28, #36, #37, #42, #52), and #6 as above;
  - 12 stated intakes left empty. Post-hoc, rewriting only the shapes batch 24 fixes (an empty strength object, an ungrounded label) keeps 3 of them, and Spark is then fully right on 40 (`spark_drops.py --spain`, output in `runs/spark/drops_spain.txt`);
  - 2 intakes kept where the key has none (#45, #52), and 2 strength misses (#41, #58);
  - 4 false-for-null as-needed values (#7, #29, #45, #55), 3 statuses left unknown (#9, #23, #36), and 2 frequencies (#6, #9);
  - #26, fully right after the checks, had the ingredient string "null" before them.
- **Base Glimmer, 49 of 60:** 8 answers ran to the 16,000-token limit, and those 8 aren't valid JSON. The checks dropped 7 replies whole. 9 claims kept a misplaced value or a placeholder as their ingredient, such as "200", "10 mg", "unknown" or "amount_digit_text": the strings that batch 24's grounding rule is written to clear.

### r2 on r1's four test splits
| System | Split | n | Valid JSON | Dropped by checks | Invalid JSON | No reply | Fully right | Missing / extra | Harmful before / after |
|---|---|---|---|---|---|---|---|---|---|
| Glimmer + LoRA r1 | test_iid | 100 | 100 | 0 | 0 | 0 | 100 | 0 / 0 | 0 / 0 |
| Glimmer + LoRA r1 | test_shift | 120 | 120 | 0 | 0 | 0 | 113 | 0 / 0 | 0 / 0 |
| Glimmer + LoRA r1 | test_codeswitch | 50 | 50 | 0 | 0 | 0 | 47 | 0 / 0 | 0 / 0 |
| Glimmer + LoRA r1 | test_real | 33 | 33 | 0 | 0 | 0 | 30 | 0 / 0 | 0 / 0 |
| **Glimmer + LoRA r1** | **all** | **303** | **303** | **0** | **0** | **0** | **290** | **0 / 0** | **0 / 0** |
| Glimmer + LoRA r2 | test_iid | 100 | 100 | 0 | 0 | 0 | 99 | 0 / 0 | 0 / 0 |
| Glimmer + LoRA r2 | test_shift | 120 | 120 | 0 | 0 | 0 | 118 | 0 / 0 | 0 / 0 |
| Glimmer + LoRA r2 | test_codeswitch | 50 | 50 | 0 | 0 | 0 | 48 | 0 / 0 | 0 / 0 |
| Glimmer + LoRA r2 | test_real | 33 | 33 | 0 | 0 | 0 | 30 | 0 / 0 | 0 / 0 |
| **Glimmer + LoRA r2** | **all** | **303** | **303** | **0** | **0** | **0** | **295** | **0 / 0** | **0 / 0** |

- **r2's 8 misses, none harmful:**
  - test_iid #57: Lyrica marked as needed, which the note says of Zyrtec. r1 had this note right;
  - test_shift #85: the held-out Inzirqo cut to "Inzir" (r1 cut it three ways, in #13, #63 and #85);
  - test_shift #97: an Arabic note that says the medicine was stopped, read as active, as r1 did;
  - test_codeswitch #10 copies the slip "Arblibli", and #41 cuts the Arabic Beloc-Zok name short, as r1 did;
  - test_real #13 to #15: U2's "Augmentin 875 and 125" read as an 875 mg intake, as r1 did.
- **r1's misses that r2 had right:** test_shift #13 and #63 (Inzirqo), #24, #34 (Naprosyn) and #59, and test_codeswitch #24.

### Reading the comparison
- **On unseen Spanish brands,** r2 is fully right on 56 of 60 notes and r1 on 55, with one reply per note at temperature 1.0. Adding 80 Spanish brands to training shows no measurable gain here: r1, trained without them, was already fully right on 55. Spark 1.3 is fully right on 38.
- **The pre-registered risk, name_text,** is where both runs miss: 102 of 108 names for r2 and 103 for r1. Each misspelled Thervan ("Theravan", "Therav") made the product reject its reply, so those claims were lost and nothing false was shown. #6 is a generated note whose two sentences run together.
- **No regression shows on r1's splits:** r2 is fully right on 295 of 303 and r1 on 290, both with 0 harmful claims.
- **Limits:** these are single runs on generated text, with the brands said inside English and Egyptian-Arabic speech, from one European market. A gap of a few notes is descriptive, and a second run of either recipe could move it.
- **r1 stays the headline result (45d6bc7).** r2 shows that adding Spain's brand names to training changed nothing measurable on these tests.

### Cost and time
- **Modal, the ledger's estimates:** r2's smoke runs $0.71, its training $1.14 (894 s with loading) and the eval $0.86 (673 s). In the eval, the engine loaded in 202 s, base Glimmer took 389 s for test_spain's 60 notes, and each adapter took 7 to 11 s per split.
- **Modal's billing summary for October, read twice after the eval:**
  - at about 14:23 CET, $9.75 of compute; at 14:30, $9.46 (`--json`: $9.45861). Both were all from credits, with $0.00 billed.
  - The figure fell by $0.29 within minutes, so it isn't final yet, and the 10:45 reading behind the ledger's first reconcile line may not have been final either.
  - The ledger stands at $9.70, which is above Modal's latest figure, so the spend checks stay on the safe side. No new reconcile line is added until Modal's figure settles.
- **Meta:** Spark 1.3 on test_spain, 60 calls, $0.80 on the ledger.

## Written before any Glimmer result: how to read the comparison
- **The bar on generated speech:** Spark 1.3 gets 193 of 303 transcripts fully right, with 1 harmful claim.
- **Learning the key's conventions:** a model trained on this key learns them. That covers the clean name instead of the copied slip (21 of Spark's misses) and null instead of false for an unsaid as-needed (25). It also covers null instead of an empty strength object, which avoids the parser's drops (23). Any gain on those is reported as the product's format learned, which a parser change would give Spark too, not as better listening.
- **For batch 24, to be pre-registered there:** an empty strength object counts as no strength, and an intake label that is empty or ungrounded becomes the claim's name. On these replies, that keeps 23 intakes, clears the one harmful label and changes nothing else.

## Re-scored after batch 24 (29 Oct, 23:45 CET)
- **What changed:**
  - **Batch 24** (6b5013e, merged in ab676b6) grounds the ingredient fields and counts an empty strength as no strength.
  - **The scorer** (`finetune/score.py`) now counts harm "after the checks" on the product's parsed output. An INN said under an alias counts as said.
- **Every number matches the prediction committed before the build** (`evidence/batches/24/rescore-prediction.md`, 1f19ca3). The CEO's reference build made that prediction:

  | System | r1's four splits (303 notes) | test_spain (60 notes) |
  |---|---|---|
  | Spark 1.3 | 193 → **203** | 38 → **40** |
  | Glimmer base | 50 → 51 | 11 → 11 |
  | Glimmer + LoRA r1 | 290 → 290 | 55 → 55 |
  | Glimmer + LoRA r2 | 295 → 295 | 56 → 56 |

- **Harmful claims after the checks,** counted on the product's output: 0 for every system on every split. Before batch 24, Spark 1.3 had 1 (the "string" label, test_iid #79), and base Glimmer had 54 on r1's splits and 9 on test_spain (`evidence/batches/24/harm_parsed_merged.out`).
- **Reading it:**
  - Spark's 10 extra notes and 23 more intakes come from parser fixes alone. That is the product's format, not better listening.
  - The headline stays r1: 290 of 303 fully right, with 0 harmful claims.
