## Ranked missing items

### 1. A brief a clinician can actually scan and verify — **3 hours**
- **What:** A clinician-facing page, rather than a validated report object. A GP might use a source-linked discrepancy brief before a visit; this package does not yet demonstrate that workflow. It is not a reconciled medication list.
- **Why it matters — clinic/judges:** IDs and generic findings still leave the clinician to reconstruct the case. “Reported intake differs” is less useful than seeing **patient: 50 mg twice daily | pack: 100 mg per tablet**, alongside the evidence.
- **Evidence:** `anamnesis/schema/report.py` defines the bundle; `findings_ar.json` shows IDs and template text. No rendered brief or evidence-navigation interaction is demonstrated.
- **Smallest fix:** Build one local, printable HTML view: discrepancies first; patient statement and pack details side by side; reported regimen/status; clickable source-image overlay and turn-level audio playback. Clearly label missing sources. Narrow the canonical `match` wording to **“The compared identity and strength details agree”**, where applicable, rather than implying agreement on the whole medication history. Keep all generated clinical prose templated.

### 2. Cross-medication overlap — already visible in the showcase — **2 hours**
- **What:** Duplicate active ingredients and possible same-class duplication across the intake, not merely agreement between one claim and one pack.
- **Why it matters — clinic/safety:** **This is the absence a clinical judge is likely to notice first:** the showcased patient reports Concor/bisoprolol and Beloc-Zok/metoprolol together—two beta blockers. That may have an explanation; the system should neither diagnose an error nor recommend stopping anything. But treating each pair independently misses an obvious clarification opportunity.
- **Evidence:** `voice_ar.json` reports both as current use. `SPEC.md` §3 only defines pairwise findings and leftovers; duplicate INNs are prohibited *inside a strength*, not assessed across medications.
- **Smallest fix:** Add a separate, templated cross-medication observation: **“Two medications reported as current belong to the same curated class; concurrent use is unconfirmed.”** Include both source references. Detect identical active ingredients across distinct reported products, including combination products; demonstrate same-class overlap only through a tiny, explicit curated mapping. Repeated photos alone must not imply duplicate use.

### 3. The missing distinction between pack contents, prescribed directions and actual use — **2 hours**
- **What:** Frequency, timing, PRN use, missed doses and contradictory patient statements are not meaningfully reconciled. There is no prescribed-list comparator.
- **Why it matters — clinic/safety:** A manufacturer’s box usually cannot confirm “twice daily,” “only when needed” or “I take it at night.” Agreement on tablet strength says nothing about adherence or prescribed frequency. Supply mismatch also needs quantity, acquisition date and reported consumption—not just a photographed box.
- **Evidence:** `DoseRegimen` has frequency and PRN fields, but `PackObservation` has no dispensing directions; the decision order does not compare regimens. Timing, adherence and supply history are absent.
- **Smallest fix:** Display existing regimen fields and source-linked verbatim usage statements. Add **“Prescribed directions, timing, adherence and supply consistency not assessed”** to the brief. Preserve contradictory statements without silently choosing one. Do not manufacture a frequency discrepancy from a pack strength. Defer dispensing-label or medication-list comparison.

### 4. An explicit account of what was not captured — **2 hours**
- **What:** Coverage of OTC medicines, herbal products, supplements, inhalers, injections, patches, eye drops and medication devices—and visibility when inputs were omitted.
- **Why it matters — clinic/safety:** Patients often exclude non-prescription products from “my medicines.” A pill-box-oriented pipeline can also quietly miss precisely those products. “No discrepancy found” must not look like “all medicines checked.”
- **Evidence:** The catalogue is eight synthetic entries in the M1 review. `SPEC.md` restricts supported forms and defers liquids. `loop.py` reads only the top three regions per image; failed segmentation can yield no observation at all.
- **Smallest fix:** Add a fixed intake prompt explicitly naming OTC/herbal products and non-tablet medicines. Preserve unsupported mentions as unverified, source-linked entries rather than dropping them. Show **images submitted / images with readable observations / detected regions not read / processing interrupted**. State that detection counts do not establish that every product was found. Present an input with no recovered evidence as incomplete, not clear.

### 5. A realistic, held-out input trial — **4 hours**
- **What:** Evidence beyond short scripted speech and generated packaging.
- **Why it matters — judges/safety:** The first ordinary input may contain glare, tiny curved text, a box back, an unboxed blister or five overlapping packs. Long speech introduces corrections, historical medicines, another household member’s medicines and uncertain names. Unsupported languages can transcribe plausibly while resolving incorrectly.
- **Evidence:** `README.md` says all data are synthetic. `decisions.md` records SAM finding packs only through “label.” The live Arabic note is 12.62 seconds and one turn. `loop.py` stops at the first successful segmentation concept, caps regions and shares a 12-call budget.
- **Smallest fix:** Run six fixed, held-out staged cases using real phone captures of packaging and fictional medication histories: glare/rotation; blister-only; multiple packs; a non-tablet product; unfamiliar-script packaging; and a 60–90-second rambling, code-switched note with a correction. Manually annotate expected mentions and readable labels before running. Record omissions, wrong extractions, abstentions, latency and cost. Patch demonstrated shipping blockers only; visibly abstain elsewhere. Describe these honestly as staged real-media tests, not clinical validation.

### 6. Evidence that the brief saves clinician work rather than creating it — **2 hours**
- **What:** An observed use test and a strategy for low-value clarification prompts.
- **Why it matters — clinic/judges:** A stopped Panadol with no accompanying pack may be an ordinary historical statement, not an important unresolved medication. If every such item competes with a genuine disagreement, clinicians will stop scanning.
- **Evidence:** `findings_ar.json` flags stopped Panadol as `missing_modality`; `templates.py` asks whether it is currently used despite the discontinuation statement. The package has reviewer verdicts but no GP/pharmacist task evaluation.
- **Smallest fix:** Ask one GP and one pharmacist outside the build to review two staged cases, first from raw inputs and then from the brief, with order alternated. Measure time to identify unresolved facts, missed facts and unnecessary questions. Separate **source disagreements**, **incomplete evidence** and **historical statements**, without suppressing source data or assigning clinical risk. Report these as usability observations, not efficacy evidence.

### 7. A judging story based on demonstrated behavior, not model count — **2 hours**
- **What:** A visible reason this is a distinctive physician-built intake tool, and evidence that segmentation/refinement contributes.
- **Why it matters — judges:** Indie judging is not a production-robustness contest. The weak point is neither lack of APIs nor lack of open weights: it is whether the models produce a useful, demonstrable interaction. The fixed-order loop is not model-directed planning.
- **Evidence:** `SPEC.md` §4 explicitly says no model chooses actions. M3 leaves an open-weight benchmark pending. Muse Code’s contribution is documented development review, not runtime clinical intelligence.
- **Smallest fix:** Show Voice Transcribe handling the bilingual history, SAM locating the evidence, and Spark extracting grounded facts. Compare initial versus zoomed reading on one genuinely difficult staged image; if zoom does not help, say so. Credit Muse Code as a development tool. Do not claim autonomous reasoning or chase the agentic bonus.
  
  **First 20 seconds:**  
  **0–5:** A short Egyptian Arabic/English medication statement beside the phone photo.  
  **5–12:** The finished brief exposes one actual disagreement or concurrent-use uncertainty, with the two source values visible.  
  **12–20:** Click the finding to hear the turn and see the highlighted label. Show **“Reports disagreements; gives no treatment advice.”**  
  Do not open with architecture, reviewer counts or a terminal.

### 8. A release gate that closes instead of generating another milestone — **2 hours**
- **What:** A bounded exit from review and hardening.
- **Why it matters — process/judges:** Yes: the current balance is over-hardening and under-shipping. Seven hardening batches are not inherently excessive, but 400 tests alongside no demonstrated clinician page, no held-out realistic trial and no live bounded-loop result is the wrong allocation now.
- **Evidence:** Batch log; M2’s repeated HOLD rounds; M3’s current HOLD and planned B15; pending M3 grill and open-weight benchmark.
- **Smallest fix:** Timebox the already accepted B15 work and one targeted verification to two hours. Close the current HOLD before live-loop spending. If it cannot close, reduce the release surface rather than launching another broad review cycle. Thereafter, block release only for reproduced harmful false agreement, wrong provenance, advice leakage, spend-cap failure or failure of the frozen demo path.

### 9. A concrete privacy boundary for the first realistic trial — **1 hour**
- **What:** Rules for what may enter hosted models and retained artifacts.
- **Why it matters — safety/clinic:** Real packaging photos can contain patient names and dispensing identifiers; rambling recordings can contain identifying histories. “Synthetic data” is not an operational safeguard once realistic testing begins.
- **Evidence:** `README.md` promises synthetic data; `SPEC.md` retains transcripts and input-derived artifacts. `decisions.md` distinguishes contributor-mode training exposure for Muse Code, but no patient-facing handling policy is shown.
- **Smallest fix:** Keep submission and testing fictional and de-identified; exclude pharmacy identifiers, personal conversations and real patient histories. State what leaves the laptop and what is retained. Keep raw media out of git, provide a local deletion path, and make no confidentiality or compliance claims not supported by provider terms.

## Ordered next-5 plan

1. **Close the existing HOLD and freeze scope — 2 hours.**  
   Complete the already accepted release-blocking work; run targeted checks. Inventory adapter and off-ledger Meta spend before further calls. Establish one remaining-spend ceiling covering both.

2. **Build the clinician brief and the two clinical boundaries — 7 hours.**  
   Implement the source-linked view, cross-medication overlap observation, and explicit regimen/comparator limitations. Use templated observations and factual questions only.

3. **Test realistic inputs and expose incomplete coverage — 6 hours.**  
   Add the inclusive intake prompt and completeness display; execute the six held-out staged cases. Use cached artifacts for development and cap this live-test tranche at **$1**, only if the total budget permits.

4. **Observe two clinician reviews and lock data handling — 3 hours.**  
   Run the GP/pharmacist tasks, make only the highest-impact presentation changes, and finalize the synthetic/de-identified input policy.

5. **Record, package and submit — 2 hours.**  
   Record the three-minute demo, include a clearly labelled replay fallback and the small results table, document supported inputs and failures, and verify a clean offline run. Target submission **Wed 4 Nov, 20:00 CET**, ahead of **Thu 5 Nov, 03:00 CET**.

**Planned work: 20 focused hours. Reserve another 4 hours for integration and submission failures—not extra features.**

## Stop doing

- Broad multi-reviewer grills after every change; keep one release review and targeted reproduction of genuine blockers.
- Expanding salt, alias and formulation coverage without a failure in the frozen supported cases.
- Treating test totals, batch counts, reviewer attribution and process tooling as submission progress.

## Cut

- Open-weight hosting and benchmarking; do not chase that bonus on this hardware, budget and schedule.
- Barcode/GS1 resolution, external drug databases and catalogue expansion.
- General interaction checking, comprehensive therapeutic-duplication detection and any treatment recommendation.
- Full prescribed-list reconciliation, supply arithmetic, comprehensive liquid/device interpretation and multilingual coverage beyond the tested scope.
- Production deployment features: accounts, EHR integration, dashboards and elaborate infrastructure. Ship a local demonstrator with an auditable brief.
