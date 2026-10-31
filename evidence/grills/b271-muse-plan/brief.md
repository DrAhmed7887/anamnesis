# Batch 27.1 design: durations, "weiß nicht", and a dropped amount's tablet count

You are planning, not building. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, and use no API key;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The plan is done ONLY when your reply has the four sections in §4, and every point cites a file and line you opened in this session.

## 2. What happened (31 Oct)
- **Batch 27 merged** the relation checks (`anamnesis/providers/relations.py`, the hook in `anamnesis/providers/claims.py`).
- **The Opus supervisor found two gaps that fail safe:** "I take Concor ten a day for five years" drops the 10, because rule 6 takes "five years" as a splitter; and German "ich weiß nicht fünf Milligramm" drops the 5.
- **The live probe found one that doesn't:** on "ten milligrams a day, five in the morning and five at night" the tuned Glimmer wrote a 10 mg intake and five tablets. Rule 6 dropped the 10, but the five stayed and gave a false `strength_mismatch`.
- **A CEO reference build of the three fixes** passes this batch's contract and batch 27's, loses none of 1,452 scored replies, and changes none of 148 saved live claims.

## 3. The CEO's design (challenge it)
- **The specification:** SPEC.md §2, "Relation checks (batch 27)": the three places marked "batch 27.1".
- **The contract:** `tests/contract/test_b271_relations.py`.
- **The build brief:** `briefs/27.1.md`.

## 4. Reply
1. **Verdict on the design:** one line.
2. **Risks:** numbered, each with file:line and what to do: phrasings the duration rule would read wrongly, how "weiß nicht" interacts with rule 1's window, and how the tablet-count rule interacts with the pairing rule and `units_per_intake`'s existing checks.
3. **The implementation plan:** where each change goes, in order.
4. **Open questions for the CEO.**

Keep it under 500 words.
