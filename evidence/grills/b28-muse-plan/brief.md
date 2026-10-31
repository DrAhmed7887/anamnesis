# Batch 28 design: a second label reader after the zoom

You are planning, not building. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, and use no API key;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The plan is done ONLY when your reply has the four sections in §4, and every point cites a file and line you opened in this session.

## 2. What happened (30 Oct, live)
- **Reading is the main miss.** In the live U1–U8 columns, Spark 1.3 read four of the eight staged packs as partial in at least one run, even after the loop's 2× zoom (`anamnesis/agent/loop.py`, `_zoom`). The pack then gives `unreadable_source`, and the clinician can ask for a re-photo (`anamnesis/review.py`).
- **A second model reads differently.** Muse Spark Open on Fireworks, at low reasoning effort, read three of those four from the same crops correctly; the fourth stayed partial.

## 3. The CEO's design (challenge it)
- **The specification:** SPEC.md §4 step 5b, the §4 "Budget" line, §4 "The second reader in the live script (batch 28)", and §8's `add_photo` lines.
- **The contract:** `tests/contract/test_b28_second_reader.py`, 22 tests.
- **The build brief:** `briefs/28.md`.

## 4. Reply
1. **Verdict on the design:** one line.
2. **Risks:** numbered, each with file:line and what to do. For instance: anything that lets a second reading override evidence it shouldn't; the budget and the session's dollar cap; the re-photo path; provenance of the crop; the brief's timeline; and anything the contract fails to pin.
3. **The implementation plan:** where each change goes and in which order you'd build and test it.
4. **Open questions for the CEO.**

Keep it under 600 words.
