# Fine-tune plan: Muse Glimmer 30B with a LoRA for claim extraction

This plan was committed before any training call. It follows Ahmed's call of 28 Oct evening (`evidence/decisions.md`): a LoRA fine-tune of Meta's open-weight **Muse Glimmer 30B** on Fireworks, as the Fireworks credit request said (`credit-requests.md`:61, in the hackathon folder). The facts on Fireworks were checked on 28 Oct against its docs and the account (summary at the end).

## The task, and why it departs from the blueprint
- **The task is the intake's claim extraction.** The patient's transcript turns go in, and claims JSON comes out in the exact schema that `anamnesis/providers/claims.py` sends Spark 1.3 (`_SYSTEM_PROMPT`, `CLAIMS_SCHEMA`). The user message is formatted as `MetaClaimExtractor` formats it.
- **Every output is scored by the product's own parser,** `parse_claims_json`, with its stated-amount and no-advice checks. So a tuned model is judged by exactly the rules Spark 1.3 is, and it could be plugged into the intake later.
- **Why not the blueprint's version 1** (`finetune-eval-plan.md` §1): there, the model outputs discrepancies too. In Anamnesis, plain code compares the two sides and no model decides a finding (claims row 1.16), so only the step a model already does here is trained. Label reading stays out (the blueprint's v2).

## The data: generated, with every answer built in code
`finetune/gen.py`, seeded and deterministic:
- **Drugs:** the catalogue's 9 entries, with their brands, aliases and INNs. To these are added about 60 common medicines from RxNorm: the ingredient, its brand names and its marketed strengths, in `evidence/data/rxnorm_drugs.json`. Ten of those RxNorm medicines are held out of training entirely. Amended 29 Oct, before any data was generated: the RxNorm grounding showed that the catalogue has 9 entries, too few to hold out 10.
- **Utterances,** from templates in English and Egyptian Arabic, including Arabic–English mixing. They cover:
  - a brand or an INN, and an amount in digits or in words, with units;
  - regimens ("twice a day", "two tablets", as needed);
  - a stopped medicine, a range ("one or two"), no amount, and two or three medicines per note.
- **The speech-to-text noise seen on 28 Oct,** at a set rate: a repeated word or number ("ten ten", "10 10"), and a doubled or run-together brand ("BelocZok BelocZok", "BelocZokZok").
- **The answer** is built from the same choices in code, never by a model. Where the product's rules say a field is null (a range, an unstated amount), the answer says null.
- **Splits:** train 1,200; val 150; test_iid 100; test_shift 120, with templates unseen in training and the 10 held-out drugs; test_codeswitch 50, with heavy Arabic–English mixing. Templates are split between train and test.

## The real-transcript slice
These are the transcripts Muse Voice Transcribe actually returned on 27–28 Oct, for the U cases and the two synthetic notes. There are 33 distinct transcripts from 14 notes, in 54 saved reports. All are synthetic voices, but the speech-to-text output is real, including U12's repeated words. Each answer is written from the note's script before any model sees the slice. This is the honest test of noise that no template fully imitates.

## Training (Fireworks)
- **The job:** supervised fine-tuning on `accounts/fireworks/models/muse-glimmer-30b` with LoRA rank 16, set explicitly (through the API, an omitted rank means full-parameter training), for 2 epochs at Fireworks' default learning rate.
- **The targets:** answers only. The system and user turns get weight 0, set explicitly. Every model gets the product's system prompt with reasoning strength set to low.
- **Cost:** Fireworks' docs say SFT on this model is free for jobs started before 1 Dec 2026. If it is billed, it costs about $3 per 1M training tokens, and this set is about 2–3M.

## The comparison: the same prompt, schema and parser for all three
- **Spark 1.3,** through Meta's API: the product's own extractor today.
- **Base Glimmer.**
- **Glimmer with the LoRA.**

Base and tuned Glimmer run on Fireworks, through whichever of these two is chosen before the evaluation, and the choice is recorded with the results:
- the Serverless Training sampler, which needs no deployment;
- one on-demand deployment for about an hour, deleted afterwards. That costs about $8 per GPU-hour.

Fireworks no longer serves base Glimmer serverlessly, and it serves no LoRA serverlessly.

## The metrics, fixed now
- **Per claim:** name, INN, amount and unit, regimen, and status, each against the answer.
- **Per transcript:** every claim exactly right.
- **Harmful:** an amount or INN that the transcript doesn't support. This is counted before and after the product's stated-amount check, which would drop it.
- **Also:** the share of replies that are valid JSON, latency, and cost.
- **Every miss is listed per split and system.** With one training run and these n, the results are descriptive: never "better" or "beats" without the counts beside them.

## Limits, stated before the results
- The training and test text is generated, so it measures the task on generated speech, not real speech.
- The real-transcript slice comes from synthetic voices.
- There is one training run and no tuning of its settings.

## Spend
`scripts/spend_check.py` runs before each paid step. The stop line is 50% of the Fireworks credit.

## Facts checked on 28 Oct
- **The account:** `accounts/<account>` is ready and unsuspended.
- **Quotas:** 32 H200, B200 and B300 training GPUs each; 8 job submissions; 8 serverless training runs at once; 0 serverless LoRA adapters.
- **The docs:** LoRA SFT on Glimmer is free for jobs before 1 Dec 2026, takes a JSONL `messages` format with per-message weights, and defaults to rank 8 (firectl). An omitted rank through REST or the SDK means full-parameter training.
- **Serving:** base Glimmer left Fireworks serverless on 25–26 Sep 2026, and a tuned LoRA is served on-demand only. Reasoning tokens count against `max_tokens`.

## Amended 29 Oct: training on Modal (Ahmed's call, before any training call)
- **Why:** Fireworks refused both dataset uploads on 29 Oct with "HTTP 403: dataset uploads are temporarily disabled, please contact Fireworks AI to get access", and the two datasets stay in UPLOADING. Ahmed chose to train on Modal now, on his $100 Modal credit, rather than wait for Fireworks support. Where this section disagrees with "Training (Fireworks)" and the Fireworks serving lines above, this section wins. The task, the data, the metrics and the limits stay as written.
- **Weights:** `meta-models/Muse-Glimmer-30B` from the Hugging Face Hub (Apache-2.0, not gated), pinned at revision `cec94fcfd6512f2cfe708138c32533b346ea4f69`, in bf16 (59.6 GB). They go into a Modal volume. Nothing is uploaded to the Hub.
- **Hardware:** one 80 GB H100 on Modal, at $0.001097 per second plus 8 cores and 32 GiB (list prices, 29 Oct). An H200 was the first choice.
- **Training** (`finetune/glimmer.py` holds every setting; `finetune/modal_glimmer.py` runs it):
  - A bf16 LoRA, not QLoRA: the base stays frozen in bf16. Rank 16, alpha 32, dropout 0.05.
  - The adapter sits on every linear layer of the 52 language-model blocks except the attention's output gate: q, k, v and o, and the MLP's gate, up and down, 364 layers in all. The vision tower is frozen and untouched.
  - **Targets, answers only:** Glimmer's chat template renders the system, user and answer messages. The loss covers only the assistant's turn after `<|start|>assistant`: its channel header ` to=user<|message|>`, the JSON and `<|eot|>`. No reasoning text is trained, because gen.py's answers have none.
  - AdamW at a learning rate of 1e-4, since Fireworks' default doesn't exist off Fireworks. 8 warm-up steps, then a cosine decay to 0. No weight decay, gradients clipped at 1.0. An effective batch of 16 (micro-batch 2 × 8 accumulated), 2 epochs, so 150 steps. Seed 20261029, with gradient checkpointing.
  - The validation loss on the 150 val examples is logged after each epoch. One run with no tuning: the adapter at the end of epoch 2 is the one evaluated, whatever the validation loss says.
- **Inference for base and tuned Glimmer** (vLLM 0.32.0 on the same kind of H100):
  - The messages are the training ones: the product's system prompt with "Reasoning strength: low", and the user message as `MetaClaimExtractor` formats it.
  - **Two passes per example.** The first is free: the model reasons until it opens its answer to the user (`to=user<|message|>`). The second continues from there under the product's `CLAIMS_SCHEMA`, through vLLM's structured outputs, just as Meta's API constrains Spark 1.3's reply after its reasoning. Together the two passes get at most the product's 16,000 tokens.
  - A reply that never opens an answer counts as no reply. vLLM's Glimmer reasoning parser isn't used: it never ends the reasoning phase for a `to=user` answer, so the schema would never apply.
  - Sampling follows the model card's recommendation: temperature 1.0, top-p 0.95, top-k 64, one reply per example, with a fixed seed per example.
- **Spark 1.3:** `finetune/spark_eval.py` sends each test example's turns through the product's own `MetaClaimExtractor`: its prompt, its schema, reasoning effort low and 16,000 max tokens. Its first reply is scored. When the parser rejects a reply the product asks once more, and that retry is counted but not scored, so every system is scored on one reply per example. Expected cost: about $1 for the 303 test examples.
- **Scoring:** `finetune/score.py`, unchanged, on every system and split.
- **Smoke runs first, never scored:** 2 training steps on 32 examples, then 2 examples per test split. They check the template's masking, the adapter's 364 layers, vLLM's LoRA loading and the two passes. Their outputs stay under `evidence/finetune/runs/smoke*`.
- **Cost:** each Modal step first runs `scripts/spend_check.py` with its timeout at list price. Train and eval are capped at 2 h each, so at most $9.17 each. Each step's wall time at list price, an over-estimate, goes to `evidence/spend/modal_ledger.jsonl`. Expected: about 1 h of training and 1 h for both evals, so about $10 of the $100 credit. The stop line is 50%, as everywhere.
- **Limits added:**
  - The learning rate and the target layers are this plan's choice, not Fireworks' defaults.
  - Glimmer runs in bf16 on vLLM, not on Fireworks' serving stack, so its numbers describe this setup.

### Facts checked on 29 Oct
- **Glimmer's config:**
  - a dense model of 29.6B parameters, including a 1.8B vision encoder;
  - 52 layers, a width of 6,656, 32 query heads and 2 KV heads, and a vocabulary of 202,048;
  - attention alternates three sliding-window layers with one global layer.
- **Support in the libraries:** transformers ships `muse_glimmer` (5.21.0 is used here). vLLM 0.32.0 lists Glimmer with LoRA support, and its LoRA loader maps Hugging Face's layer names.
- **Modal:** on this account, it asks for a payment method before it runs a GPU large enough for Glimmer. The H200, H100 and A100 80 GB were each refused on 29 Oct, before anything ran.

## Amended 29 Oct (2): r2, the same recipe on a verified Spanish vocabulary (Ahmed's call, before any r2 call)
**Why:** Ahmed asked for better, non-US data, from "WHO and USA or Europe, whatever makes it easy". r1 stands as run and scored (f07e273). r2 changes only the names the patient says.

**The vocabulary:** `scripts/drugs_v2.py`, from AEMPS CIMA (Spain's medicines agency), read 29 Oct, written to `evidence/data/drugs_v2.{json,md}`.
- 59 of r1's 60 INNs map to a Spanish name that CIMA's own SNOMED CT VTM confirms. Prednisolone has no marketed tablet or capsule in Spain.
- There are 136 Spanish brands, each the first word of a marketed tablet or capsule product, up to 4 per INN. Each comes with its strengths as the product names print them, its WHO ATC code and its SNOMED CT VTM id.
- A brand is dropped if it says its ingredient ("Acido", "Aspirina", "Vals").
- Three products were spot-checked against CIMA's record: Emconcor (C07AB07, [SNOMED CT id removed]), Eutirox (H03AA01) and Adiro (B01AC06).

**The data (`finetune/data_v2/`, `finetune/gen.py --vocab v2`, same seed):**
- Of the Spanish brands of r1's training INNs, 99 are new names, meaning not already a US or catalogue name.
- One in five, drawn with seed + 2, is held out: 19 brands over 17 INNs, such as Astudal, Thervan, Brotmin and Nolpaza. The other 80 are added to their medicines in training, with Spain's printed strengths joined to the US ones.
- r1's 10 held-out INNs are the same, and none of their Spanish brands are used.
- **train** (1,200) and **val** (150) follow r1's recipe, templates and 25% noise.
- **test_spain** (60) uses the training templates. Its notes say only the 19 held-out brands and never an ingredient name, so every mention is a name neither r1 nor r2 has seen.
- A unit test regenerates r1's data byte for byte, and another finds none of the 19 brands in train or val, by whole word.

**Training r2:** exactly r1's settings (`finetune/glimmer.py`: rank 16, alpha 32, the same 364 layers, lr 1e-4, batch 16, 2 epochs, seed), on data_v2's train and val, with one H100 on Modal. A 2-step smoke run comes first, as for r1.

**Evaluation:** r1's method unchanged: the two passes, the product's schema, the model card's sampling, 16,000 tokens and the same seeds. It runs in one vLLM engine with both adapters (`modal_glimmer.py --jobs`):
- base Glimmer, r1 and r2 on test_spain;
- r2 on r1's four test splits (test_iid, test_shift, test_codeswitch, test_real), to check for regressions;
- Spark 1.3 on test_spain through the product's extractor (`spark_eval.py test_spain --data finetune/data_v2`).

A 2-example smoke eval comes first.

**The metrics** are those above, every miss listed, by `finetune/score.py` unchanged.
- **Expected risk:** name_text on the unseen brands, as r1 cut the held-out "Inzirqo" three ways.
- **The reading:** r2 against r1 on test_spain asks whether training on more European names helps with unseen ones. r2 against r1 on the old splits asks whether it cost anything. Both runs are single runs, so the results are descriptive.

**Limits:**
- one European market (Spain);
- brand names inside English and Egyptian-Arabic speech, with no Spanish-language templates;
- generated text, and one run each.

**Cost:** Modal about $4 (training about $1.20, the eval about $2.50), Meta about $0.70. `spend_check.py` runs before each step, and Modal's spend limit is $0.
