### A. Says more than the cited row's allowed wording or evidence, or widens its scope

**1. Severity: MEDIUM**
* **Sentence:** `| U1 Concor, Russia (Cyrillic) | match | insufficient_information | match ✓ |` (and the remaining 9 rows of the U1–U10 table, plus: `- **U5 is still a miss.** The patient's Norvasc is paired with the 10 mg box instead of the 5 mg one, and the brief says it can't confirm agreement. After batch 21 it is a tie between the two boxes, because both amounts were dropped. [4.11]`)
* **Row:** [4.11] (and Pending row [1.18])
* **Why:** Row 4.11's evidence and allowed wording cover only the 1-of-10 and 3-of-10 totals, the "no false match" line, U5's pairing, and U7's key error. It does not evidence the per-case brands, countries, scripts, specific statuses (`unresolved_name`, `unreadable_source`, `intake_differs_from_unit_strength`), or failure causes (e.g., "the reader transcribed the manufacturer block", "SAM finds no pack in flat label artwork", or U5 being a tie because both amounts were dropped). Furthermore, listing each box's country (Russia, Belgium, Australia, Finland, Israel, China) bypasses row 1.18, which is `⏳ Pending` ("The batch 21 manifest: each box's brand, strength and country... Only once the manifest records both countries"), something the README's own HTML comment admits is not landed yet ("To add once each row lands, never before: ... countries (1.18)").
* **Fix:** Remove the U1–U10 per-case breakdown table (or reduce it to the facts in 4.11 and 1.13) and revise the U5 bullet to: `- **U5 is still a miss.** The patient's Norvasc is paired with the 10 mg box instead of the 5 mg one, and the brief says it can't confirm agreement. Spark still sometimes writes an amount as a word. On batch 21's code that word was dropped, and the engine traces U5's miss to it. [1.13, 4.11]`

**2. Severity: MEDIUM**
* **Sentence:** `| Muse Spark 1.3 (Meta API) | 14 | 2 | 0 | 4 | 0 | $0.0094 | 7.4 s |` (specifically the `Cost per read` and `Median time` columns across all three rows of the comparison table).
* **Row:** [4.13]
* **Why:** Row 4.13's evidence and allowed wording give the 5 outcome counts (`14 / 2 / 0 / 4 / 0`, `14 / 1 / 0 / 3 / 2`, `1 / 1 / 10 / 8 / 0`), and row 5.6 gives total spend on Baseten ($0.30) and Fireworks ($0.28). Neither row evidences per-read cost (`$0.0094`, `$0.0136`, `$0.0100`) or median time (`7.4 s`, `15.4 s`, `23.4 s`).
* **Fix:** Remove the `Cost per read` and `Median time` columns from the comparison table:
  `| Reader | Correct | Harmful | Missed | Abstained | Error |`
  `|---|---|---|---|---|---|`
  `| Muse Spark 1.3 (Meta API) | 14 | 2 | 0 | 4 | 0 |`
  `| Muse Spark Open on Baseten | 14 | 1 | 0 | 3 | 2 |`
  `| Muse Spark Open on Fireworks, strict JSON mode | 1 | 1 | 10 | 8 | 0 |`

**3. Severity: MEDIUM**
* **Sentence:** `- **Both scorings.** The scorer splits a combination's ingredients at "+", "/", "&", "and" and "with". Readers also wrote a comma, so the comma was added after the run, which moved four verdicts out of harmful. As run, the three rows were 13 / 3 / 0 / 4 / 0, 13 / 2 / 0 / 3 / 2 and 0 / 3 / 9 / 8 / 0. [4.13]`
* **Row:** [4.13]
* **Why:** Row 4.13's evidence states only: `A scorer fix made after the run (a comma now splits an INN set) moved four verdicts out of harmful. As run: 13 / 3, 13 / 2 and 0 / 3 (:68–83).` It does not evidence the list of pre-existing delimiters (`"+", "/", "&", "and" and "with"`) or the full 5-number tuples for the as-run scores (such as Fireworks `Missed` changing from `9` to `10`).
* **Fix:** `- **Both scorings.** A scorer fix made after the run (a comma now splits an INN set) moved four verdicts out of harmful. As run: 13 / 3, 13 / 2 and 0 / 3. [4.13]`

### D. Technically allowed by its row, but would still mislead a careful judge

**4. Severity: HIGH**
* **Sentence:** `- Every miss on the ten public photos and the two synthetic notes is in the tables above. [4.11, 4.12]`
* **Row:** [4.11, 4.12]
* **Why:** There is no table for the two synthetic notes in the README, and the prose under `### Two synthetic voice notes` says only that `3 of 6 findings came out as expected before batch 21, and 6 of 6 after it` because spoken number words were dropped. A careful judge looking for "the tables above" to inspect the 3 misses on the synthetic notes will find no table for them, and reading row 4.1 in `docs/CLAIMS.md` reveals what was omitted: those 3 misses were a regression from 27 Oct (when 6 of 6 passed) caused by the batch 20 prompt turning the English and Arabic Concor `match` and the Arabic Beloc-Zok finding into `insufficient_information`. Claiming every miss on the synthetic notes is "in the tables above" when no such table exists is false on its face.
* **Fix:** `- Every miss on the ten public photos is in the table above. On the two synthetic notes, 3 of 6 findings came out as expected before batch 21 (the batch 20 prompt turned the Concor match into insufficient_information in both languages, and the Arabic Beloc-Zok finding too, because each dose spoken in words was dropped), and 6 of 6 after it. [1.13, 4.1, 4.11, 4.12]`

**5. Severity: MEDIUM**
* **Sentence:** `- Muse Voice Transcribe turns the note into timed turns. SAM 3.1 marks each pack it finds. Muse Spark 1.3 picks the medicines out of the transcript and reads each label. [1.2]`
* **Row:** [1.2]
* **Why:** Row 1.2 states that since batch 23 (which is merged at this commit), `SAM tries a third concept, "package", when the first two find nothing`, whereas the `Results` and `Comparison` sections report numbers from batches 21 and 22 before `"package"` was added to the loop (and row 4.14 notes neither U1–U10 nor the comparison has been rerun on batch 23). A careful judge reading `How it works` and `Results` without this distinction in `How it works` won't know that the current product loop has a third SAM fallback concept that was not active during any of the reported test runs.
* **Fix:** `- Muse Voice Transcribe turns the note into timed turns. SAM 3.1 marks each pack it finds (since batch 23, SAM tries a third concept, "package", when the first two find nothing; neither the comparison nor U1–U10 has been rerun on it). Muse Spark 1.3 picks the medicines out of the transcript and reads each label. [1.2, 4.14]`

Verdict: HOLD
