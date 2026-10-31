# The hero, ten fresh runs (31 Oct, 12:45–12:54 CET): 10 of 10 with the system's own categories

As set out in `hero-rerun-plan.md` before any call: U12 (two public Commons photos, the synthetic voice note `U12.wav`), ten runs on the default path (Spark 1.3 transcribes, extracts and reads), `main` at 2e0d985 (batch 27 merged), one sitting. Scorer: `score_rerun.py`.

| Scored | Correct | Harmful |
|---|---|---|
| As registered on 28 Oct (Concor `strength_mismatch`) | 0 of 10, by construction | 0 |
| With the system's own categories (Concor `intake_differs_from_unit_strength`, Beloc-Zok `match`, the beta-blocker note) | **10 of 10** | 0 |

- **Every run gave all three findings:** Concor 10 mg said against the 5 mg box, Beloc-Zok matching the Bloxazoc 50 mg box, and the same-class note for two beta-blockers.
- **Transcription still repeats words.** Five of the ten transcripts had a repeat ("take take", "and and", "twice twice", "morning morning"), and one had a stray full stop. None of it cost a finding.
- **Against 28–29 Oct (6 of 10 with the same categories):** that run predates batch 24's fix for empty strengths and "null" labels (this folder's `README.md`). The difference is two commits of code, not chance alone, but n = 10 each and one synthetic voice: it describes these runs, not human speech.
- **Spend:** $0.40 of Meta for the ten runs (`runs.jsonl`: $0.39781).
