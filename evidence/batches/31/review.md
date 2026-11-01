# Batch 31 review: the follow-up runs by itself (SPEC §8)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 3 rounds, planned first by a read-only Muse session and audited by a fresh one

Verdict: PASS

**What the batch adds:**
- **`follow_up`** (`anamnesis/review.py`): after the intake, Anamnesis asks the patient for a photo of every medicine they mentioned but didn't photograph, takes the replies through `add_photo`, and leaves the brief a draft for the clinician to approve.
  - Every message is the template that names the medicine.
  - Each round asks only what was pending at its start, for at most `max_rounds` (default 2) rounds.
  - A request the clinician opened or withdrew is left alone.
  - A reply gets a copy of its request.
  - A photo already given is logged `duplicate`, and the run never approves.
  - Code fixes what to ask, in what order and when to stop: no model chooses an action.
- **The log:** `FollowUpOutcome` and `FollowUpStep` (`anamnesis/schema/review.py`), and `PhotoAlreadyGiven` for a repeated photo.
- **On the brief:** `render_brief(..., follow_up=log)` adds "Anamnesis sent the follow-up itself, for medicines mentioned but not photographed: photos asked for {asked}, received {received}." It first checks that the log belongs to the review (`_check_follow_up_log`).

**Why:** Ahmed's call (1 Nov, 13:15) to strengthen the Best Agentic Use-Case bonus entry, which the guide judges on autonomy, effectiveness and practical usefulness. The Meta line went to $100 for it.

**Who did what:**
- **A read-only Muse session planned it** ($0.2012, `evidence/grills/b31-muse-plan/`). It proposed this loop plus a model that picks what to ask next or stops. The CEO took the loop and not the model choice (`effect.md` there): a model's stop is the one way the loop could leave evidence ungathered, and it would break "no model chooses an action".
- **The CEO** wrote the SPEC lines, the contract (22, then 43, 46 and 47 cases) and a throwaway reference build for each contract (`reference.md`): 22 of 22 with 8 of 8 deliberate breaks caught, 43 of 43 with 6 of 6, then 46 of 46. They were deleted afterwards.
- **Muse built it in three rounds:**
  - **round 1** ($0.96180): the loop as first specified, gate 2,786;
  - **round 2** ($1.15781): the review's fixes, gate 2,805;
  - **round 3** ($0.51118): the re-check's last points, gate 2,808.
- **A fresh read-only Muse session audited round 1** ($0.2461, `evidence/grills/b31-muse-audit/`): a sound build, with three minor points, all taken (a repeated target, a non-integer `max_rounds`, a named error for a repeated photo).
- **The Opus supervisor** (`supervisor.md`) found the major problem in round 1:
  - **What it was:** every unreadable pack got the same "this medicine pack" text, and any photo that gave a reading replaced it. Two dark packs could vanish behind two shots of another medicine.
  - **The fix:** the follow-up asks only for medicines mentioned but not photographed, and unreadable packs stay with the clinician.
  - **The rest of its findings:** it also found a log that the brief would credit from another review, a reply that could retarget its request, weak refusal tests, and withdrawn requests asked again. All were taken.
  - **Round 2:** it approved with five points, all taken in round 3. Among them is a known limit now stated in SPEC §8 and pinned: after the follow-up, the findings are those of an intake given every photo at once.
  - **Round 3:** approved. Its two minor points were taken by the CEO without another Muse round: a contract case for a step whose kind differs from its request's, and SPEC wording.

**The gate** (on the final contract, `7f7d544`): 2,809 tests pass, ruff is clean, and the contract lock holds.

**Usage:** Muse's three build rounds cost $2.63079 est. (`usage.json`, the Muse ledger). The read-only plan and audit cost $0.4473 more and are counted in `scripts/spend_check.py`. Meta stood at about $81.4 of the $150 credit, and the line is $100.

**Not in this batch:**
- the live run, which follows the merge, pre-registered;
- a reconciler change for the losing same-brand pack;
- a patient app: `reply` is a library callback, and in the demo the developer plays the patient.
