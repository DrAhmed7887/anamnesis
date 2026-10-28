# Claims table

What the video, the README and the submission form may say about Anamnesis, and the evidence behind each claim. **A claim without a row here can't be used.** The script and the README cite rows by number.

Checked on 28 Oct 2026 against `main` at 3b40d5a (batches 1–20). Line numbers are at that commit and get re-checked at the `demo-freeze` tag. Rows 1.13, 4.2, 4.4, 4.9, 4.11–4.13 and 5.1–5.10 were rechecked later that day against `main` at d51bf72 (batches 21 and 22 merged, and batch 21's live rerun); their line numbers are at that commit.

- ✅ **Allowed**, in the wording given or narrower.
- ⏳ **Pending**: the evidence comes from a later run, or from a batch that isn't merged yet. Until it lands, the row can't be used.
- ❌ **Never**: nothing in the repo backs it, or it's false.

## Words we never use
- "autonomous", "self-correcting", "reorients", "plans its own steps": the order is fixed in code and no model chooses an action (SPEC.md:114).
- "25 languages": that is Voice Transcribe's own range. Anamnesis was tested on English and Egyptian Arabic only (SPEC.md:3).
- "validated", "clinically tested", "prevents errors", "saves N minutes", "caught a double dose", "catches it": nothing measured these. The real-media runs are staged tests (docs/DATA_HANDLING.md:44).
- "never shows advice": pack text is quoted as printed and can include directions (SPEC.md:30). Say "adds no advice of its own".
- "open source": there is no LICENSE yet. Say "public" until there is one.
- "MD", or anything that implies current practice. Say "physician (MBBCh)".
- Any statistic or citation without a row here.

## 1. What it does
| # | Claim | Evidence | Allowed wording |
|---|---|---|---|
| 1.1 | ✅ Voice note and photos in, one-page brief out | SPEC.md:3, :144 | "The patient sends a voice note and photos of their medicine packs. The clinician gets a one-page brief." |
| 1.2 | ✅ Three Meta models in the product | README.md:10–13; `evidence/spend/ledger.jsonl`: `muse-voice-transcribe-1.0` 16 calls, `sam-3.1` 38, `muse-spark-1.3` 51 | "Muse Voice Transcribe turns the note into timed turns. SAM 3.1 finds each pack's label. Muse Spark 1.3 picks the medicines out of the transcript and reads each label." |
| 1.3 | ✅ Every finding links to its sources | SPEC.md:163, :169; `anamnesis/brief_html.py`:212–214; `tests/contract/test_b19_brief.py`:275, :359 | "Every finding links back to the audio turn and the image region it came from." |
| 1.4 | ✅ Hear the turn (turn level only) | SPEC.md:8, :168; `brief_html.py`:81–88; `test_b19_brief.py`:349 | "Click a turn and you hear that turn, from its start to its end." Never "the exact words" or "the 5-second clip": Voice Transcribe returns turns, not word timings. Each 27 Oct synthetic note came back as one turn (8.7 s and 12.6 s, `evidence/live/2026-10-27/report_en.json`, `report_ar.json`). |
| 1.5 | ✅ See the region | SPEC.md:166–167; `test_b19_brief.py`:324, :339 | "Click the box and you see the crop the label reader saw." |
| 1.6 | ✅ The reader sees only the crop | SPEC.md:118 (batch 18); `evidence/live/2026-10-27/zoom_after/summary.md` | "The label reader only ever sees the cropped pack, so a reading can't come from another pack." If a number is used: "8 of 8 crop reads correct, on synthetic phone-style photos (27 Oct)". |
| 1.7 | ✅ Disagreements first, side by side | SPEC.md:146–161; `test_b19_brief.py`:262, :285 | "Disagreements come first, with the patient's words and the pack side by side." |
| 1.8 | ✅ Fixed text, no advice of its own | SPEC.md:64; `anamnesis/schema/templates.py`:5–17, :32–38; `test_b19_brief.py`:377 | "Every sentence Anamnesis adds is fixed text. It adds no advice of its own, and pack text is quoted as printed." |
| 1.9 | ✅ Two brand names, one medicine | SPEC.md:171–178, :198; `anamnesis/core/overlap.py`; `templates.py`:40–43; `test_b19_brief.py`:560 | "Panadol and Gelocatil are two brand names for one medicine. Anamnesis notes that both contain paracetamol, and that concurrent use is unconfirmed." |
| 1.10 | ✅ Two medicines in one class | SPEC.md:176; `templates.py`:44–47; `test_b19_brief.py`:313 | "It also notes two medicines from one class, beta-blockers. Concurrent use is unconfirmed." Only one class is curated, and interactions aren't checked (`templates.py`:36–37). |
| 1.11 | ✅ A pack never shows use | SPEC.md:171; `test_b19_brief.py`:517 | "Only what the patient says counts as use. A photo of a pack never does." |
| 1.12 | ✅ Nothing is silent | SPEC.md:181–190; `test_b19_brief.py`:404 | "If a photo shows no pack, the brief says so." |
| 1.13 | ✅ Amounts must be stated | SPEC.md:32–61; `anamnesis/providers/stated.py`; `tests/contract/test_b20_stated_amounts.py` | "A dose a model writes is kept only if the patient said it or the pack prints it." Limit: Spanish number words aren't read, so such a dose is dropped (SPEC.md:61). **Live on 28 Oct, before batch 21, this rule dropped every dose spoken in words.** Spark copied the word ("five") into the amount, and every such case failed safe to `insufficient_information` (`evidence/batches/21/live-before.md`:11–29 on `batch/21-real-media`, 6d41473). Batch 21 asks for digits. Never imply the rule worked live before batch 21. After batch 21, both synthetic notes kept their spoken doses (row 4.12). Spark still sometimes writes an amount as a word. On batch 21's code that word was dropped, and the engine traces U5's miss to it (`live-after.md`:27, :37). Since batch 22 (38dd1f4), one bare word is read as its value and must still be stated; with a sign, a comparator, punctuation or tashkeel it never parses, so "less than five" is not 5 (SPEC.md:24). The digits prompt stays the main path. |
| 1.14 | ✅ The brief is one static page | SPEC.md:144; `test_b19_brief.py`:359, :373, :586 | "The brief is one static page. It calls no model, and it refuses media the report wasn't made from." |
| 1.15 | ✅ Not a medical device | README.md:19; `templates.py`:33 | "Anamnesis is not a medical device and gives no medical advice." |
| 1.16 | ✅ Code compares, not a model | SPEC.md:77–95, :114; `anamnesis/core/reconcile.py`:325, :421; `anamnesis/agent/loop.py`:165 | "Then plain code compares the two sides. No model decides a finding." |
| 1.17 | ✅ An unreadable label is reported, never guessed | SPEC.md:57, :79; `templates.py`:14; `tests/contract/test_b14_agent_loop.py`:139; `tests/contract/test_b2_reconcile.py`:111 | "When a label can't be read, Anamnesis doesn't guess. It says so." |
| 1.18 | ⏳ One medicine, a different brand name in another country | The batch 21 manifest: each box's brand, strength and country | "The same medicine can carry another brand name in another country." Only once the manifest records both countries. |

## 2. The clinician's pause: one new photo
| # | Claim | Evidence | Allowed wording |
|---|---|---|---|
| 2.1 | ✅ The clinician can ask for one new photo (tested offline) | SPEC.md:203–225; `anamnesis/review.py`:25, :42, :88; `tests/contract/test_b20_review.py`:236, :336 | "If a label can't be read, the clinician can ask the patient for one new photo. Only that photo is processed, and the brief updates." Also "the run pauses for a person, then resumes" (SPEC.md:203). |
| 2.2 | ✅ Nothing is final until approved | SPEC.md:226, :229; `templates.py`:122–124; `review.py`:153; `test_b20_review.py`:465, :500 | "The brief stays a draft until the clinician approves it." |
| 2.3 | ✅ Who decides | SPEC.md:114, :203; `evidence/grills/supervisor-2026-10-27/effect.md`:13 | "The code fixes the order. The clinician decides the pause. No model chooses an action." This is the framing for the agentic track: human in the loop. |
| 2.4 | ✅ The message to the patient is fixed text | `templates.py`:128–130; `test_b20_review.py`:325 | Quote it as it is. |
| 2.5 | ⏳ The pause, live, on a real photo | Batch 21: the unreadable shot, its re-photo, their saved reports and brief | Until it lands: "built and tested offline", never "shown live". |
| 2.6 | ✅ In the demo, the developer plays the clinician | SPEC.md:213–226 (the review is a set of functions; there is no clinician app); the demo script for case R2 | Say it: "Today, that request is one function call, and I play the clinician." On screen while the review states show: "Staged demo: the developer plays the clinician. The request is one function call; there is no clinician app yet." |

## 3. Safety, privacy and spend
| # | Claim | Evidence | Allowed wording |
|---|---|---|---|
| 3.1 | ✅ Photos are cleaned first | SPEC.md:115; `anamnesis/agent/media.py`:35; `tests/contract/test_b15_5_zoom.py`:76, :84 | "Before any model sees a photo, Anamnesis turns it upright and strips its metadata, GPS included." |
| 3.2 | ✅ A wrong-pack bug found and fixed | `evidence/decisions.md`:64–67; `evidence/live/2026-10-27/zoom_before/summary.md` (2 wrong), `zoom_after/summary.md` (8 of 8 right) | "On sideways phone-style test photos, 2 of 3 labels were first read from the wrong pack. Turning every photo upright first fixed it." The photos were drawn by a script (`scripts/make_hard_media.sh`:1–5). |
| 3.3 | ✅ No patient data | `docs/DATA_HANDLING.md`:5–19; README.md:19 | Before batch 21: "All data is synthetic." After it: "No patient data. The packs are real, the history is invented, and the voice is the developer's own." |
| 3.4 | ✅ Standard models in the product | `ledger.jsonl`: no `*-contributor` id among its 105 calls; DATA_HANDLING.md:31 | "Every product call used Meta's standard models." Never "never used contributor mode": the M1 grill did (`evidence/decisions.md`:41–42). |
| 3.5 | ✅ Every call logged and capped | SPEC.md:121–128; `anamnesis/providers/spend.py`:20, :78; `tests/contract/test_b14_agent_loop.py`:156, :245 | "Every model call is logged with its cost, and each intake has a call cap and a dollar cap." Never "cryptographic" or "audit trail". |
| 3.6 | ❌ The 2× zoom as a demo beat | `evidence/grills/pre-b16/effect.md`:13, :22 (Z4, Z9) | The zoom never fired live. It gets a row only if a batch 21 photo triggers it and the zoomed reading is right. |

## 4. Results
| # | Claim | Evidence | Allowed wording |
|---|---|---|---|
| 4.1 | ✅ Both languages right, live, on synthetic notes: 27 Oct only, and only next to the regression | `evidence/decisions.md`:45–49; `evidence/live/2026-10-27/report_en.json`, `report_ar.json`. Regression: `evidence/live/2026-10-28/report_en.json`, `report_ar.json` and `live-before.md`:11–21 on `batch/21-real-media` | "On 27 Oct, with that day's code, all three findings came out right on both synthetic notes." Never on its own: on 28 Oct, `main` 3b40d5a turned the Concor `match` into `insufficient_information` in both languages, and the Arabic Beloc-Zok finding too, because of the batch 20 prompt (row 1.13). Prefer rows 4.11 and 4.12. |
| 4.2 | ✅ About 3 cents per intake | `evidence/live/2026-10-28/runs.jsonl` on `main` (8800944), the 12 `-b21` rows: 1.6–5.2 cents each, 3.1 on average, $0.368 in all (the ledger's 60 calls agree, and so does `live-after.md`:6 since its correction in d51bf72). Before batch 21: 1.6–4.0 cents, 2.7 on average | "About 3 cents per intake (12 live intakes, 28 Oct)." Refresh with the hero's runs at the freeze. |
| 4.3 | ✅ Arabic spellings vary | `evidence/decisions.md`:31, :36, :47 | "The same Arabic recording came back in three different spellings across runs. Curated Arabic brand names cover the ones seen so far." |
| 4.4 | ✅ for the public photos, ⏳ for Ahmed's cases: expected results first | U1–U10: `manifest.md` committed in 8b993ff at 08:00 UTC on 28 Oct. The ledger's first call that day is at 08:01 UTC, and none falls between 27 Oct 13:31 UTC and then (`evidence/spend/ledger.jsonl` on `main`). The U rows are unchanged on `main`. Ahmed's cases (R1–R8): not run yet | "The expected results were committed before the first run", with the commit. For R1–R8, only once their run is logged after the manifest commit. |
| 4.5 | ⏳ The hero case, N of 10 | 10 live runs of the hero (R1b or R1 in the batch 21 manifest) on the `demo-freeze` code, `evidence/live/<date>/` | "N of 10 runs gave the expected brief." N exactly as measured, every miss listed. |
| 4.6 | ⏳ The real-case table | Batch 21 reports | "Staged tests: real packaging, a fictional history, the developer's own voice; not a validation." Every miss stays in the table. |
| 4.7 | ⏳ A real human voice | Batch 21 | Until then: "tested on synthetic voices only" (SPEC.md:3). |
| 4.8 | ✅ No outside usability check | Not run: cut from the 28 Oct plan | "No outside usability check was done." |
| 4.9 | ✅ How long one intake takes (refresh at the freeze) | `runs.jsonl` on `main` (8800944), the 12 `-b21` rows: 17–49 s from start to finish; claim requests 8.3–26.4 s against the 30 s timeout, U10's the closest (`live-after.md`:8). Before batch 21: 14–36 s | "One intake took 17 to 49 seconds (12 live intakes, 28 Oct)." Replace with the hero's 10 runs at the freeze. |
| 4.10 | ⏳ The hero's disagreement | Case R1b (V1b + P1) in the batch 21 manifest: Gelocatil said as 650 mg against a 1 g box, expected `strength_mismatch` | "The patient said six hundred and fifty milligrams. The pack says one gram." Only if V1b is recorded and R1b comes out as pre-registered. |
| 4.11 | ✅ The same pre-registered cases, before and after batch 21 | Before: `live-before.md`:31–47 and `evidence/live/2026-10-28/report_U1.json`…`report_U10.json` on `batch/21-real-media` (6d41473). After: `live-after.md`:20–34 and `report_U1-b21.json`…`report_U10-b21.json` on `main` (8800944). The cases were pre-registered in `manifest.md` (8b993ff, row 4.4) and rerun unchanged (`live-after.md`:5) | "On the same ten pre-registered public-photo cases, with the same expected results, the code got 1 right before batch 21 and 3 after it. Neither run showed a false match, or a wrong strength or ingredient as fact." Always name U5 in the README, in both columns: the patient's Norvasc is paired with the 10 mg box instead of the 5 mg one, and the brief says it can't confirm agreement. Never "fixed": it is still a miss after batch 21 (`live-after.md`:27, :34). U7 stays a miss in both tables: its key was the CEO's error and is kept as written. A rerun on later code gets its own column and never replaces these two. Never show the U photos or the U voice notes (§8). |
| 4.12 | ✅ The two synthetic notes, before and after batch 21 | `live-after.md`:10–18 on `main` (8800944); `evidence/live/2026-10-28/report_en-b21.json`, `report_ar-b21.json` and their `runs.jsonl` rows. Before: `report_en.json`, `report_ar.json` (6d41473) | "On two synthetic notes, one English and one Egyptian Arabic, 3 of 6 findings came out as expected before batch 21, and 6 of 6 after it." The notes are `say` voices: results as text only (§8). |
| 4.13 | ⏳ An open-weight label reader, zero-shot | `evidence/decisions.md`:138–143 on `main` (Ahmed's call): `OpenWeightLabelReader` (batch 22, 38dd1f4) reads the same SAM 3.1 crops as Spark 1.3, with Spark 1.3's prompt, schema and parser, on 39 public photos (30 Cairo University phone photos under CC BY 4.0, and 9 Wikimedia Commons photos). The expected readings and scoring rules were committed before any reader ran (c1b5b6e: `evidence/batches/22/preregistration-notes.md`, `preregistration.json`, `preregistration-gemini.json`). Not run yet: the Baseten key was refused (HTTP 403) and there is no Fireworks key (the engine, 28 Oct) | Only after the run: "A zero-shot comparison on 39 public photos, scored by rules committed beforehand: on the same crops, Muse Spark Open read ‹a› correctly and Spark 1.3 read ‹b›", with every miss published per photo and reader, and harmful misses named. Say "descriptive comparison, n = 39", never "benchmark" or "beats". No model was trained. Prize-track wording waits for Ahmed (`decisions.md`:142). |

## 5. How it was built
| # | Claim | Evidence | Allowed wording |
|---|---|---|---|
| 5.1 | ✅ Muse Code built the last eight batches | `evidence/batch_log.jsonl`:20–27 on `main`: batches 16, 17, 18, 19, 19.1, 20, 21 and 22; each `evidence/batches/<n>/` has `builder.md`, `gate.json`, `supervisor.md`, `review.md` | "Muse Code wrote the product code for the last eight batches." Recount at the freeze: batch 23 and later add to N. |
| 5.2 | ✅ What Muse Code wrote | `git blame` at 3b40d5a: every line of `anamnesis/brief.py`, `brief_html.py`, `review.py`, `schema/review.py`, `core/overlap.py` and `providers/stated.py` comes from a Muse batch commit | "The brief, the photo request and the cross-medicine check are code Muse Code wrote." |
| 5.3 | ✅ Its share of the product code | `git blame` at 3b40d5a: 1,576 of 3,887 lines in `anamnesis/` (41%, `__init__.py` files left out) | README line 15: "All product code in `anamnesis/` from batch 16 on was written by Muse Code." Never "all code": the CEO wrote `scripts/` (for example bbccafe, d4eee84, 202ae89, b689014), and Codex and Claude built batches 1–15.5 (README.md:15; `evidence/decisions.md`:70–77). Re-check at the freeze: every commit to `anamnesis/` since batch 16 must be a Muse batch commit. |
| 5.4 | ✅ Claude Code wrote the tests Muse had to pass | CLAUDE.md:6–7; `scripts/batch.sh`:27 (the gate fails a batch that touches `tests/contract/`); every Muse batch has its `evidence/batches/<n>/supervisor.md` (16, 17, 18, 19, 19.1, 20, 21, 22) | "Claude Code wrote the spec and the acceptance tests. Muse Code couldn't edit them, and an independent reviewer checked every batch." Here "every batch" means every Muse batch: batches 13 and 14 have no `supervisor.md`. |
| 5.5 | ✅ Muse Code's usage (estimate, refresh at the freeze) | `evidence/spend/muse_ledger.jsonl` on `main` (d51bf72): 17 billing entries for 22 Muse sessions (batches 16–22 and one goal probe), 56.7M input and 0.70M output tokens, $15.52 est. | "Muse Code's sessions cost about $15.50 of Meta credit so far, priced from its own billing records (28 Oct)." Meta's dashboard is the final word. |
| 5.6 | ✅ Total Meta spend so far (refresh before the final cut) | `evidence/spend/ledger.jsonl` on `main` (d51bf72): $1.21 over 226 calls; the engine's checkout holds 2 later calls, not yet committed, that make it $1.22. `muse_ledger.jsonl` on `main`: $15.52 est. Open-weight reads are billed to Fireworks or Baseten and kept out of this total (a81c9d1) | "About $16.75 of the $150 credit so far (28 Oct)." Re-cite once those 2 calls are committed. Later batches and runs add to it. |
| 5.7 | ✅ Tests (refresh at the freeze) | `evidence/batches/22/gate.json` on `main`: 1,122 passed; `batch_log.jsonl`:27: 847 contract and 275 unit tests | "1,122 tests run offline, with no keys." Use sparingly: test counts aren't progress (`supervisor-2026-10-27/effect.md`:27). |
| 5.8 | ✅ Batches 1–20 in one day | `git log` (first commit 27 Oct 10:34 CET); `batch_log.jsonl` (batch 1 at 09:38 UTC, batch 20 at 21:30 UTC, 27 Oct) | "Batches 1 to 20 were each specified, built, gated and reviewed in one day, 27 Oct." |
| 5.9 | ⏳ Muse Code at work, on film | Nothing filmed yet: batch 21 and batch 22's two rounds ran headless, logging to files (the engine, 28 Oct). The next Muse run is batch 23 on Fri, if it isn't cut | Label any sped-up part with its factor, e.g. "8× speed". Without a recording, scene 6 shows stills of the evidence folder, and nothing calls them footage. |
| 5.10 | ✅ The reviewer caught a spec error before the merge | `evidence/batches/22/supervisor.md`:3–21 (round 1, finding 1) and :53–55 (round 2: APPROVE); `review.md`:15, :19–20 on `main` (merged in 38dd1f4) | "In batch 22, the independent reviewer caught a spec error: as briefed, 'less than five milligrams' would have been read as exactly five and shown as a match. The contract now pins that case." Never "the builder's bug", "Muse fixed its own bug" or "self-correcting": the error came from the CEO's brief and Muse built it exactly as written (`review.md`:20). The reviewer found it, and round 2 had to pass 40 new contract cases (`review.md`:19). |

## 6. People and sources
| # | Claim | Evidence | Allowed wording |
|---|---|---|---|
| 6.1 | ✅ The builder | Ahmed's own wording | "Ahmed Zayed, physician (MBBCh)." Nothing that implies current practice: no "MD", coat, stethoscope or ward. |
| 6.2 | ✅ The Lancet study | Brodeur PG et al. "Conversational diagnostic artificial intelligence in ambulatory primary care: a prospective feasibility study." *Lancet* 2026;408(10565):1732–44, abstract read 28 Oct 2026. The text-only chat is from Google Research's post on the study (11 Mar 2026, updated 8 Oct 2026), read 28 Oct | "In a Lancet feasibility study, primary care doctors who read an AI pre-visit chat said it helped them prepare in 33 of 44 cases. But a chat can't see the pack." Lower third: "Brodeur et al., The Lancet 2026 · single-centre feasibility study · text-only chat". Never "75% of visits": the 44 are the cases where the doctor read the transcript and answered the survey. Never "proved", and never "AMIE can't read images": a multimodal version exists, tested in simulated consults. |
| 6.3 | ❌ Any other citation | None checked | Each needs a check against its source and a row first. |

## 7. Never: claims from the old video playbook
The video playbook (planning notes outside this repo) was written before most of the product existed. These claims in it have nothing behind them.

| Playbook claim | Why it can't be used |
|---|---|
| A React web app with drag-and-drop upload | There is no app or server. The product's page is one static HTML brief (SPEC.md:144) |
| A patient guardrail chat with "0.0% medical advice violations" across four languages | There is no patient chat and no such measurement. The advice check is a regression check, not the safety boundary (SPEC.md:64) |
| The agent "autonomously rotates, re-crops and re-reads" (`reorient_and_zoom_crop`) | Fixed code turns photos upright from their EXIF tag before any model sees them (SPEC.md:115). The zoom never fired live (row 3.6) |
| German and Spanish audio, paper discharge summaries | Not tested. Spanish number words fail closed (SPEC.md:44) |
| Metoprolol 25 mg against a 100 mg pack as the demo case | Not a live case. The hero is Panadol + Gelocatil (`evidence/grills/pre-b16/effect.md`:38) |
| A "Muse Code append-only audit log pattern", a "cryptographic audit trail" | Neither exists. There is a plain spend ledger (SPEC.md:128) |
| An open-weight benchmark (Spark Open, Glimmer, LoRA) and its track | The benchmark was cut on 27 Oct (`evidence/decisions.md`:58–59). Ahmed brought back only a zero-shot label-reader comparison, as batch 22 (`decisions.md`:138–143; row 4.13). No fine-tuning, no ranking, and no track wording until Ahmed decides |
| An FHIR R4 export | Not built |
| A live demo URL | None exists. A hosted sample brief may come on Tue; it then gets a row |
| "Dr. Ahmed Zayed, MD", a clinical coat | See row 6.1 |
| "The exact 5-second utterance", word-level sync | Turn level only (row 1.4) |
| "Simulate instant streaming" | Simulate nothing. Label every sped-up segment |
| "A rushed doctor misses it. Anamnesis catches it." | Unmeasured. Say "flags it for the clinician" |
| Statistics about judges ("over 65% skip…") | No source |
| Prize amounts | Not needed, and the playbook's two figures disagree |
| "Bi-directionally grounded", "visual chain of thought", "breakthrough" | Vague or untrue. Use rows 1.3–1.6 |

## 8. Media and licences
| Item | Evidence | Rule |
|---|---|---|
| macOS system voices (`say`) | The macOS licence on the build Mac (macOS 27.0.1, Setup Assistant's `OSXSoftwareLicense`, "Voices" section): personal, non-commercial use only, with no publishing or public sharing | No `say` audio in any published file, the video and the hosted brief included. The synthetic voice notes of 27 Oct are `say` voices, so they never play in the video, and the hosted sample brief goes up without audio. A `say` scratch voiceover can exist only in local drafts, if Ahmed agrees |
| Background music | No licence checked | No music unless its licence is checked and given a row |
| Ahmed's voice and the real pack photos | DATA_HANDLING.md:41 | The final video needs Ahmed's explicit yes for that file, and so does any hosted brief that uses them |
| Public pack photos U1–U10 | `manifest.md`:48–74 on `batch/21-real-media`: U1–U3 CC0 or public domain, U4–U8 CC BY or CC BY-SA, U9–U10 from DailyMed with no licence, private scoring only | Not in the video or a hosted brief: the results go on screen as text. U9–U10 are never shown, committed or recorded. A Commons photo would need its credit and licence checked first, and then a row here |
| The U voice notes | `manifest.md`:54: macOS `say` (Samantha) | Internal tests only. Never in the video or a hosted brief |
| The 39 comparison photos | `decisions.md`:141; `evidence/batches/22/preregistration-notes.md`:3: 30 Cairo University phone photos (CC BY 4.0) and 9 Wikimedia Commons photos | Not in the video or a hosted brief unless each photo's credit and licence are checked and given a row here. Results go on screen as text |
| Briefs from code before batch 21 | `live-before.md`:49–51 | Never captured for the video: a dose spoken in words is dropped on that code. The hero and the pause states are captured from the code their N/10 is measured on, at the `demo-freeze` tag. That code is `main` after batch 22 (38dd1f4, the engine, 28 Oct). On batch 21's code Spark still sometimes wrote an amount as a word, which was dropped, and the hero's «خمسمية» and «جرام واحد» are spoken in words (`live-after.md`:27, :37). Batch 22 reads one bare word as a safety net; the digits prompt stays the main path (SPEC.md:24) |
