# README draft check (Gemini 4, judge/claims-video a00f113): what changes

Gemini 4 Argon on Vertex, 28 Oct, on the README draft and `docs/CLAIMS.md` at a00f113. **Verdict: HOLD**, with 1 high and 4 medium findings (`qm.md`). The package was those two files, about 18k tokens.

| # | Severity | Decision | What changes |
|---|---|---|---|
| 4 | high | **Accepted.** | The last Limitations line says the two synthetic notes' misses are "in the tables above", but those notes have no table. The line says where the misses are instead. The 3 of 6 is given with its cause: the batch 20 prompt dropped doses spoken as words, and the same notes gave 6 of 6 on 27 Oct. Row 4.1 allows that number only next to the regression. |
| 1 | medium | **Accepted in part.** | The U1–U10 table stays, because it is the table of every miss. Its statuses and causes come from `live-before.md`:31–47 and `live-after.md`:20–34, which row 4.11 already cites. Each case's brand and country come from the pre-registered `manifest.md`:65–74. Row 4.11's allowed wording now covers the table, and a cell found in none of those lines goes. Row 1.18 is a different claim (one medicine under two brand names), so it doesn't block a photo's country. |
| 2 | medium | **Accepted as a row fix.** | Cost per read and median time are in `comparison.md`:23–25, the lines row 4.13 already cites for the counts. Row 4.13 lists them, and the README keeps the columns. |
| 3 | medium | **Accepted as a row fix.** | The scorer's split characters (:69) and the full as-run scores (:79–83) are inside row 4.13's cited :68–83. Row 4.13's allowed wording takes them, and the README sentence stays. |
| 5 | medium | **Accepted, in another place.** | The note goes at the top of "Results, as measured", not in "How it works". It says which code each run used, and that batch 23's changes (the "package" concept and the volume rule) haven't been rerun on them (rows 4.14, 1.19). |

**Also checked, by the engine:** the Lancet citation in row 6.2.
- Crossref lists it in *The Lancet* 408(10565):1732–44, October 2026, first author Brodeur, DOI 10.1016/S0140-6736(26)01535-7.
- Google Research's page for the study gives "33 of 44", where the 44 are the cases in which the doctor read the transcript before the visit, as row 6.2 says.
- The README's citation line takes the DOI.

**Routed:** all five findings go to the judge-facing session, which owns the README and the claims table.

**Spend:** $0.05548 (estimated) on the Google credit, which now stands at $1.68 of $50.95.
