# Anamnesis

**What the patient says vs. what's on the pack.**

The patient sends a voice note and photos of their medicine packs. The clinician gets a one-page brief. [1.1] Every finding links back to the audio turn and the image region it came from. [1.3]

Built for the Meta Global AI Developer Hackathon. Track: Indie. Also entered for two bonus prizes: Best Agentic Use-Case and Best Build on Meta Open Weight Models. [6.4]

Anamnesis is not a medical device and gives no medical advice. [1.15]

Numbers in brackets, such as [4.13], are rows of [`docs/CLAIMS.md`](docs/CLAIMS.md). Each row gives a claim's evidence by file and line, and the words the claim may use.

## Why
In a Lancet feasibility study, primary care doctors who read an AI pre-visit chat said it helped them prepare in 33 of 44 cases. But a chat can't see the pack. [6.2]

<sub>Brodeur PG et al. Conversational diagnostic artificial intelligence in ambulatory primary care: a prospective feasibility study. *Lancet* 2026;408(10565):1732–44. [doi:10.1016/S0140-6736(26)01535-7](https://doi.org/10.1016/S0140-6736%2826%2901535-7)</sub>

## How it works
```mermaid
flowchart LR
    voice["Voice note"] --> vt["Muse Voice Transcribe:<br/>timed turns"]
    vt --> cx["Muse Spark 1.3:<br/>the medicines the patient names"]
    photo["Pack photos"] --> clean["Turned upright,<br/>metadata stripped"]
    clean --> sam["SAM 3.1:<br/>marks each pack it finds"]
    sam --> rd["Muse Spark 1.3:<br/>reads each crop"]
    cx --> st["A number is kept only if it is in<br/>the patient's turns or the reader's label text"]
    rd --> st
    st --> cmp["Plain code compares<br/>the two sides"]
    cmp --> brief["One-page brief:<br/>each finding linked to its turn and crop"]
    brief --> doc{"Clinician"}
    doc -- "asks for one new photo" --> photo
    doc -- "approves" --> signed["Approved brief"]
```
<sub>The diagram restates rows 1.2, 1.3, 1.6, 1.13, 1.16, 2.1, 2.2 and 3.1.</sub>

- Muse Voice Transcribe turns the note into timed turns. SAM 3.1 marks each pack it finds. Muse Spark 1.3 picks the medicines out of the transcript and reads each label. [1.2]
- Before any model sees a photo, Anamnesis turns it upright and strips its metadata, GPS included. [3.1]
- The label reader only ever sees the crop of its own box. [1.6]
- A number a model writes is kept only if it appears in the patient's turns or in the label text the reader returned. [1.13]
- When a pack prints a strength per a volume, such as 250 mg per 5 ml, a reading keeps that strength only if the pack also prints it in the reading's own unit, such as per ml. Otherwise the strength is left empty. It is built to lose a strength rather than keep a wrong one, and its known exceptions are under Limitations. [1.19]
- Then plain code compares the two sides. No model decides a finding. [1.16]
- When the reader reports a label unreadable or partial, Anamnesis says so. [1.17] If a photo shows no pack, the brief says so. [1.12]
- Every product model call is logged with its cost, and each live intake has a call cap and a dollar cap. [3.5]

## The brief
- Disagreements come first, with what the patient said, as extracted, and the pack side by side. [1.7]
- Click a turn and you hear that turn, from its start to its end. [1.4] Click the box and you see the crop the label reader saw. [1.5]
- Every sentence Anamnesis adds is fixed text. It adds no advice of its own, and pack text is quoted as printed. [1.8]
- Panadol and Gelocatil are two brand names for one medicine. Anamnesis notes that both contain paracetamol, and that concurrent use is unconfirmed. [1.9] It also notes two medicines from one class, beta-blockers. Concurrent use is unconfirmed. [1.10]
- Only what the patient says counts as use. A photo of a pack never does. [1.11]
- The brief is one static page. It calls no model, and it refuses media the report wasn't made from. [1.14]
- Every brief ends with a collapsed "How it got here" table: one row per agent step, with its model, tokens, time and cost, and a total with the intake's calls and spend. [1.20]

## The clinician's pause
- If a label can't be read, the clinician can ask the patient for one new photo. Only that photo is processed, and the brief updates. The run pauses for a person, then resumes. [2.1]
- The brief stays a draft until the clinician approves it. [2.2]
- The code fixes the order. The clinician decides the pause. No model chooses an action. [2.3]
- The pause is built and tested offline. [2.1, 2.5] There is no clinician app yet: the request is one function call, and in the demo the developer plays the clinician. [2.6]

## Results, as measured
Every run below predates batch 23 except the last, the full intake with Muse Spark Open: batches 23 and 23.1 made no live calls of their own. [5.6] The synthetic notes ran on 27 Oct's code, then on batches 1–20 and on batch 21; the public photos on batches 1–20 and on batch 21; and the comparison on batch 22's code. [4.1, 4.11, 4.12, 4.13] Batch 23's changes, the "package" concept and the volume rule, haven't been rerun on those. The last run used batch 23.1's code, on eight of the public photos. [4.14, 1.19, 4.16]

These are staged tests, not a validation. The expected results come first, and every run is reported as it came out, failures included. [4.15] No patient data: the pack photos are rendered test images or real public photos, the patients' histories are invented, and every voice so far is synthetic. [3.3]

### Ten public pack photos, before and after batch 21
The expected results were committed before the first run (8b993ff). [4.4] On the same ten pre-registered public-photo cases, with the same expected results, the code got 1 right before batch 21 and 3 after it. Neither run showed a false match, or a wrong strength or ingredient as fact. [4.11]

| Case | Expected | Before batch 21 | After batch 21 |
|---|---|---|---|
| U1 Concor, Russia (Cyrillic) | `match` | `insufficient_information` | `match` ✓ |
| U2 Augmentin, Belgium (French) | `match` | not paired | `insufficient_information`: the claim came back with no strength (fails safe) |
| U3 Panadol, Australia | `match` | `insufficient_information` | `match` ✓ |
| U4 Panadol 500 mg, Finland, two tablets | `intake_differs_from_unit_strength` | ✓ | ✓ |
| U5 Norvasc 5 mg and 10 mg, Israel | paired with the 5 mg box, `match` | paired with the 10 mg box | paired with the 10 mg box, `insufficient_information`: a wrong pairing |
| U6 Glucophage, China | `match` | `unresolved_name` | the same: the reader transcribed the manufacturer block (fails safe) |
| U7 Sortis 40 mg vs "Lipitor twenty milligrams" | `strength_mismatch` | `insufficient_information` | `unreadable_source`: the pack read as only partly readable (not harmful) |
| U8 Betaloc ZOK 100 | `match` | `unreadable_source` | the same: low resolution, the unit cut off (not harmful) |
| U9 Panadol Extra carton | `ingredient_mismatch` | no pack found | the same: SAM finds no pack in flat label artwork (fails safe) |
| U10 Panadol Extra Strength 500 | `match` | no pack found | the same (fails safe) |

- **U5 is still a miss.** The patient's Norvasc is paired with the 10 mg box instead of the 5 mg one, and the brief says it can't confirm agreement. [4.11] Before batch 21, the claim tied with both boxes and the tie went by id. Batch 21 lets the patient's stated dose break such a tie, but in its run the claim and the 5 mg box both came back without amounts, so the two boxes tied again. Spark still sometimes writes an amount as a word, and on batch 21's code that word was dropped. [4.11, 1.13]
- **U7 is a miss in both runs.** Its expected result was written wrong: it assumed the patient stated a strength, but Spark read "Lipitor twenty milligrams" as an intake. The expected result is kept as written. [4.11]
- These two runs are the scope of the "no false match" line. In the comparison below, Spark 1.3 showed a wrong strength as fact on 2 of 20 crops. [4.11]
- Every case, cause and cost: [`evidence/batches/21/live-after.md`](evidence/batches/21/live-after.md).

### Two synthetic voice notes
On two synthetic notes, one English and one Egyptian Arabic, 3 of 6 findings came out as expected before batch 21, and 6 of 6 after it. [4.1, 4.12]

| Note | Expected | 27 Oct | 28 Oct, before batch 21 | After batch 21 |
|---|---|---|---|---|
| English: Concor "five milligrams once a day" | `match` | ✓ | `insufficient_information` | ✓ |
| English: metoprolol 50 mg twice a day vs Beloc-Zok 100 mg | `intake_differs_from_unit_strength` | ✓ | ✓ | ✓ |
| English: Panadol, stopped | stopped | ✓ | ✓ | ✓ |
| Arabic: كونكور خمسة ملي جرام (Concor, five milligrams) | `match` | ✓ | `insufficient_information` | ✓ |
| Arabic: بيلوك زوك خمسين ملي جرام (Beloc-Zok, fifty milligrams) vs Beloc-Zok 100 mg | `intake_differs_from_unit_strength` | ✓ | `insufficient_information` | ✓ |
| Arabic: البنادول (Panadol), stopped | stopped | ✓ | ✓ | ✓ |

The three misses on 28 Oct came from the batch 20 prompt. Spark copied each dose spoken in words ("five") into the amount, the stated-amount rule dropped it, and every such case failed safe to `insufficient_information`. Batch 21 asks for digits. [1.13, 4.1]

### Cost and time
About 3 cents per intake (12 live intakes, 28 Oct). [4.2] One intake took 17 to 49 seconds (12 live intakes, 28 Oct). [4.9]

## Muse Spark Open, Meta's open-weight model, as the label reader
Built with Muse Spark Open, in a zero-shot comparison and in a run of the full intake as its label reader. The product's default label reader stays Muse Spark 1.3. [4.13, 4.16]

### A zero-shot comparison on 39 public photos

In a pre-registered zero-shot comparison, SAM 3.1 found a pack in 20 of 39 public photos. On those 20 crops, as first scored, Spark 1.3 read 13 correctly with 3 harmful readings, and Muse Spark Open on Baseten read 13 with 2. A scorer fix made after the run raised both to 14, with 2 and 1 harmful. [4.13] Every reader read the same SAM 3.1 crops with the same system prompt, schema and parser, and no model was trained. Baseten also got the schema as text in its user message, and Fireworks used strict JSON mode. The photos are 30 Cairo University phone photos (CC BY 4.0) and 9 Wikimedia Commons photos. [4.13]

<sub>Cairo photos: Abdelmaksoud E, Gadallah A, Asad A. Mobile-Captured Pharmaceutical Medication Packages. Mendeley Data, v1, 2022. [doi:10.17632/bjy2svvmn8.1](https://doi.org/10.17632/bjy2svvmn8.1), CC BY 4.0.</sub>

A descriptive comparison from one pass, n = 20: 20 photos of 17 packs, since the Cairo photos come two per pack. Scored after the scorer fix below: [4.13]

| Reader | Correct | Harmful | Missed | Abstained | Error | Cost per read | Median time |
|---|---|---|---|---|---|---|---|
| Muse Spark 1.3 (Meta API) | 14 | 2 | 0 | 4 | 0 | $0.0094 | 7.4 s |
| Muse Spark Open on Baseten | 14 | 1 | 0 | 3 | 2 | $0.0136 | 15.4 s |
| Muse Spark Open on Fireworks, strict JSON mode | 1 | 1 | 10 | 8 | 0 | $0.0100 | 23.4 s |

- **Both scorings.** The scorer splits a combination's ingredients at "+", "/", "&", "and" and "with". Readers also wrote a comma, so the comma was added after the run, which moved four verdicts out of harmful. As run, the three rows were 13 / 3 / 0 / 4 / 0, 13 / 2 / 0 / 3 / 2 and 0 / 3 / 9 / 8 / 0. [4.13]
- **Every harmful reading:** [4.13]
  - Spark 1.3 read Janumet's metformin as 100 mg, where the pack prints 1000 mg. [4.13]
  - Spark 1.3 read a 250 mg/5 ml syrup as "250 mg per dose". [4.13]
  - Spark Open on Baseten read the same syrup as 250 mg per ml, a fivefold error. [4.13]
  - Spark Open on Fireworks put the placeholder "not_printed_in_visible_crop" in a reading's ingredient field. [4.13]
- **Why Fireworks scores low:** its strict JSON mode returned no strength on any crop, so that row measures the host's setting, not the open weights. [4.13]
- **Baseten's 2 errors** were length stops at the 4,000-token limit: no reading, charged, and failed safe. [4.13]
- **Diagnostics decided after the run, not scores:**
  - With JSON mode off, the same model on Fireworks read 5 of 5 crops that the other two readers had read correctly. [4.13]
  - Read again with an 8,000-token cap, Baseten's two length stops both came back correct. Both replies ended under the old 4,000-token cap, so this was a second draw, not a fix, and the table keeps both as errors. [4.13]
  - In a diagnostic after the run, not pre-registered, the concept "package" found a pack in all 19 photos where the first two concepts found none. With it, Spark 1.3 would have read 22 of the 30 Cairo phone photos correctly, not 7. Batch 23 added it to the loop. [4.14]
- The volume rule above was written for the two syrup readings, but the comparison wasn't rerun on it. [1.19, 4.13]
- Every photo, reader and verdict: [`evidence/batches/22/comparison.md`](evidence/batches/22/comparison.md).

### The full intake, with Spark Open reading the labels
With Muse Spark Open as its label reader, the full intake ran end to end on eight pre-registered public-photo cases, once each, with no harmful reading. It got the same correct-or-miss verdict as with Spark 1.3 on seven. [4.16] Both columns ran on 28 Oct evening on the same code, and everything but the label reader was the same: Voice Transcribe, Spark 1.3 for the claims, SAM 3.1 and the caps. The plan was committed before the first call (4f5e569). [4.16]

| Case | Expected | Spark 1.3 reads | Spark Open reads |
|---|---|---|---|
| U1 Concor, Russia | `match` | `insufficient_information` | `match` ✓ |
| U2 Augmentin, Belgium | `match` | `unreadable_source`: read as partial | `insufficient_information` |
| U3 Panadol, Australia | `match` | ✓ | ✓ |
| U4 Panadol, Finland, two tablets | `intake_differs_from_unit_strength` | ✓ | ✓ |
| U5 Norvasc 5 mg and 10 mg, Israel | paired with the 5 mg box, `match` | ✓ | ✓ |
| U6 Glucophage, China | `match` | `unresolved_name` | `unresolved_name` |
| U7 Sortis 40 mg vs "Lipitor twenty milligrams" | `strength_mismatch` | `unreadable_source` | `unreadable_source` |
| U8 Betaloc ZOK 100 | `match` | `unreadable_source` | `unreadable_source` |

- **U1 is the one case where the verdicts differ, and the reader didn't cause it.** Both readers read the pack as bisoprolol 5 mg. The claim extraction, Spark 1.3 in both columns, dropped the spoken "five milligrams" in one run and kept it in the other. [4.16]
- **U2 is the one case where the readers differ.** Spark Open read the pack fully, amoxicillin 875 mg + clavulanic acid 125 mg, and Spark 1.3 read it as partial. Both miss U2 on the claim side: the claim came back without its amounts. [4.16]
- **U5** paired with the 5 mg box in both columns, on one run per reader, so it isn't counted as fixed. [4.16, 4.11]
- n = 8, one run each, so a one-case difference can be chance. U9 and U10 were left out, because their DailyMed photos may not go to Baseten. [4.16]
- $0.56 for the 16 intakes, Meta $0.37 and Baseten $0.19. An intake took 31.7–63.4 s with Spark Open reading, and 28.9–45.7 s with Spark 1.3. [4.16]
- Every case and cause: [`evidence/batches/22/intake-openweight.md`](evidence/batches/22/intake-openweight.md).

## How it was built
- Muse Code wrote the product code for the last ten batches. [5.1] All product code in `anamnesis/` from batch 16 on was written by Muse Code. [5.3] The brief, its timeline, the photo request, the cross-medicine check and the volume rule are code Muse Code wrote. [5.2]
- Claude Code wrote the spec and the acceptance tests. Muse Code wasn't allowed to edit them, and the gate fails any batch that does. A separate Claude Opus reviewer checked every Muse batch. [5.4]
- Batches 1–12 were built with GPT-6 Sol and Luna through Codex, some with Claude Code fixes, and batch 6 by Claude Code directly. Batches 13–15.5 were built by Claude Sonnet subagents. [5.3]
- In batch 22, a separate Claude Opus reviewer caught a spec error: as briefed, "less than five milligrams" could have been read as exactly five, if a model wrote the amount as "<five". The contract now pins that case. [5.10]
- Batch 23 took nine rounds: a separate Claude Opus reviewer sent it back seven times before approving it. Before each round, Claude Code checked its own contract on a throwaway reference build. At the end, all 44 deliberate single-rule breaks of that reference were caught by the contract. Its follow-up, batch 23.1, passed review in one round with nothing to change. [5.11]
- Before the freeze, a Gemini 4 grill claimed 11 breaks, and each was run against the code. Two were real: the comparison script's photo check was wider than the data rule and was fixed, though no photo outside the rule was ever sent, and a volume written in words stays a known limit. [5.12]
- Before the freeze, Muse Code audited the repository read-only and found 7 minor gaps, each checked against the code and fixed. It pinned the audit as its goal with its own goal tool, kept to the seven-step plan it wrote, and closed the goal complete: 31 of its 32 model calls ran under that goal. [5.13]
- Batches 1 to 20 were each specified, built, gated and reviewed in one day, 27 Oct. [5.8]
- Muse Code's sessions cost about $28.06 of Meta credit so far, priced from its own billing records (28 Oct). [5.5] About $30.27 of the $150 credit in logged calls so far (28 Oct). Muse grill runs are billed separately. [5.6]
- Each Muse batch's record is in `evidence/batches/<n>/`: `builder.md`, `gate.json`, `supervisor.md` and `review.md`. [5.1]

## Run the tests
1,932 tests run offline, with no keys. [5.7]

```bash
uv run pytest
```

## Limitations
- No outside usability check was done: it was declined ("not now"). [4.8]
- Tested on synthetic voices only, in English and Egyptian Arabic. [3.3, 4.12]
- The same Arabic recording came back in three different spellings across runs. Curated Arabic brand names cover the ones seen so far. [4.3]
- Turns, not words: click a turn and you hear the whole turn. [1.4]
- The number check looks only at the number, not its unit, and doesn't check the regimen's counts. On the pack side it checks the label text the reader itself returned. Spanish number words aren't read, so such a dose is dropped. [1.13]
- Only one class is curated, beta-blockers, and interactions aren't checked. [1.10]
- SAM 3.1 doesn't always find the pack: in the comparison it found one in 20 of 39 public photos. [1.2, 4.13]
- The volume rule gives up some coverage on purpose, listed in SPEC §2: single-dose injectables and pens read per dose, such as "40 mg/0.4 ml", lose their strength, which fails closed. It doesn't read every syrup wording, and three kinds of wording are known to keep a strength they shouldn't: a tablet word before "in" or «في» and the volume, kept on purpose ("Paracetamol 250 mg = one tablet in each 5 ml"); a volume written in words ("Each five ml contains 250 mg"); and a per-1-ml print beside another volume, read per dose ("Each 5 ml contains 250 mg/ml"). Packs print volumes in digits. [1.19, 4.17]
- Salt names that aren't curated, such as rosuvastatin calcium, sitagliptin phosphate and candesartan cilexetil, stay as written, so a pack read with its salt doesn't pair with the patient's claim. [4.17]
- Decomposed accents (Unicode NFD) in catalogue names aren't normalised, so such a name goes unpaired, which fails safe. [4.17]
- Spoken numbers with a thousand after a hundred or another thousand are a known gap: "two hundred and one thousand" parses as 201,000, and «ألفين وألف» as 3,000. [4.17]
- Every miss is in the tables above: the ten public photos, the two synthetic notes and the intake run with Muse Spark Open. [4.11, 4.12, 4.16]

## Data and privacy
- No patient data. The pack photos are rendered test images or real public photos, the patients' histories are invented, and every voice so far is synthetic. [3.3] The rules for the developer's own photos and voice are in [`docs/DATA_HANDLING.md`](docs/DATA_HANDLING.md).
- Every product call used Meta's standard models. [3.4]

## Built with
- **Meta models in the product:** Muse Voice Transcribe, SAM 3.1 and Muse Spark 1.3. [1.2]
- **Meta tooling in the build:** Muse Code. [5.1]
- **Open weights:** Muse Spark Open, Meta's open-weight model, in a zero-shot comparison (on Baseten and Fireworks) and in a run of the full intake as its label reader (on Baseten). The product's default label reader stays Muse Spark 1.3. Those providers bill Spark Open's reads, outside the Meta credit. [4.13, 4.16, 5.6]

## Where things are
- [`SPEC.md`](SPEC.md): the contract.
- [`anamnesis/`](anamnesis/): the product code.
- [`tests/contract/`](tests/contract/): the acceptance tests. [5.4]
- [`evidence/`](evidence/): each batch's record, the live runs, the spend ledgers and the decisions.
- [`docs/CLAIMS.md`](docs/CLAIMS.md): every claim on this page, with its evidence.

By Ahmed Zayed, physician (MBBCh). [6.1]

<!-- Draft from docs/CLAIMS.md (judge/claims-video, 28 Oct). To add once each row lands, never before:
the hero's N of 10 (4.5) and its disagreement (4.10); Ahmed's real cases (4.6) and his voice (4.7, and 3.3's second
wording); the pause, live (2.5); one medicine under another brand name in another country (1.18); a hosted sample brief, once it
has a row (§7). -->
