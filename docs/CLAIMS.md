# Claims table

What the video, the README and the submission form may say about Anamnesis, and the evidence behind each claim. **A claim without a row here can't be used.** The script and the README cite rows by number.

Checked on 28 Oct 2026 against `main` at 3b40d5a (batches 1–20). Line numbers are at that commit and get re-checked at the `demo-freeze` tag. Rows 1.13, 4.2, 4.4, 4.9, 4.11–4.13 and 5.1–5.10 were rechecked later that day against `main` at 8800944 (batch 21 merged, and its live rerun) and `batch/22-openweight-reader` at f3e6843 (not merged); their line numbers are at those commits.

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
| 1.13 | ✅ Amounts must be stated | SPEC.md:33–44; `anamnesis/providers/stated.py`; `tests/contract/test_b20_stated_amounts.py` | "A dose a model writes is kept only if the patient said it or the pack prints it." Limit: Spanish number words aren't read, so such a dose is dropped (SPEC.md:44). **Live on 28 Oct, before batch 21, this rule dropped every dose spoken in words.** Spark copied the word ("five") into the amount, and every such case failed safe to `insufficient_information` (`evidence/batches/21/live-before.md`:11–29 on `batch/21-real-media`, 6d41473). Batch 21 asks for digits. Never imply the rule worked live before batch 21. After batch 21, both synthetic notes kept their spoken doses (row 4.12). But Spark still sometimes writes an amount as a word, which is dropped: that caused U5's miss (`live-after.md`:27 on `main`, 8800944). Batch 22 reads a bare number word; until it merges, no claim rests on that. |
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
| 4.2 | ✅ About 3 cents per intake | `evidence/live/2026-10-28/runs.jsonl` on `main` (8800944), the 12 `-b21` rows: 1.6–5.2 cents each, 3.1 on average, $0.368 in all (the ledger's 60 calls for them agree; `live-after.md`:6 prints $0.36897). Before batch 21: 1.6–4.0 cents, 2.7 on average | "About 3 cents per intake (12 live intakes, 28 Oct)." Refresh with the hero's runs at the freeze. |
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
| 4.13 | ⏳ An open-weight label reader, zero-shot | Batch 22 on `batch/22-openweight-reader` (not merged): Muse Spark Open on Fireworks reads the same SAM crops as Spark 1.3, on public photos whose expected readings are written down before any run. It needs the merge, Ahmed's Fireworks key, the run itself and a `decisions.md` entry: the newest still says the benchmark is cut and batch 22 is only the timeline (`decisions.md`:58–59, :127 on `main`) | After the run, only: "On the same crops, the open-weight model read ‹a› of ‹n› labels as they were written down beforehand, and Spark 1.3 read ‹b›", with every miss in the table. Say "comparison", never "benchmark", "beats" or "outperforms". No fine-tuning. No track or bonus wording unless `decisions.md` records Ahmed's call. |

## 5. How it was built
| # | Claim | Evidence | Allowed wording |
|---|---|---|---|
| 5.1 | ✅ Muse Code built the last seven batches | `evidence/batch_log.jsonl`:20–26 on `main` (8800944): batches 16, 17, 18, 19, 19.1, 20 and 21; each `evidence/batches/<n>/` has `builder.md`, `gate.json`, `supervisor.md`, `review.md` | "Muse Code wrote the product code for the last seven batches." Recount at the freeze: batch 22 and later add to N. |
| 5.2 | ✅ What Muse Code wrote | `git blame` at 3b40d5a: every line of `anamnesis/brief.py`, `brief_html.py`, `review.py`, `schema/review.py`, `core/overlap.py` and `providers/stated.py` comes from a Muse batch commit | "The brief, the photo request and the cross-medicine check are code Muse Code wrote." |
| 5.3 | ✅ Its share of the product code | `git blame` at 3b40d5a: 1,576 of 3,887 lines in `anamnesis/` (41%, `__init__.py` files left out) | README line 15: "All product code in `anamnesis/` from batch 16 on was written by Muse Code." Never "all code": the CEO wrote `scripts/` (for example bbccafe, d4eee84, 202ae89, b689014), and Codex and Claude built batches 1–15.5 (README.md:15; `evidence/decisions.md`:70–77). Re-check at the freeze: every commit to `anamnesis/` since batch 16 must be a Muse batch commit. |
| 5.4 | ✅ Claude Code wrote the tests Muse had to pass | CLAUDE.md:6–7; `scripts/batch.sh`:27 (the gate fails a batch that touches `tests/contract/`); every Muse batch has its `evidence/batches/<n>/supervisor.md` (16, 17, 18, 19, 19.1, 20, 21) | "Claude Code wrote the spec and the acceptance tests. Muse Code couldn't edit them, and an independent reviewer checked every batch." Here "every batch" means every Muse batch: batches 13 and 14 have no `supervisor.md`. |
| 5.5 | ✅ Muse Code's usage (estimate, refresh at the freeze) | `evidence/spend/muse_ledger.jsonl` on `main` (8800944): 15 billing entries for 20 Muse sessions (batches 16–21 and one goal probe), 52.1M input and 0.64M output tokens, $14.19 est. With batch 22's two rounds (`batch/22-openweight-reader`, f3e6843): $15.52 est. | "Muse Code's sessions cost about $15.50 of Meta credit so far, priced from its own billing records (28 Oct)." Meta's dashboard is the final word. |
| 5.6 | ✅ Total Meta spend so far (refresh before the final cut) | `evidence/spend/ledger.jsonl` on `main` (8800944): $1.21 over 226 calls. `muse_ledger.jsonl` on `batch/22-openweight-reader` (f3e6843): $15.52 est. | "About $16.74 of the $150 credit so far (28 Oct)." Later batches and runs add to it. |
| 5.7 | ✅ Tests (refresh at the freeze) | `evidence/batches/21/gate.json` on `main`: 1,018 passed; `batch_log.jsonl`:26: 769 contract and 249 unit tests | "1,018 tests run offline, with no keys." Use sparingly: test counts aren't progress (`supervisor-2026-10-27/effect.md`:27). |
| 5.8 | ✅ Batches 1–20 in one day | `git log` (first commit 27 Oct 10:34 CET); `batch_log.jsonl` (batch 1 at 09:38 UTC, batch 20 at 21:30 UTC, 27 Oct) | "Batches 1 to 20 were each specified, built, gated and reviewed in one day, 27 Oct." |
| 5.9 | ⏳ Muse Code at work, on film | The engine's screen recording of one Muse run, with its real duration. Batch 21 and batch 22's two rounds already ran on 28 Oct, so which run gets filmed is still open | Label any sped-up part with its factor, e.g. "8× speed". |
| 5.10 | ⏳ The reviewer caught a bug before it merged | `evidence/batches/22/supervisor.md`:9–21 and `round2-brief.md`:7–9 on `batch/22-openweight-reader` (f3e6843, not merged): in round 1, Muse Code's build read "I take Concor, less than five milligrams" as exactly 5 mg, which reached `match`. `tests/contract/test_b22_round2.py` now pins it (`reference.md`:13–15) | Only once batch 22 merges with an approving review: "In batch 22, the independent reviewer caught the build reading 'less than five milligrams' as exactly five, which would have shown as a match. The contract now pins that case." Never "Muse fixed its own bug" or "self-correcting": the reviewer found it, the CEO pinned it, and Muse's round 2 had to pass the pins. |

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
| An open-weight benchmark (Spark Open, Glimmer, LoRA) and its track | The benchmark was cut on 27 Oct (`evidence/decisions.md`:58–59). Batch 22 brings back only a zero-shot label-reader comparison (row 4.13). No fine-tuning, no ranking, and no track unless `decisions.md` records Ahmed's call |
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
| Briefs from code before batch 21 | `live-before.md`:49–51 | Never captured for the video: a dose spoken in words is dropped on that code. The hero and the pause states are captured from the code their N/10 is measured on, at the `demo-freeze` tag. That code should include batch 22's number-word fix: on batch 21's code Spark still sometimes writes an amount as a word, which is dropped, and the hero's «خمسمية» and «جرام واحد» are spoken in words (`live-after.md`:27, :37) |
