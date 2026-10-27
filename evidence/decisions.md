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
