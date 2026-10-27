# Batch 20 supervisor (Claude Opus 5.5, high effort, read-only)

Prompt: `evidence/grills/BATCH_SUPERVISOR_PROMPT.md`. The builder was Muse Code (`muse-spark-1.3`). The supervisor is a different model family and was not told the CEO's opinion. It probed offline, in scratch copies of the code from before and after the batch. The docs-only commit `f4eb10a` (another session) was out of scope.

## Round 1: SUPERVISOR: CHANGES
1. **major** `anamnesis/providers/spark.py` (`parse_label_json`). A label reply whose `label_text` isn't a string crashes the intake instead of being a malformed reply.
   - Why: `stated_amounts(data.get("label_text") or "")` raises `AttributeError` on an int, list or dict. Neither the parser nor `IntakeSession.call` catches it.
   - Ran: `label_text: 5` through a `MetaLabelReader` on a mock transport, then `run_intake`. Before the batch: a `read: error: spark ProviderError` step. After: an `AttributeError`, no report, and the charge sits on the ledger without reaching any report.
2. **major** `anamnesis/review.py` (`add_photo`). `add_photo` never checks that the review belongs to the report, so a review written for another report can hide a pack that was read clearly.
   - Ran: report A, where o1 is unreadable, gives review `r1`. That review is applied to report B, where o1 is a clear "Concor 10 mg". The call is accepted, B's o1 is superseded and its finding disappears, and the brief accepts the returned pair and shows the clear pack as "Replaced by a newer photo."
   - The SPEC §8 refusal list didn't name this case (CEO gap).
3. **minor** `anamnesis/review.py`. New regions aren't de-duplicated by `region_id` as the loop does. Ran: a segmenter returning `[R2, R2]` gives the region twice and two elements with `id="region:…"`.
4. **minor** `anamnesis/providers/stated.py`. The `point` branch doesn't check the value is positive. Ran: `stated_amounts("zero point zero")` returns `{0.0}`.
5. **minor** (SPEC) `stated_amounts`. `normalise` strips punctuation, so a run of number words joins across a comma. Ran: "Concor five, two tablets" states 7 (a small fail-open).
6. **minor** (maintainability) `add_photo` is about 65 lines and prepares the new photo twice. It repeats the loop's undecodable step and the zoom predicate inline, and it computes the review status in two places.

Mutations: 25 tried in a scratch copy; the suite caught all 25. Findings 1 and 2 were holes no test covered.

**CEO triage:**
- **#1–#5 accepted**, with round 2 cases added to the contract:
  - #1: a non-string `label_text` is a malformed reply;
  - #2: `add_photo` refuses a review of another report (added to SPEC §8);
  - #3: regions de-duplicated as in the loop;
  - #4: only positive values;
  - #5: SPEC §2 now ends a run at punctuation.
- **#6 accepted in part:** prepare once, reuse the loop's `_NEEDS_ZOOM`, and one status helper. A shared loop helper would change `run_intake` before the deadline, so it is deferred as a follow-up.

## Round 2: SUPERVISOR: APPROVE
Each of the six findings was re-checked by re-running its round 1 probe:
- **#1:** `label_text: 5` through a mock `MetaLabelReader` and `run_intake` now matches the build from before the batch: a `read: error: spark ProviderError` step, with the spend on the report.
- **#2:** answering report B with report A's review is refused before any photo is prepared or any model is called.
- **#3:** a region found twice is kept once, and the brief has one element with its id.
- **#4:** "zero point zero" states nothing.
- **#5:** "five, two", "five. Two", "five; two", "five\ntwo" and "خمسه، اتنين" state 5 and 2, never 7; "twenty-five" and "two and a half." are unchanged.
  - The digit pass is unchanged: 21 fixed strings ("2.5", "2,5", "1,000", "0.125", "875 mg/125 mg", "٢٫٥", …) give the same sets, and a 200,000-case fuzz on digit and punctuation strings found 0 differences.
- **#6:** done as briefed: the photo is prepared once, the zoom condition is the loop's `_NEEDS_ZOOM`, and one status helper is used.

7. **minor, new** `anamnesis/providers/stated.py` (`_RUN_BREAK`). Line breaks other than `\r` and `\n` (`\u2028`, `\x85`, `\v`) and the ellipsis `…` don't end a run. Ran: "five\u2028two" and "five… two" each state 7. A transcript is unlikely to contain them.

Mutations: the 25 round 1 mutants were re-run and all caught; 12 of 13 round 2 mutants were caught. The survivor wraps a value in `str()`, which behaves the same as the real code.

**CEO triage:** #7 is a follow-up for the next contract: add the Unicode line breaks and `…` to the break set in SPEC §2. It fails open only on characters a transcript is unlikely to contain, so it doesn't block this batch.
