# Fine-tune plan: Muse Glimmer 30B with a LoRA for claim extraction

This plan was committed before any training call. It follows Ahmed's call of 28 Oct evening (`evidence/decisions.md`): a LoRA fine-tune of Meta's open-weight **Muse Glimmer 30B** on Fireworks, as the Fireworks credit request said (`credit-requests.md`:61, in the hackathon folder). The facts on Fireworks were checked on 28 Oct against its docs and the account (summary at the end).

## The task, and why it departs from the blueprint
- **The task is the intake's claim extraction.** The patient's transcript turns go in, and claims JSON comes out in the exact schema that `anamnesis/providers/claims.py` sends Spark 1.3 (`_SYSTEM_PROMPT`, `CLAIMS_SCHEMA`). The user message is formatted as `MetaClaimExtractor` formats it.
- **Every output is scored by the product's own parser,** `parse_claims_json`, with its stated-amount and no-advice checks. So a tuned model is judged by exactly the rules Spark 1.3 is, and it could be plugged into the intake later.
- **Why not the blueprint's version 1** (`finetune-eval-plan.md` §1): there, the model outputs discrepancies too. In Anamnesis, plain code compares the two sides and no model decides a finding (claims row 1.16), so only the step a model already does here is trained. Label reading stays out (the blueprint's v2).

## The data: generated, with every answer built in code
`finetune/gen.py`, seeded and deterministic:
- **Drugs:** the catalogue's brands and aliases, with their INNs. Ten drugs are held out of training entirely.
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
