# README draft check, round 2 (Gemini 4, judge/claims-video 9812676): what changes

Gemini 4 Argon on Vertex, 28 Oct evening, on the README draft and `docs/CLAIMS.md` at 9812676. That commit holds the round 1 fixes, both checker agents' findings and Ahmed's bonus decision. **Verdict: HOLD**, with 1 high, 5 medium and 3 low findings (`qm.md`). Nothing in this pass is false. The high finding is the README breaking a rule its own claims table sets.

| # | Severity | Decision | What changes |
|---|---|---|---|
| 7 | high | **Accepted.** | Delete the sentence "On 27 Oct, with that day's code, all three findings came out right on both notes." Row 4.1 lets the README show that result only as the 27 Oct column of the notes table, and the table already has it. The sentence wasn't misleading, since the regression is in the same paragraph. It broke the row's rule. |
| 1 | medium | **Accepted.** | The diagram's node shortens row 1.13 so far that "the label text" could be read as the pack's print. Use "A number is kept only if it is in<br/>the patient's turns or the reader's label text". |
| 2 | medium | **Accepted, reworded.** | "At least one wording" is vague. Gemini's "one such wording" is too narrow: the fail-open is a kind of wording, a tablet word before `in` or `في` and the volume (SPEC §2, batch 23.1). The README and row 1.19 both say: "One kind of wording still keeps a per-tablet reading on purpose: a tablet word before 'in' or 'في' and the volume, as in 'Paracetamol 250 mg = one tablet in each 5 ml'." |
| 5 | medium | **Accepted as a citation fix.** | "Built and tested offline" is row 2.5's wording for the time before the pause runs live. Cite [2.1, 2.5]. |
| 6 | medium | **Accepted as a citation fix.** | The sentence is true, but its backing sits in other rows. "Before batch 21" is `main` 8bb9035, batches 1–20 (rows 4.1, 4.11, 4.12). "No run since batch 22" is row 5.6: batches 23 and 23.1 made no live calls. Cite those rows. |
| 8 | medium | **A dependency, not a wording fix.** | The Best Agentic Use-Case entry stands only if the pause and resume are shown (`plan-2026-10-28/effect.md`:30). Row 2.5, the pause live, waits for Ahmed's unreadable shot and its re-photo. Before submission, either row 2.5 lands or the agentic entry is reconsidered. The README keeps its line, because the pause section already says what has run only offline. |
| 9 | low | **Accepted.** | "The rules for real media" could suggest there is patient media somewhere. Use "The rules for the developer's own photos and voice are in `docs/DATA_HANDLING.md`." |
| 3 | low | **No README change.** | "Codex" is what `codex` is, and it is plainer for a judge. Row 5.3's allowed wording takes it. |
| 4 | low | **No README change.** | The README's diagnostic 4 sentence is longer than row 4.13's, but every fact it adds is in the row's evidence. Row 4.13's allowed wording takes the README's sentence. |

**The HOLD:** the HOLD lifts once #7 is fixed. There is no third Gemini round on the draft. The README gets its full re-check at the `demo-freeze` tag, and again before it merges on Tue.

**Spend:** $0.06485 (estimated) on the Google credit, which now stands at $1.74 of $50.95.
