# Grill: what are we missing to win?

You are a skeptical judge of the Meta AI Developer Hackathon (Cerebral Valley, Oct–Nov 2026) and a senior engineer who has judged many hackathons. Find what would stop this entry from winning, and what would most raise its chances with the time that is left.

- **Be concrete and specific to this project.** No generic hackathon advice.
- **Don't invent facts.** If you'd need something you aren't told, say "unknown" and name what to check.
- **Never suggest medical advice features** or regulatory claims: the product deliberately gives no advice.

## The entry
- **Anamnesis** is a pre-visit medication intake. Before a visit, a patient records a short voice note about the medicines they take, in English, Egyptian Arabic or a mix of the two, and photographs their medicine packs.
- **The agent reconciles what was said with what the packs print.** It gives the clinician a one-page brief of findings, each citing its evidence (a transcript turn, a crop of the photo).
- **The finding types:** `match`, `strength_mismatch`, `intake_differs_from_unit_strength` (for example 10 mg taken against a 5 mg tablet), `missing_modality` (said but not photographed, or the reverse), `unreadable_source`, `unresolved_name` and `insufficient_information`.
- **It never gives advice.** The clinician can request a re-photo, and the agent pauses and resumes.
- **The pipeline,** a bounded agent loop:
  1. Meta Voice Transcribe;
  2. claim extraction by Muse Spark 1.3 with a strict JSON schema, or optionally a fine-tuned Muse Glimmer 30B served on Modal;
  3. SAM 3.1 segments each photo;
  4. each crop's label is read by Spark 1.3, or optionally Muse Spark Open on Fireworks;
  5. a deterministic reconciler, with a catalogue grounded in RxNorm and carrying WHO ATC codes;
  6. the clinician brief, as HTML with a "how it got here" timeline of every model call, with tokens, cost and latency.
- **Provenance rules:**
  - an amount must be stated in the transcript;
  - a medicine's name must occur in the turn it cites;
  - no advice strings pass;
  - a label amount must be printed on the label;
  - anything uncertain fails safe, so no finding is shown as fact.
- **How it was built:**
  - Claude Code (Anthropic) acted as the planner and reviewer. It wrote the specification and the contract tests first.
  - Meta's Muse Code agent wrote all the product code, in 27 gated batches, each with an independent reviewer.
  - Since 30 Oct, Muse also plans each batch read-only and a fresh Muse session audits it.
  - 2,519 tests; Meta API spend about $54 of the $150 hackathon credit.
- **The data:** patient data is synthetic only. The voices are macOS `say` voices on invented scripts, used for runs only and never in the film. The photos are public Wikimedia Commons and Cairo University CC BY pack photos.
- **The team:** one physician-engineer, solo, in the Indie pool.

## The evidence so far (every number pre-registered; all misses published)
- **The fine-tune.** A LoRA on Muse Glimmer 30B, trained on Modal on one H100 in 14 minutes, on generated multilingual transcripts.
  - On 303 held-out generated notes it is fully right on 290, with 0 harmful claims after the product's checks.
  - Spark 1.3 is fully right on 203, and base Glimmer on 51.
  - On 19 Spanish brands it never trained on: 55 of 60, against Spark 1.3's 40.
  - **Limits:** generated text, one run each.
- **Serving.** On 30 Oct the tuned model went into the product as an optional extractor, served on Modal by the eval's own code. It returned 5 of 5 test notes byte-identical to the eval's replies.
- **Live, full intakes** on 8 public-photo cases (U1–U8, synthetic voice notes), one run per case per column, 0 harmful in every column:

  | Column | Correct (of 8) |
  |---|---|
  | Spark 1.3 extracts and reads | 4 |
  | Tuned Glimmer extracts, Spark 1.3 reads | 3 |
  | Tuned Glimmer extracts, Spark Open on Fireworks reads, before a fix | 1 |
  | The same, after a fix | 5 |

  - **The third column's cause:** every one of its misses came from Fireworks timeouts, because the reader asked for no reasoning effort. The fix: ask for low effort, as Spark 1.3's reader does.
  - **The claims:** Glimmer gave the same claims as Spark on 7 of 8 cases, in about a third of the time.
  - **The remaining misses:** a pack read as partial, a Chinese-only pack that never prints the brand, and a combination product's two amounts.
- **The hero case.** A staged disagreement on public photos, run 10 times live: a Concor dose different from its box, and a Beloc-Zok brand mismatch.
  - All three findings together came out in 6 of 10 runs, and the others failed safe. No harmful reading.
  - Its pre-registered expectation used the wrong finding type, so it scored 0 of 10 as pre-registered.
- **The clinician's pause** (a re-photo request, then a resume) worked live, as pre-registered.
- **A zero-shot label-reading comparison,** 20 public photos: Spark 1.3 14 correct, Spark Open on Baseten 14.

## The submission
- **The pool and bonuses:** the Indie pool, plus the Best Agentic Use-Case and Best Build on Meta Open Weight Models bonus prizes.
- **Judging,** from our notes: creativity, technical ambition, whether it works, and use of Meta AI tooling.
- **The materials:**
  - a video of at most 3 minutes: screen captures from the frozen code and Ahmed's own voiceover;
  - a README with an architecture diagram, how to reproduce, an evidence index and a claims table that cites the evidence;
  - the public repository: a filtered copy, Apache-2.0.
- **Deadlines:** the feature freeze is Sat 31 Oct, 23:59 CET. After it, only fixes for harmful agreements, wrong provenance, advice leakage, spend-cap failures or the demo path go in. Submission is Wed 4 Nov, 15:00 CET.
- **Deliberately not built:** a FHIR export, barcode reading, a longitudinal medication record ("digital twin"), any medical advice, and a patient-facing app. The intake runs as a script that produces an HTML brief.

## Your reply
1. **The five biggest risks to winning,** ranked. For each:
   - the judge's likely objection, in their words;
   - which criterion or bonus it hits;
   - what we can do about it.
2. **What's missing, in three groups.** For each item give the effort in hours, the risk, and why it matters:
   - (a) worth doing before the freeze (at most about 4 hours, small and safe);
   - (b) only in the video, README or demo, by Wed 15:00;
   - (c) tempting but not worth it.
3. **The overclaim check:** which of our statements above a skeptical judge would dispute, and how to phrase them so they hold.
4. **For each bonus prize:** do we have what that judge looks for? What would make it undeniable?
5. **The single most important change,** in one sentence.

Keep it under 1,200 words.
