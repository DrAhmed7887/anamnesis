# Batch 23 review: the "how it got here" timeline, the M5 review's fixes, and two coverage fixes from the open-weight comparison (SPEC §2, §4, §5, §7)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 9 rounds, goal pinned with its goal tool in each

**What the batch adds:**
- **The timeline:** a collapsed "How it got here" section in the brief (`<details id="timeline">`). It has one row per agent step: target, outcome, model, tokens in and out, time and cost. A total row spans the table, and the steps sum to the report's `spend_usd`.
- **The M5 review's fixes:**
  - a `*-contributor` model is refused anywhere in an id;
  - both Arabic-Indic digit sets are normalised;
  - the units pin never reaches `match`.
- **Two coverage fixes from the 39-photo comparison:**
  - SAM's third concept, "package", is shared by the intake and `add_photo`, with a call budget that covers every call;
  - SPEC §2's rule for a strength printed per a volume other than 1 ml.

**Who did what:**
- **Claude Code (Opus 5.5), as CEO,** wrote the SPEC lines, the briefs and the contracts on 28 Oct: `test_b23_timeline.py`, `test_b23_m5_fixes.py`, `test_b23_coverage.py`, then one contract per review round, `test_b23_round2.py` to `test_b23_round9.py`. Two earlier keeps moved to the drops in round 5, on purpose, and are marked in their files.
- **Before each round, the CEO proved the contract with a throwaway reference build and mutants** (`reference.md`). From round 5 on, that meant a full reference of the volume rule. It ends at 1,382 contract tests passing and 44 of 44 mutants caught.
- **From round 5, the CEO also ran a differential check:** Muse's code against the reference, on every contract label plus edge cases, read with each `per`. It found the round 6 gaps before the supervisor did. In rounds 7–9 the two agree on every check: 844, 884, then 916.
- **Muse wrote all the code:**
  - the timeline (`brief_html.py`, `schema/templates.py`, `schema/report.py`, `agent/session.py`);
  - the M5 fixes;
  - the shared SAM concepts and budget (`agent/loop.py`, `review.py`);
  - the volume rule in `providers/spark.py`;
  - its unit tests.
- **An independent Opus supervisor** reviewed every round: CHANGES seven times, then APPROVE for round 8, with two minors that round 9 took, then APPROVE again for round 9 (`supervisor.md`).
- **Gemini 4** (`gemini-4-argon` on Vertex) checked rounds 1 and 2 (`evidence/grills/m6-timeline/`, `m6-timeline-r2/`, both triaged).

**What the review rounds found:**
- **Rounds 1–3:** the volume rule was written as lists of wordings, and each review found syrup forms the lists missed:
  - the Arabic decimal sign, IU, cc and the Unicode slashes;
  - «لكل», spoons, and the volume-first "Each 5 ml contains";
  - Spanish and French, and a container's total.

  Each kept a 250 mg/5 ml syrup read as 250 mg per ml, a fivefold error. Also:
  - the call budget ran out with three SAM concepts;
  - `add_photo` used two concepts;
  - the timeline total didn't span the table;
  - the live guard counted retries against the loop budget, fixed in `scripts/intake_live.py`.
- **Round 4** replaced the lists with a clause rule. Its water exemption kept powder-for-suspension cartons ("250 mg/5 ml when reconstituted with water"), the commonest syrups in Egypt, and spoons printed without ml.
- **Round 5 turned the question around:** beside a dose volume, a strength is kept only when it is printed in the reading's own unit and not also printed beside the volume. A missing wording now loses a strength; it can't keep a wrong one.
- **Rounds 6–8 closed the refusal's gaps:**
  - abbreviation dots (`B.P.`, `Ph. Eur.`);
  - words or brackets between the amount and `per` (`250 mg (as trihydrate) per 5 ml`, `250 mg as amoxicillin trihydrate per 5 ml`);
  - dosing lines;
  - the Arabic dual and the colloquial spoon.

  They also stopped dropping insulin pens and drops whose own print follows the volume (`3 ml pen, 100 U/ml`).
- **Round 9 took the round 8 APPROVE's two minors:**
  - a tablet or capsule word between the amount and the volume means the volume is for dissolving, so effervescent, soluble and dispersible tablets keep their strength (`1000 mg effervescent tablet, dissolve in 200 ml`);
  - the colloquial dual «معلقتين» counts as a spoon.
- **The CEO's errors:** many of these bugs came from the SPEC's or the brief's own wording, and Muse built each exactly as written:
  - two concepts in `add_photo`, and plain "spoon" missing (round 2);
  - the volume-first `)` (round 3);
  - the water clause (round 4);
  - "at most three words (its unit, `base`, a salt)" and "`ملعقة` with any suffix" (round 6);
  - an exclusion for «مل» that would have lost «ملي», which a Muse unit case caught before the round 6 lock.

**Coverage it gives up, on purpose.** These fail closed, so the brief asks for the pack. SPEC §2 lists them all; the main ones:
- prefilled syringes and pens read per dose;
- combination strengths printed with one unit;
- two products on one label;
- an amount printed only after its volume ("Each ml contains 50 mg");
- a line break or a comma between the amount and the tablet word.

**Privacy:** the nine Muse exports carry no personal names; the one hit is inside base64. They show no reads of `evidence/raw/`. `muse-session.md` lists every tool call by its path or command only.

**Spend:**
- **Muse:** $1.90922, $1.02533, $0.93302, $1.47801, $2.31884, $1.17377, $0.87097, $0.48866 and $0.57724, so **$10.77506 for the batch** (estimated).
- **Gemini 4 checks on Vertex:** $0.61827.
- **Live calls:** none.

**Follow-ups:**
- **The first item for the follow-up batch:** apply the tablet-word carve-out only when the connector is `in` or `في` (supervisor round 9, #1). Every dissolving line uses one of those, and it closes syrup wordings like "250 mg = 1 tablet per 5 ml" and "250 mg tab/5 ml". No pack prints those wordings, but they keep a per-tablet reading.
- **A per-dose exemption for single-dose injectables,** worded so that an oral measuring syringe or a multi-dose pen can't use it.
- **The volume rule is now most of the 322 lines this batch added to `spark.py`.** A table-driven version with the word lists in one place would be easier to review.

**Next:** merge, then the Gemini 4 check of the merged batch on main.

Verdict: PASS
