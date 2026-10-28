### A. Says more than the cited row's allowed wording or evidence, or widens its scope

**1. Severity: MEDIUM**
* **README:** `st["A number is kept only if it is<br/>in the turns or the label text"]` (with `<sub>The diagram restates rows 1.2, 1.3, 1.6, 1.13, 1.16, 2.1, 2.2 and 3.1.</sub>`)
* **Row:** [1.13]
* **Why:** Row 1.13's allowed wording is `"A number a model writes is kept only if it appears in the patient's turns or in the label text the reader returned."` It explicitly notes that on the pack side it checks `"the label text the reader itself returned"` and forbids wording that implies checking what the pack prints directly. Dropping `"a model writes"` and `"the reader returned"` widens the scope in the diagram.
* **Fix:** `st["A number a model writes is kept only if it appears<br/>in the patient's turns or in the label text the reader returned"]`

**2. Severity: MEDIUM**
* **README:** `"It doesn't read every syrup wording, and at least one wording still keeps a per-tablet reading on purpose: "Paracetamol 250 mg = one tablet in each 5 ml". [1.19]"`
* **Row:** [1.19]
* **Why:** First, `"at least one wording"` widens row 1.19, which states `"one such wording still keeps a per-tablet reading on purpose"` after Batch 23.1 narrowed the fail-open to dissolving lines with `in` or «في». Second, row 1.19 forbids `"reads every syrup wording"`, and its allowed wording does not state that the rule "reads" syrup wordings (it filters strengths written by the reader).
* **Fix:** `"Batch 23.1 narrowed the fail-open to dissolving lines, the ones with 'in' or 'في', and one such wording still keeps a per-tablet reading on purpose: 'Paracetamol 250 mg = one tablet in each 5 ml'. [1.19]"`

**3. Severity: LOW**
* **README:** `"Batches 1–12 were built with GPT-6 Sol and Luna through Codex, some with Claude Code fixes, and batch 6 by Claude Code directly. Batches 13–15.5 were built by Claude Sonnet subagents. [5.3]"`
* **Row:** [5.3]
* **Why:** Row 5.3's evidence records `"codex"`, not `"Codex"`.
* **Fix:** `"Batches 1–12 were built by GPT-6 Sol and Luna through codex, some with Claude Code fixes, and batch 6 by Claude Code directly. Batches 13–15.5 were built by Claude Sonnet subagents. [5.3]"`

**4. Severity: LOW**
* **README:** `"Read again with an 8,000-token cap, Baseten's two length stops both came back correct. Both replies ended under the old 4,000-token cap, so this was a second draw, not a fix, and the table keeps both as errors. [4.13]"`
* **Row:** [4.13]
* **Why:** Row 4.13 specifies a narrower exact allowed sentence for this diagnostic: `"Read again, both came back correct, but both replies ended under the old cap: a second draw, not a fix."` (Though the extra details appear in row 4.13's evidence notes, they are outside the quoted allowed wording.)
* **Fix:** `"Read again, both came back correct, but both replies ended under the old cap: a second draw, not a fix. The table keeps both as errors. [4.13]"`

### B. Makes a claim with no row, or cites a row that doesn't cover what the sentence says

**5. Severity: MEDIUM**
* **README:** `"The pause is built and tested offline. [2.1]"`
* **Row:** [2.1] (and un-cited pending row [2.5])
* **Why:** The phrase `"built and tested offline"` is the fallback wording from row 2.5 (`⏳ Pending`), not row 2.1's allowed wording column. Row 2.1 only has `(tested offline)` in its claim title.
* **Fix:** Fold into the first bullet of that section using row 2.1's title and allowed wording: `"If a label can't be read, the clinician can ask the patient for one new photo (tested offline). Only that photo is processed, and the brief updates. The run pauses for a person, then resumes. [2.1]"`

**6. Severity: MEDIUM**
* **README:** `"Every run below predates batch 23. The synthetic notes ran on the code of 27 Oct, of batch 20 and of batch 21, the public photos on batch 20's and batch 21's, and the comparison on batch 22's. Batch 23's changes, the "package" concept and the volume rule, haven't been rerun on any of them. [4.1, 4.11, 4.13, 4.14, 1.19]"`
* **Row:** [4.1, 4.11, 4.13, 4.14, 1.19]
* **Why:** None of the five cited rows states or backs that the pre-batch-21 runs of the synthetic notes or public photos ran specifically `"on the code ... of batch 20"`; rows 4.1, 4.11, and 4.12 only describe them as `"before batch 21"` (at `main` 3b40d5a / 6d41473, which covers batches 1–20) and attribute the regression to `"the batch 20 prompt"`. Nor do those rows state the synthetic notes weren't rerun on batch 23.
* **Fix:** `"The synthetic notes ran on 27 Oct and on 28 Oct before and after batch 21, and the public photos ran before and after batch 21. [4.1, 4.11, 4.12] Neither the comparison nor U1–U10 has been rerun on batch 23's 'package' concept or volume rule. [1.19, 4.13, 4.14]"`

### C. Uses a word or claim that the table forbids

**7. Severity: HIGH**
* **README:** `"On 27 Oct, with that day's code, all three findings came out right on both notes. [4.1]"`
* **Row:** [4.1]
* **Why:** Row 4.1 explicitly restricts how the README may use this claim: `"Never on its own... Prefer rows 4.11 and 4.12. The README shows it only as the 27 Oct column of the notes table, beside the 28 Oct regression and the result after batch 21."` Writing it as a prose sentence above the table violates row 4.1's README restriction.
* **Fix:** Delete the sentence from the prose and keep the 27 Oct results solely as the `27 Oct` column in the table below it, citing `[4.1, 4.12]` on the lead-in sentence.

### D. Technically allowed by its row, but would still mislead a careful judge

**8. Severity: MEDIUM**
* **README:** `"Built for the Meta Global AI Developer Hackathon. Track: Indie. Also entered for two bonus prizes: Best Agentic Use-Case and Best Build on Meta Open Weight Models. [6.4]"`
* **Row:** [6.4] and [2.3]
* **Why:** Row 2.3 states of the Best Agentic Use-Case bonus prize: `"That entry stands only with the pause and resume on screen (plan-2026-10-28/effect.md:30), and row 2.5, the pause live, is still pending."` Meanwhile, under "The clinician's pause", the README admits the pause is only `"tested offline"` with no live run yet. A careful judge reading both will notice the submission claims a bonus prize whose own prerequisite (`[2.5]`) hasn't landed yet, or that the "agentic" workflow has no model choosing any action (`[2.3]`) and hasn't been run live.
* **Fix:** Keep `[6.4]`'s exact wording, and add row 2.3's allowed framing right after it so the basis of the entry is transparent up front: `"The code fixes the order. The clinician decides the pause. No model chooses an action. [2.3]"`

**9. Severity: LOW**
* **README:** `"The rules for real media are in [`docs/DATA_HANDLING.md`](docs/DATA_HANDLING.md)."`
* **Row:** [3.3] (uncited in the second sentence)
* **Why:** Saying `"The rules for real media"` right after `"No patient data"` could make a judge wonder if real patient media is handled elsewhere. Row 3.3 backs `docs/DATA_HANDLING.md` only for no patient data and staged tests (`[4.15]`).
* **Fix:** Remove the uncited sentence or cite `[3.3, 4.15]`: `"These are staged tests, not a validation (`docs/DATA_HANDLING.md`). [3.3, 4.15]"`

Verdict: HOLD
