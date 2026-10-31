# Decision log

## 2026-10-27: Antigravity suggestions (`docs/SUGGESTIONS_FOR_CLAUDE.md`)
Ahmed approved Antigravity writing suggestions for the orchestrator, and left the decisions to Claude Code.

| Suggestion | Decision | Reason |
|---|---|---|
| Client-side spend cap and ledger | **Accepted**, batch 4 (`SpendGuard`) | Matches SPEC §5 and Muse's m0 advice to log spend per call. Built with the **documented** prices from `docs/muse/`: the file's table listed Spark at $0.15/$0.60 per 1M tokens, while the docs say $1.25/$4.25. SAM and Voice prices were also wrong |
| Barcode / GS1 DataMatrix triangulation | **Deferred** to day 5+, if there's time | Clinically strong, but a GTIN or PZN code only resolves through a product database we don't have offline. It adds a non-Meta component to a Meta hackathon and a native dependency. The PZN example in the file is unverified |
| Four literature citations | **Hold:** verify each one before use | Cornish et al. 2005 (Arch Intern Med) matches known figures. The other three are unverified, and the NEJM AI attribution looks wrong. Nothing goes into the submission unless it has been checked against the source |
| ICU levofloxacin renal-dosing case | **Rejected** | It's inpatient renal dose adjustment, which is dosing-advice territory and outside pre-visit intake |
| Astra M1 action items | Already triaged | `evidence/grills/m1-core/effect.md` |

## 2026-10-27: ER splittability
Muse (M1 #3) said ER tablets can't be split. That is too broad: some scored ER tablets (Beloc-Zok, metoprolol succinate) may be halved. Splittability is therefore a per-product `splittable` flag in the catalogue, not a rule based on release form.

## 2026-10-27: Antigravity files left in the repo
- `CLAUDE.md`: **rewritten** by Claude Code to match the decisions above (the draft had the barcode schema, the unverified citations and the ICU case as instructions, plus a wrong portal address). Committed.
- `docs/SUGGESTIONS_FOR_CLAUDE.md`: decisions logged above. Kept **out of git**, because it contains the wrong price table and personal context. It stays as a local note.
- `docs/DATASET_RESEARCH_AUDIT.md`: a reference for the eval stage (packaging-photo datasets, speech corpora, RxNorm/openFDA/CIMA APIs). **Unverified.** The DOIs and licences get checked before any dataset is used. Kept out of git until then.

## 2026-10-27: first live run (synthetic media; the ledger total printed after that run, including 7 SAM debugging calls, was $0.03249 of a $5 cap)
- **Voice Transcribe** (English, plus Egyptian Arabic with code-switching) and **Spark label reading** (strict JSON schema plus image input) worked on the first try. Spark also returned the correct release forms: Beloc-Zok `modified`, Concor `immediate`.
- **SAM 3.1** found the packs only with the concept "label" ("medicine box" and 3 others gave 0 regions). Its output format differs from the docs; batch 6 fixed the parser using the real output as a fixture.
- **New blocker, proven on live data:** Spark returns INNs with the salt ("bisoprolol fumarate", "metoprolol succinate"). The catalogue uses the active moiety, so `reconcile_all` pairs **nothing**: every finding comes back `missing_modality`. This is M1 finding #2, which we had deferred. **Next batch:** a curated salt-to-moiety mapping, with the salt kept as its own field (succinate vs tartrate stays visible to the clinician).
- **Resolved, same day (batch 7):** a curated salt-to-moiety table, with the salt kept as `IngredientAmount.salt`. On the rerun, the live readings pair: Concor → `match`; Beloc-Zok 100 mg vs "metoprolol 50 mg twice a day" → `intake_differs_from_unit_strength`. Ledger total after the rerun: $0.048 of the $5 cap. Sol hit the provider's rate limit mid-batch, and Claude Code finished it.

## 2026-10-27: claim extraction live (batches 8–9), no hand-written claims
- **English voice note:** all correct, end to end. Concor `match`; metoprolol 50 mg twice a day vs Beloc-Zok 100 mg `intake_differs_from_unit_strength`; Panadol (stopped, no pack) `missing_modality`.
- Batch 9 fixed two live findings: Spark puts the **brand** into `intake_amount.inn` (now resolved through the catalogue), and Voice writes "BelocZok" as one word (brands now also match their joined form).
- **Arabic voice note varies between runs.** The same audio gave Concor in Latin script on one run and كونكور (Arabic script) on two others. Spark keeps the name as spoken, which is correct. The catalogue knows only Latin brands, so the latest run gave `unresolved_name` for Concor. **Next:** curated Arabic-script brand aliases in the catalogue (deterministic, auditable), not LLM transliteration.
- Ledger total after the rerun: $0.129 of the $5 cap.

## 2026-10-27: batch 10 live rerun
- English chain unchanged and correct after the identity rewrite (no regression).
- The Arabic note was transcribed with **all three brands in Arabic script** this time (كونكور, بلوك زوك, البنادول, the last with an attached article). All are `unresolved_name`. That makes 3 runs and 3 different spellings of the same audio. Batch 11 (Arabic-script aliases + Arabic letter normalisation + optional ال/وال/بال) is the planned fix.
- Ledger total: $0.167 of the $5 cap.

## 2026-10-27: Meta spend outside the ledger (QM M2 round 2, #6)
The ledger only covers calls made through our adapters. Muse Code (`muse` CLI) grill runs are billed by Meta directly:
- **M0 plan grill** (run by Antigravity, 27 Oct morning): probably `muse-spark-1.3-contributor`. Cost not measured.
- **M1 core grill:** `muse-spark-1.3-contributor`, about 2.67M input / 84k output tokens ≈ **$0.20** at contributor rates. Synthetic code only.
- From M2 on, `scripts/grill.sh` pins Standard mode. Those runs will be billed at standard rates, still outside the ledger, and noted here.

## 2026-10-27: first fully correct live run in both languages (after batch 13, QM PASS)
- **English and Arabic voice notes both reconcile correctly, live and end to end, with Spark-extracted claims (nothing hand-written):** Concor → `match`; metoprolol 50 mg twice a day vs Beloc-Zok 100 mg → `intake_differs_from_unit_strength`; Panadol (stopped, no pack) → `missing_modality`.
- This Arabic run mixed all the variants seen so far: كونكور (Arabic script), "BelocZok" (joined), "الPanadol" (Arabic article on a Latin brand).
- Builder change: batch 13 was built by a Claude Sonnet subagent at Ahmed's request. A plain-codex attempt (ChatGPT login, no Sol available on that account) was stopped before it changed any file.
- Ledger total: $0.220 of the $5 cap (live adapter calls only; Muse grills are outside it, see above).

## 2026-10-27: supervisor review (Astra) changes the plan
- Found the blind spot every other reviewer shared: the showcase patient takes **two beta-blockers** (bisoprolol and metoprolol). The pairwise reconciler can't see it. A cross-medication overlap observation (templated, non-advisory) moves into B16.
- Re-prioritised to ship: B15 time-boxed to 2 h → B16 clinician brief and overlap → B17 staged real-media cases → usability check → demo. Target submission Wed 4 Nov 20:00 CET.
- Release gate narrowed: block only on harmful false agreement, wrong provenance, advice leakage, spend-cap failure, or a failure on the frozen demo path.
- Open decision for Ahmed: cut the open-weight benchmark (gives up the $10K bonus), or keep a minimal Baseten comparison if time remains.
- Full triage: `evidence/grills/supervisor-2026-10-27/effect.md`.

## 2026-10-27: open-weight benchmark cut (M2 F-09)
Ahmed accepted the supervisor plan, which cuts the Baseten/Modal open-weight benchmark (and with it the $10K Open Weight bonus) for hardware, budget and schedule reasons. The Baseten $100 credit stays unused unless time remains after B17.

## 2026-10-27: workflow change
From batch 13: Claude Sonnet subagents build (high effort); an Opus 5.5 supervisor subagent (high effort) must APPROVE each batch, read-only and independently; Claude Code orchestrates and gates. Batch 15 took 3 supervisor rounds. The supervisor caught a spend gap on the cap-refusal path and a contract test that proved nothing.

## 2026-10-27: batch 15.5 inserted before B16 (Ahmed's call): the zoom problem
- Ahmed asked to solve "the zoom problem" before B16, on a worktree branch (`batch/15.5-zoom`) so `main` stays untouched. Numbered 15.5 so the B16 and B17 references in earlier tables keep their meaning.
- A live check on 4 staged 12 MP phone photos found a **wrong-provenance bug**, not a zoom bug: SAM applies EXIF orientation and Spark doesn't, so on a portrait photo 2 of 3 labels were attached to the wrong pack. The crop-zoom also refused every rotated photo. Fix: every photo is prepared (upright pixels, all metadata including GPS dropped) before any model sees it, and a region is only read from the photo it was found on.
- The zoom itself never fired: Spark read every upright label at full frame. It stays as the fallback; it goes in the demo only if a real B17 photo triggers it and the zoomed reading is correct.
- Triage of the zoom check and of the pre-B16 idea and code grills: `evidence/grills/pre-b16/effect.md`.

## 2026-10-27: Muse Code builds from batch 16
- Batches 1–12 were built with Codex (with milestone grills by GPT-6 Astra), and batches 13–15.5 were built with Claude Code.
- Ahmed decided on 27 Oct 2026 that Muse Code builds every batch from 16 on. This closes pre-B16 J8.
- From batch 16 on, Antigravity (Ahmed's personal account) orchestrates: it writes the contracts and briefs and runs the batch reviews. **Muse Code** builds on Ahmed's personal Meta account (`muse exec --model muse-spark-1.3 --no-foreign-personal-context`, never a `*-contributor` model). Gemini via `agy` stays the quality manager.
- Muse Code build runs are billed by Meta outside our adapter ledger, so each run's cost is logged below.

## 2026-10-27 (evening): roles revised: Claude Code is CEO, Muse Code builds everything
- Ahmed decided that Claude Code acts as CEO. It writes `SPEC.md`, the briefs and the contract tests, runs Muse headless, gates, has each batch reviewed by an independent Opus supervisor, merges, and reports the Meta usage after every batch. **From batch 16 on, Muse Code writes all code.** Antigravity is no longer in the loop; its pipeline commit (`92dea05`) and SPEC v3.2 draft were kept, and the draft's unbuilt parts (crop-first reads, Spark estimates) are labelled batch 18.
- Muse usage is priced per session from its own billing records at the documented Spark 1.3 prices (`scripts/muse_usage.py` → `evidence/spend/muse_ledger.jsonl`, `evidence/batches/<n>/usage.json`). Meta's dashboard is the final word.
- GPT-family second opinions come from GPT-OSS 120B via Antigravity.

## 2026-10-27 (night): milestone M4 quality manager, Gemini 4 Argon by two routes
- Ahmed asked for the Gemini 4 QM before the next batch, "either from agy or google cloud the 50$".
- **Evidence half: Antigravity.** Free on AI Pro, but it cut the 315 KB package off at about 191 KB, then ran out of quota.
- **Code half: Vertex AI.** `gemini-4-argon`, billed to the Google Developer Program credit ($50.95 available on 25 Oct), $0.12 est.
- **Triage:** `evidence/grills/m4-muse-brief/effect.md`. The evidence half passed. The code half's HOLD rests on a by-design rule. Two majors (overlaps from conflicted claims, salts hidden in the brief) go to batch 19.1.
- **Outside the Meta ledgers.** This Google spend is outside both Meta ledgers; Cloud Billing is the final word on it.

## 2026-10-27 (night): batch 21 scope (Ahmed's call)
- **Real media, first time.** Batch 21 runs the first real phone photos and a real human voice, under `docs/DATA_HANDLING.md`, written before anything was recorded. Ahmed records the photos, and fictional voice notes that he reads himself. The expected results are written before any model sees a file, the hero case runs 10 times, and staged runs are capped at $1.
- **Contract items.** Its contract carries:
  - the QM M4 round-2 items: a salt-or-release `formulation` patient question, a pin for a salt named only in free text, a SPEC line on Unicode digits;
  - the supervisor's batch 19.1 pins: escaping and `dir="auto"` on the Ingredient rows;
  - whatever the real media show.
- **CEO tooling:** `scripts/intake_live.py` writes each brief next to its report (QM M4 code #8) and records the claim call's latency against the 30 s timeout. The live claim calls of 27 Oct took 11.6 and 13.1 s.

## 2026-10-28: one plan to submission for both CEO sessions (Ahmed's call)
- Two Claude Code sessions act as CEO on this repo. After checking the other session's open work, Ahmed approved one plan to submission in plan mode, just after midnight.
- **Owners.**
  - Session A: batch 21 (real media), the M5 grill and QM, and the README and repo prep.
  - Session B: the eval scorecard, batch 22 (the "how it got here" timeline and the batch 20 follow-ups), and the photo-request demo script.
  - A new session makes the video, from Fri 30 Oct.
- **Rules.**
  - Each session works in its own worktree and messages the other before it writes to `main` or merges.
  - One Muse run at a time, and batch numbers are claimed by message.
- **Held-out answers.** The scorecard's answer keys live in a separate private repo, outside Muse's workspace. They are published after the final pass.
- **Dates.**
  - Feature freeze Sat 31 Oct 23:59. After it, only release-gate fixes go in.
  - Submission by Wed 4 Nov 16:00 CET. That is earlier than both deadline times on record: Wed 17:00 CET in an old calendar entry, and Thu 5 Nov 03:00 CET in our notes from the participant guide.
- **Cut order if late:**
  1. the batch 22 timeline;
  2. the hosted brief;
  3. the photo-request beat in the video;
  4. extra scorecard passes.

  Never cut: the batch 21 hero case, the video, the README or the submission.
- **Tracks:** Indie and Best Agentic Use-Case. The open-weight bonus went with the cut benchmark.
- **Money:** Meta $11.55 of $150 so far, about $30 projected by submission. Google only for the M5 QM.

## 2026-10-28: the plan revised after its grill (Ahmed's call)
- An independent Opus subagent grilled the approved plan. Its verdict: the video got one pass at the end, real media came with no fix slot, and the repo could not go public as it was. The CEO verified each factual claim. Triage: `evidence/grills/plan-2026-10-28/effect.md`.
- Ahmed adopted the revision.
  - **Sessions:** one engine session runs Muse, the live calls, the one ledger and merges, from the main checkout. A judge-facing session starts today on the claims table, the storyboard, the video and the README. Session B retires before starting any of its part.
  - **Cuts:** the synthetic scorecard and its private answer-key repo. In their place:
    - pre-registered real cases, with expected results committed before any run;
    - the hero's N/10, with every miss reported.

    Batch 22 is only the "how it got here" timeline. Also cut: the `run_intake` refactor, the Unicode-break and Arabic-form follow-ups (unless real media reproduce them), and the M5 Muse grill. The M5 QM stays.
  - **New:**
    - a live run of current `main` before batch 21: it hasn't run end to end live since 27 Oct;
    - a second fix slot on Fri;
    - a rough cut on Sat;
    - a claims table before the voiceover;
    - gate hardening and a `demo-freeze` tag on Sat;
    - a handoff note;
    - submission by Wed 4 Nov 15:00 CET.
  - **Privacy, before going public:** a committed Muse export (M1) holds a personal skill catalog from work outside this project. Every Muse run also sends that catalog, because those skills load from `~/.agents/skills`, which `--no-foreign-personal-context` does not cover. So the skills get disabled in Muse before the next build, and the public repo is a filtered copy without that file.

## 2026-10-28: the zero-shot open-weight comparison returns, as batch 22 (Ahmed's call)
- **What changed:** the plan's revision had cut the open-weight benchmark and made batch 22 the "how it got here" timeline. Ahmed then said yes to a zero-shot comparison (the plan's addendum, 28 Oct). The timeline moves to batch 23 and is still the first thing cut.
- **What it is:** `OpenWeightLabelReader` (batch 22, merged in 38dd1f4) reads a pack crop with Meta's open-weight Muse Spark Open on Fireworks or Baseten, using Spark 1.3's prompt, schema and parser. `scripts/reader_eval.py` segments each photo once with SAM 3.1, and every reader reads the same crops. No model is trained: the training research found no time for a fine-tune before the freeze.
- **Photos:** only the 39 public ones: 30 Cairo University phone photos (CC BY 4.0) and 9 Wikimedia Commons photos. Their expected readings and scoring rules were committed before any call (c1b5b6e). Ahmed's own photos and voice never go to these providers (`docs/DATA_HANDLING.md`).
- **How it is reported:** a descriptive comparison, n = 39, with every miss published per photo and reader. Never a "benchmark", and never "beats". Entering the open-weight prize track waits for Ahmed to read the guide's wording.
- **Spend:** about $2 a pass on Meta's credit for SAM and Spark 1.3. The open-weight reads go on the Fireworks or Baseten credit, which the Meta total leaves out (a81c9d1).

## 2026-10-28: three AI-written notes moved to the Trash (Ahmed's call)
- **Moved to the macOS Trash:** `docs/SUGGESTIONS_FOR_CLAUDE.md`, `docs/DATASET_RESEARCH_AUDIT.md` (both 27 Oct, from Antigravity) and `docs/PUBLICATION_BLUEPRINT_LUNA.md` (28 Oct, "generated via GPT-6 Luna"). They can be restored from the Trash until it is emptied.
- **Why:** they were never committed, and the repo goes public at submission. The suggestions file held the wrong price table, personal context, and citations already flagged as non-existent (27 Oct, above).
- **What stays:** the decisions made from the suggestions file stay in the 27 Oct entries above. Briefs 14, 15 and 15.5 still tell Muse to leave the files alone, which is now moot.

## 2026-10-28: enter the open-weight bonus prize (Ahmed's call)
- **What:** the submission enters the Best Build on Meta Open Weight Models bonus ($10K), as well as the Best Agentic Use-Case bonus ($5K). This settles the open question above ("Entering the open-weight prize track waits for Ahmed").
- **Pool and bonus prizes:** the guide, as quoted in `docs/muse/gotchas.md`:25, has two prize pools, Indie and Startups. Both of these are bonus prizes beside the pool, not tracks. So the 27 Oct line "Tracks: Indie and Best Agentic Use-Case" means the Indie pool plus that bonus.
- **What the entry stands on:** batch 22's zero-shot comparison (`evidence/batches/22/comparison.md`). Muse Spark Open, on Baseten and on Fireworks, read the same SAM 3.1 crops as Spark 1.3: n = 20 photos of 17 packs, every miss listed, and diagnostic 4 labelled as a second draw. The product's label reader stays Muse Spark 1.3. So the README and the video never list Spark Open among the product's models, and never say "matches" or "beats".
- **Open:** the repo doesn't quote this bonus's own criteria. If they ask for a product built on open weights, the comparison alone may not be enough. The intake script already takes its label reader as an argument (`scripts/intake_live.py`:95), so a run of the intake with Spark Open as the reader would need only a script flag.

## 2026-10-28: the intake with Muse Spark Open as its label reader, on U1–U8 (Ahmed's yes)
- **What:** `scripts/intake_live.py --reader baseten` makes Muse Spark Open on Baseten the label reader of the full intake. Voice Transcribe, the claim extraction (Spark 1.3) and SAM 3.1 stay on Meta. It runs on U1–U8, with a Spark 1.3 control on the same code, as planned in `evidence/batches/22/intake-openweight.md`.
- **Why:** the open-weight bonus (above). The comparison read crops outside the loop; this run puts the open-weight model inside it.
- **Data:** U1–U8 are Wikimedia Commons photos with synthetic `say` notes. U9 and U10 (DailyMed) are left out, because `docs/DATA_HANDLING.md` lets only Commons and Cairo CC BY photos go to Baseten. That line now names this run too. The script refuses any other photo before the first call, and it was tested on Ahmed's media folder, the DailyMed photos and a path that climbs out of the folder. None of the tests made a call.

## 2026-10-28: no recording for now; four engine tracks instead (Ahmed's call)
- **What:** Ahmed doesn't want to record voice notes or photos for now. The engine runs four tracks in their place:
  1. the clinician's pause, live, on public photos (Cairo pack pk025: one photo read as partial, the other read fully);
  2. a staged disagreement on public photos as the film's hero case, run 10 times;
  3. RxNorm grounding of the catalogue;
  4. a LoRA fine-tune of Meta's open-weight Muse Glimmer 30B on Fireworks, as `finetune-eval-plan.md` laid out and as the Fireworks credit request said.
- **Who:** the engine owns all four, with the same gate, ledgers and pre-registration. Antigravity, which proposed the fine-tune and partner work, may review results but doesn't write to the repo.
- **What it replaces:** the 27 Oct note that no fine-tune fits before the freeze (above). Batch 24's low items (`evidence/grills/m7-pre-freeze/effect.md`) are cut first if time runs short.
- **Limits that stay:** synthetic voice notes are used only for runs, never in the film (the macOS licence). The fine-tune trains and tests on generated text, so it measures the task on generated speech, not real speech. Ahmed's own photos and voice still go only to Meta.

## 2026-10-29: train the Glimmer LoRA on Modal (Ahmed's call)
- **What:** Fireworks refused the fine-tune's dataset upload: "HTTP 403: dataset uploads are temporarily disabled, please contact Fireworks AI to get access". Ahmed chose to train on Modal now, on his $100 Modal credit, rather than wait for Fireworks support. The method was pre-registered before any training call, in `evidence/finetune/plan.md` ("Amended 29 Oct").
- **Data:** only the generated fine-tune data and the 33 synthetic-voice transcripts go to Modal. The weights come from the Hugging Face Hub. `docs/DATA_HANDLING.md` now says so.
- **Blocker found:** Modal asks for a payment method before it runs any GPU large enough for Glimmer. The H200, the H100 and the A100 80 GB were each refused on 29 Oct, before anything ran. Only image builds ran, at an estimated $0.05. Adding a card is Ahmed's call; his credit would be spent first.
- **Meanwhile:** the Spark 1.3 baseline runs on Meta's API, because either training route needs it.

## 2026-10-29: r2 on a verified Spanish vocabulary, and the standards codes into the product (Ahmed's calls)
- **r2:** Ahmed asked for better, non-US training data: "WHO and USA or Europe, whatever makes it easy to use better data". Egypt has no open drug registry, so the new names come from Spain's AEMPS CIMA. That's 136 brands over 59 INNs, each with its WHO ATC code and SNOMED CT VTM id. r2 repeats r1's recipe with those names added, and is scored on test_spain, which holds 19 Spanish brands never trained on. It's pre-registered in `evidence/finetune/plan.md` ("Amended 29 Oct (2)"). r1's results stand as run.
- **Codes in the product (batch 24):** each catalogue entry gets its ATC code, RxCUI and SNOMED CT id from `evidence/data/drugs_v2.json`, and the brief shows them. The SNOMED ids come only from CIMA. Before the repo goes public, Ahmed decides whether SNOMED ids may sit in a public repo.
- **Not before the freeze:**
  - the FHIR export, still cut;
  - UpToDate;
  - a registry strength check;
  - Spanish-language templates;
  - the draft Egyptian brand table's unverified rows.
- **Baseten:** no call until Ahmed sees the hackathon grant applied. Our $0.54 on 28 Oct matches the $1 trial dropping to $0.48.

## 2026-10-29: the builder never sees expected results (Ahmed's yes, relayed by the workshop session)
- **Why:** in Meta's legal-agent workshop, `ground_truth/` sits outside the folder the agent runs from. `scripts/batch.sh` runs Muse from the repo root, so Muse could open pre-registered expected results such as `evidence/batches/24/manifest.md`.
- **The guard:**
  - `briefs/_worker_preamble.md` now says: don't open anything under `evidence/` or the fine-tune data; write no code for one particular test case; never open `.env` or print a key.
  - `scripts/goal_check.py` lists in `goal.md` every file a run read under those folders. It flags and never fails the gate, because a read the brief asked for is fine.
- **What the 26 Muse exports up to batch 23.1 show:** 16 runs read something under `evidence/`, but none opened a manifest, a pre-registration or a fine-tune answer key. Most reads were supervisor reviews and grill triage files that the round briefs named; the others were live reports and the spend ledger. From now on, round briefs carry their findings inline instead of naming a file under `evidence/`.
- **Batch 24:** the same commit was cherry-picked onto `batch/24-es-de` before its first Muse run. Main's `evidence/batches/24/manifest.md` was never merged into that branch, so the batch worktree doesn't hold the 8 live cases' expected results.

## 2026-10-30: the four Tuesday decisions, delegated to the CEO by Ahmed
Ahmed, 30 Oct: "you decide with the help of maybe gemini agent". A Gemini research agent (`agy`, Gemini 3.8 Flash, with web search) checked the licensing facts. Its citations were re-fetched, and five dead ones were dropped.

1. **SNOMED CT leaves the repository, not only the public copy.**
   - **Why:** SNOMED International's affiliate licence and guidance don't say whether bare ids may be published worldwide. The free Global Patient Set is CC BY-ND 4.0, not CC BY, and SNOMED's IPS guide tells member-region users not to use the IPS free set. The product and the fine-tune never read the ids, so keeping them is risk with no benefit.
   - **Done:**
     - `evidence/data/drugs_v2.json` and `.md` no longer carry the 59 VTM ids.
     - `scripts/drugs_v2.py` still reads CIMA's VTM to map products but never writes it.
     - `tests/unit/test_finetune_v2.py` now asserts that the field is absent.
   - **Tue 3 Nov:** the public copy's history filter replaces the 59 ids in older commits. They are listed by `git show 2c1bffe:evidence/data/drugs_v2.json`. The one-id mentions in plan and grill notes and in the 24.1 contract go with them.
2. **Apache-2.0, for the code only.**
   - **Why:** Apache-2.0 §4(d) makes redistributors carry `NOTICE` forward, which keeps the WHOCC's required ATC reference attached. It also gives an explicit patent grant.
   - **The scope:** an open licence can't carry the WHOCC's terms (no commercial distribution, no changes), so the data stay under their own terms. `NOTICE` and a header comment in `anamnesis/core/catalogue.yaml` say so.
   - **Done:** `LICENSE`, verbatim from GitHub's licence API. The README's licence section says the same on Tue.
3. **`CLAUDE.md`:** "Synthetic data only" becomes "Patient data is synthetic only". The line names the public pack photos and Ahmed's own fictional-script recordings, which `docs/DATA_HANDLING.md` governs. QM M9 #3.
4. **No catalogue codes beside a side that contradicts its own name.** This is batch 24.2, a provenance fix, which the freeze allows.
   - **Why:** the research found no published guidance on codes beside a conflict. Medication-reconciliation sources favour the patient's own words, checking against a second source, and flagging conflicts. A code the patient's own words dispute is worse than no code.
   - **For after the hackathon:** labelling codes "from the name" next to a flagged conflict, as the research suggests.
   - **Merged as batch 24.2** (ec714ab, merged in c639af4). The supervisor approved it, and `demo-freeze` moved to f29092e.
   - **The supervisor's follow-up, for a later batch:** the check doesn't read the intake amount's own ingredient. "Concor" with an atorvastatin intake and `inn` left empty still shows bisoprolol's codes, but only when the model ignores its prompt.

## 2026-10-30: batch 25, the brief's look (Ahmed's go)
- **The decision:** Ahmed asked what the CEO thought of a pasted plan to restyle the brief. The CEO recommended a narrow batch, CSS only and built by Muse, and Ahmed answered "Run batch 25".
- **One change from that recommendation:** one HTML tag joined the batch, the viewport tag. Without it a phone lays the brief out 980 px wide, so no style could make it fit. The contract pins the tag.
- **What the pasted plan proposed and the batch didn't do:**
  - new words on a clinical page ("DISCREPANCY DETECTED", "Reviewed & Approved");
  - web fonts;
  - glassmorphism;
  - red.

  The batch adds no words, loads nothing and keeps the amber accent.
- **Merged as batch 25** (df1f251, merged in 63b9312):
  - two Muse rounds, $1.28, and supervisor APPROVE in both;
  - `demo-freeze` moved to 0d8424c, and a fresh clone passed 2,428 tests.
- **Recorded, not done:**
  - crops from real phone photos still take a row each, because a width cap would shrink the zoom view;
  - an opened timeline could clip about 10 px when printed on A5;
  - the goal check's export-wide read scan flags text quoted in tool results, a tooling fix for after the hackathon.
- **The rest of the paste (30 Oct):** its assessment text from another model stays out of the repo, the README and the film.
  - **What it gets wrong:**
    - it misdescribes batch 24.2;
    - it calls WHO ATC "CC-BY-NC";
    - it makes MDR Rule 11 and § 203 StGB claims.

## 2026-10-30: batch 26, the open weights inside the product (Ahmed's go)
- **What:** Ahmed asked what to improve in the engine with Modal and Fireworks. He said yes to the answer through a pasted AI note, with Baseten kept off.
  - Batch 26 makes the tuned Muse Glimmer 30B (LoRA r1) an optional claim extractor, served on Modal by the eval's own engine and decoding (`--extractor glimmer`).
  - It makes Muse Spark Open on Fireworks an optional label reader, with JSON mode off (`--reader fireworks`).
  - The default path stays Spark 1.3 for both steps, so the demo path is unchanged.
- **How it was built:**
  - Muse planned first, read-only, because Ahmed asked: "dont you think muse should plan and double check?" (`evidence/grills/b26-muse-plan/`).
  - The CEO wrote the contract, and Muse built the batch in 3 rounds.
  - The Opus supervisor and a fresh Muse audit reviewed it (`evidence/grills/b26-muse-audit/`).
  - Merged in 12093c9 (feat 916454b).
- **Live on Modal:** three servers, the CEO's reference and the batch's own after rounds 1 and 2, each returned 5 of 5 test notes fully right and byte-identical to the eval's replies.
- **U1–U8, three columns,** pre-registered in 9d84f59 (`evidence/batches/26/intake-plan.md`):
  - **Spark 1.3 does both:** 4 of 8.
  - **Glimmer extracts, Spark 1.3 reads:** 3 of 8.
  - **Glimmer extracts, Spark Open on Fireworks reads:** 1 of 8.
  - **0 harmful in every column.**
  - **The causes:**
    - Glimmer's claims equal Spark's on 7 of 8, and on U2 it keeps "875 mg" where Spark dropped the amount, as pre-registered;
    - its claim requests took 4.3–7.0 s, against 10.2–22.4 s;
    - the second column's extra misses are the reader's run-to-run variation;
    - Fireworks timed out at the reader's 60 s limit on 7 of 8. A labelled diagnostic read came back correct, its successful attempt taking 52 s.
- **What the README and the film may say:**
  - The product can run its claim extraction on the tuned Glimmer, served on Modal by the code that scored it.
  - Never "better", "beats" or "matches".
  - Spark Open on Fireworks couldn't be judged live on 30 Oct, because the host answered too slowly.
- **Spend:**
  - Muse $3.39: the three rounds $2.82, plus the read-only plan and audit $0.57, which are in neither ledger.
  - Modal $6.76 for serving, all credits and $0.00 billed (reconciled in `modal_ledger.jsonl`).
  - Fireworks about $0.45, and Meta about $0.40 for the live runs.
- **Open:**
  - **Fireworks' timeout:** the reader's 60 s client timeout against tonight's Fireworks latency. A batch 26.1 raising it would be Ahmed's call.
  - **Tuesday's history scrub:** the Modal account name appears in 916454b's `batch_smoke_r2/run.txt`, now redacted in the tree.
  - **The digital twin idea** stays after the hackathon.
- **Kept out of the repo,** from the pasted notes: "lock the $10K", "zero-risk", "25,000+ tests", the 2,417 count, and the MDR class lines.

## 2026-10-30 (late): batch 26.1, and a win grill by GPT-6 Astra on Azure (Ahmed's calls)
- **Batch 26.1:** Ahmed said yes to fixing the Fireworks column.
  - **The diagnosis changed the fix.** The cause wasn't the timeout: with a 180 s limit, Fireworks itself dropped a request at about 62 s. It was the reasoning effort: the open-weight reader sent none, so Spark Open reasoned at its default, `xhigh`.
  - **The fix:** `--reader fireworks` now asks for `low`, as Spark 1.3's reader does. Batch 22's comparison path is unchanged.
  - **How it was built:** Muse planned it, built it in one round and audited it. The Opus supervisor approved. Merged in 0af0e33.
  - **The pre-registered fourth column:** 5 of 8, with 0 harmful.
- **The win grill:** Ahmed asked for a grill of the entry on GPT-6 Astra through his Azure OpenAI resource, Azure for Students (`evidence/grills/win-grill-astra/`). It cost about $0.22 of Azure credit.
  - Its main advice: report full-intake results beside the fine-tune's; audit relation-level provenance patterns; test real voices on invented scripts; show the agent's real state transitions; and build the hero on the clinician's re-photo pause.
  - The film's hero and any recording are Ahmed's calls.

## 2026-10-31: the relation-level provenance audit (Ahmed's yes)
- **What:** the hour's audit that GPT-6 Astra's win grill suggested: ten invented traps, run offline through the product's checks and reconciler, then live on Spark 1.3 and the tuned Glimmer (`evidence/audits/relation-provenance/`). Muse double-checked it read-only and added two traps (`evidence/grills/relation-audit-muse/`).
- **Found:** the checks test values, not relations. Seven of the ten traps would pass if a model got them wrong, and three of those would be false matches: a negated amount in English and in Egyptian Arabic, and micrograms written as milligrams.
- **Live, 20 calls:** no false match. Spark 1.3 got all ten right or failed safe. The tuned Glimmer misread one daily total ("ten milligrams a day, five in the morning and five at night") as a 10 mg intake, which showed a false disagreement.
- **Decision:** no code change before the freeze. A false agreement is the release-gate category, and none was seen. The cheapest guard would be a new multilingual heuristic.
  - After the hackathon, the ten traps become contract tests first.
  - The README states the limit: "each amount value is checked as said in a cited turn; which medicine, tense, negation or unit it belonged to is not checked", with this audit's numbers.
- **Spend:** Meta about $0.10 for 10 Spark calls, plus the Muse grill (about $0.2, in neither ledger). Modal: the per-call estimates, plus one more cold start to reconcile from Modal's billing.

## 2026-10-31, 10:45: the freeze moves, and batch 27 builds the relation checks (Ahmed's call)
- **Ahmed:** "why freezing I still have time you did the same mistake last hackathon and we lost". It was 10:45 on Saturday: 13 hours before our own freeze and three and a half days before submission.
- **The audit's "no code change before the freeze" is reversed.** A gap a judge can name ("the checks prove words occurred, not that the finding follows") gets closed while there is time, through the usual gate.
- **Batch 27:** six word rules on claim amounts (negation, unit, count, another medicine's, past, a split daily total), from the audit's ten traps (SPEC §2, "Relation checks (batch 27)").
  - **Measured before the contract was written,** on a CEO prototype outside the product: all ten traps fail safe; no claim changes in 97 saved live reports; no fully-right reply lost among the committed replies of Spark 1.3, base Glimmer, r1 and r2 on every test split. The word lists were corrected twice on those replies, so that isn't a held-out result.
  - **Muse planned it read-only first** (`evidence/grills/b27-muse-plan/`); five of its points tightened the SPEC.
- **The freeze, proposed:** engine changes until **Tue 3 Nov 12:00 CET**, each through the gate, the supervisor and a fresh clone. The film is captured Mon from the tag of that moment; a later change to what the demo shows means re-capturing that shot Tue morning. After Tue 12:00, only the release-gate fixes. Ahmed confirms or moves it.

## 2026-10-31, 12:33: batch 27 merged (relation checks on claim amounts)
- **What:** after the value check, six word rules decide what each number in a cited turn was said about: negation, another unit, a count, another medicine's amount, a past amount, and a split daily total (SPEC §2, "Relation checks (batch 27)"). Merged in 3d3a30e.
- **How it was built:** the CEO prototyped and measured the rules first; Muse planned read-only, built in three rounds and was audited by a fresh Muse session; the Opus supervisor sent round 2 back with five findings (all taken) and approved round 3 after 32,000 fuzzed replies with no crash and nothing kept that the value check would drop.
- **Checks after the merge** (`evidence/batches/27/checks.md`): the audit's ten traps all fail safe; 0 of 120 saved live claims change; Spark 1.3's, r1's and r2's re-scores are byte-identical; on base Glimmer's committed replies, 52 wrong amounts are no longer shown, with 2 right strengths dropped by the pairing rule.
- **Batch 27.1, after batch 28** (both fail safe): a duration ("for five years") can split a daily total; German "weiß nicht" before a number still negates it.
- **Cost:** Muse $7.29 (plan, three rounds, audit).
- **Also today:** PubMed citations re-checked for the judge session (`evidence/ncbi/`), and a PubChem snapshot test of the INN aliases (35 agree, 0 disagree, 17 unlisted), from the NCBI review session's handoff (Ahmed's call).

## 2026-10-31, 13:31: batch 28 merged (a second label reader after the zoom)
- **What:** with `--second-reader fireworks`, a pack Spark 1.3 still reads as partial or unreadable after its zoom gets one read of the same crop by Muse Spark Open on Fireworks (SPEC §4 step 5b). The second reading counts only when it is readable, for the same region, and keeps everything the first had with the same values (ingredients, strength with its `per`, a known release, known salts). Otherwise the first stands and the pack stays requestable for a re-photo. Merged in 6b114f3, with the live script carried in 957dd3c.
- **How it was built:** the CEO's SPEC, contract and reference build first; Muse planned read-only, built in three rounds, and was audited by a fresh Muse session. The audit and the Opus supervisor found the first SPEC too loose: a second model reading another release, or losing a known one, could make a false `match`. Rounds 2 and 3 closed it; the supervisor approved after a separate coding of the rule agreed on 20,000 random reading pairs, and confirmed the path without a second reader is byte-identical on 1,500 random intakes.
- **A slip, fixed:** the merge script staged `anamnesis/` and `tests/` but not `scripts/`, so `scripts/intake_live.py`'s flag stayed in the batch worktree and `main` failed batch 28's live-script tests for about ten minutes (pushed, no live run used it). Carried in 957dd3c; `batch.sh` now stages `scripts/` and the batch's Muse grills (b0833c2).
- **Cost:** Muse $3.63 (plan, three rounds, audit).
- **Live check:** U1–U8 twice, scored with and without the second reader on the same runs (`evidence/batches/28/live-plan.md`, `score_paired.py`), running now.

## 2026-10-31, 14:26: batch 27.1 merged (durations, "weiß nicht", a dropped amount's tablet count)
- **What:** a number followed by a plural duration word is never an amount; a negation right after German "weiß" doesn't negate the number; and when the relation checks drop a claim's amount, its tablet count goes too unless this claim's own count backs it (SPEC §2, "batch 27.1"). Merged in 63cefc3.
- **Why:** the Opus supervisor's two fail-safe findings on batch 27, and the live probe after it: on trap J the tuned Glimmer wrote a 10 mg intake and five tablets, and the five gave a false `strength_mismatch`.
- **How:** CEO reference first; Muse planned, built in two rounds, and a fresh Muse audit and the supervisor reviewed. The supervisor caught that the SPEC's first wording ("a negation after any word of knowing") re-opened trap A's false `match` ("sicher nicht fünf" is "certainly not five"); round 2 narrowed it to "weiß", made duration words plurals only, and made the tablet-count backing follow rules 1, 4 and 5. Approved on round 2.
- **Measured:** matches the CEO reference on all 1,452 scored replies; none loses a fully-right score against batch 27; 0 of 164 saved live claims change; the ten traps stay safe.
- **Known limit (fails safe):** Arabic puts a singular noun after numbers from 11 («عشرين سنة»), so such a duration can still split a daily amount.
- **Cost:** Muse $2.93.

## 2026-10-31, 15:13: the Meta stop line moves to $80 (Ahmed's call)
- **Ahmed:** "Fix U2 first (~$4)", then "Yes, up to $80" once the full cost was clear: the batch itself, Muse's grills (in neither ledger) and the re-measure of Spark 1.3 with its new prompt on 363 notes bring real Meta use to about $76, past the 50% line ($75).
- **The new line is $80.** Real use then (ledgers $69.7 with this batch's reservation, plus about $2.7 of grills) leaves about $8 for the re-measure, U2's three live runs and anything before submission. The card still pays only past $150.

## 2026-10-31, 15:28: batch 29 merged (one sentence in Spark's claim prompt, for combinations)
- **What:** `MetaClaimExtractor` sends the trained prompt plus "A combination product said with one amount per ingredient, such as 'Augmentin 875 and 125 milligrams', is its strength: one ingredient per amount, in the order said, each named for the ingredient it belongs to." The tuned Glimmer's prompt is unchanged (pinned). Merged in 61ae0e5.
- **Why:** U2 missed in all three of the day's live runs: Spark wrote no amount, or "875 and 125" as one string. Ahmed: "Fix U2 first (~$4)", then the $80 line.
- **How:** a pilot written before the calls (6 of 6 combination calls right, controls unchanged), then the CEO's contract and reference build; Muse built it in one round; a fresh Muse audit found nothing; the Opus supervisor approved and noted that the scorer predates the fix, so the re-measure plan gained a second, labelled view before any call.
- **Cost:** Muse $0.72; the pilot $0.13 of Meta.
- **Running:** the re-measure of Spark 1.3 with the new prompt on 363 notes, and U2 three times live (`evidence/batches/29/remeasure-plan.md`).

## 2026-10-31, 19:02: batch 30 merged (an `inn` naming several ingredients is read as that set)
- **What:** the reconciler reads an `inn` such as "amoxicillin/clavulanic acid" as its set of ingredients, each part with its own salt, in identity, salts and the second read. A catalogue name counts only when it covers all of an `inn`, and an `inn` of more than eight parts is read whole. Merged in 031a87c.
- **Why:** after batch 29, U2's pack side still conflicted, because the label reader writes Augmentin's `inn` as one combined string. This is part of "Fix U2 first".
- **How:**
  - the CEO wrote the SPEC, the contract and a reference build before every round;
  - Muse built it in three rounds;
  - a fresh Muse audit and the Opus supervisor found a salt lost inside a combined `inn` (round 2), then a part hiding an extra ingredient (round 3: a Triveram pack read short matched a Caduet claim);
  - the supervisor approved round 3: nothing moves into `match` over 2,430 targeted cases;
  - the rule also closes a false `match` already on `main` ("paracetamol plus caffeine" beside a paracetamol-only strength).
- **Known limit, in the safe direction:** an `inn` with a salt or strength the alias table lacks ("bisoprolol fumarato") abstains. None of the 132 saved reports has one.
- **Live (pre-registered):** U2 gave 1 of 3 `match` and 0 harmful, against an expected 2 of 3. The pack side was right in 3 of 3. The claim lost its amounts in 2 runs, while 11 direct calls with the same prompt were all right. That is Spark varying between calls (`evidence/batches/30/live-results.md`).
- **Cost:** Muse $2.24 (with the audit); live and diagnostic $0.25. Meta is now $77.95 of the $80 line, with the grills.
- **The engine closes here:** what remains on the Meta line is kept for anything before submission. Only release-gate fixes follow.

## 2026-10-31, 20:55: the public repo's filter scope (the independent checker's README review)
- **Tuesday's filter must cover four things:**
  - the M1 Muse export (personal context);
  - absolute home paths in 40 tracked files (409 hits);
  - the Modal account name in 916454b's history;
  - `CLAUDE.md`:10, which names the build's accounts.
- **Then re-grep** for all of them and the email address before anything is public.
- **Ahmed decides** what the public copy says about the build's accounts (already on his list for Tuesday).

## 2026-10-31, 22:05: the public repo is clean, and it keeps Muse (Ahmed: "the public repo has to clean and has muse since this is meta hackathon")
- **How:** `scripts/public/make_public.sh` builds the public copy from a fresh clone of `main` with `git filter-repo`, keeping every commit, because the history shows Muse's batch pipeline (75 contract commits, 39 Muse batch builds).
- **Muse is kept, cleaned, never dropped:**
  - every grill session stays at its path;
  - all 56 build sessions (194 MB raw, 18 MB cleaned and gzipped) go into `evidence/muse-sessions/`, with an index of tokens and cost per session;
  - the cleaner removes only Muse's encrypted reasoning and the session owner's personal context (Ahmed's own skill list).
- **What the filter removes:**
  - home and scratch paths;
  - the Modal account name;
  - other personal details;
  - SNOMED CT ids: one is still quoted in `tests/contract/test_b24_1_codes.py` and three planning docs on `main`, and the public copy replaces it;
  - the author email, which becomes GitHub noreply.

  The rules stay outside git, in `evidence/raw/public-kit/`.
- **Dry run (31 Oct, 21:50):**
  - 412 commits, and every scan gives 0 (paths, account, any Gmail, personal details, the build's account names, Notion, key-like strings) across all diffs, commit messages and sessions;
  - the only email is the noreply;
  - ruff passes and 2,757 tests pass in the public copy.
- **Pending Ahmed:**
  - The repo name.
  - Going public, on Wed.
