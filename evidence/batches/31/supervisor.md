# Batch 31: the Opus supervisor

## Round 1 review (1 Nov): SUPERVISOR: CHANGES
Scope matches `briefs/31.md`; the locked files are untouched; 2,786 tests pass and ruff is clean. Every input below was run offline with the contract's own fakes.

1. **Major, the brief accepts a log from another review** (`brief.py:104-110`). It checks only that each step's `request_id` exists, and every review numbers its requests r1, r2, … Inputs run: a log from one run with the review of another (the header says "asked for 1, received 1" beside "Waiting for the patient: new photos requested 2"); the same log tripled ("asked for 3, received 3"); a forged step for another target. Fix: refuse a repeated id, a step whose target or kind differs from its request's, and an `answered` step whose request isn't answered.
2. **Major, a SPEC decision** (`review.py:210-215`, `templates.py:128-129`, `add_photo`'s supersede rule). Every unreadable target gets the same "this medicine pack" text, nothing tells the patient which pack is meant, and any reply that gives a reading replaces the target. Input run: photo 1 holds Concor and two dark packs; the patient gets the same text twice and sends two shots of the Beloc-Zok. Both dark packs are replaced, no unreadable finding is left, and `approve()` succeeds. Fix: pass the patient the pack's picture, or ask only for medicines mentioned but not photographed.
3. **Minor, `reply` gets the live request object** (`review.py:214-215`). Input run: a callback that sets `request.target_id = "o0"` makes the matched Concor pack get replaced, and the log disagrees with the review. Fix: pass a copy.
4. **Minor, contract gaps.** Three broken builds passed all 29 batch-31 tests: no approved check of its own, no `intake_id` check of its own (`request_photo` refuses first in both), and the header counted from the review rather than the log. Fix: run the refusals on a report with nothing to request, and add a brief case where the review holds more requests than the log.
5. **Minor, unit-test gaps.** Nothing pins "any other refusal propagates" (a build that logs every error as `duplicate` passes), one test still passes with the round `break` removed, and two checks repeat the contract.
6. **Minor, a SPEC gap:** an exception from `reply` after an answered photo throws the whole run away. Say what `reply` does on a failed channel. Spend is otherwise bounded by `max_rounds`.
7. **Minor, SPEC:** a target the clinician withdrew is asked again. Fix: count a withdrawn request as well as an open one.
8. **Minor, maintainability:** `follow_up` is 54 lines with three near-identical log blocks; the media check exists three times; duplicate detection matches an error-message string.

**The CEO's effect** (round 2):
- **#2:** the follow-up asks only for medicines the patient mentioned but didn't photograph. Their message names the medicine, so it can't be ambiguous, and a pack that couldn't be read stays with the clinician, as in batch 20.
- **#1, #3, #4, #7 and the round limit:** taken into the contract and SPEC.
- **#6:** SPEC says `reply` reports a failed channel by returning `None`, and that anything it raises propagates.
- **#5, #8 and the fresh Muse audit's three points:** go to Muse in the round 2 brief. The audit's points are a repeated target in one round, a non-integer `max_rounds`, and a named exception for a repeated photo.

## Round 2 re-check (1 Nov): SUPERVISOR: APPROVE
Every round-1 input now behaves correctly:
- the foreign, tripled and forged logs are refused;
- a retargeting `reply` changes nothing;
- the dark packs stay on the page, unread;
- a withdrawn medicine isn't asked again.

All 2,805 tests pass, ruff is clean and the locked files are untouched. The shared media check moved into `anamnesis/agent/loop.py` with no change in behaviour. Nothing in Muse's build has to change before merge.

1. **Major, the CEO's decision: existing reconciler behaviour that the follow-up can now reach** (`reconcile.py:457-524`, called for every answer). The patient said Concor 5 mg, and photo 1 shows Concor 10 mg, so `intake_differs_from_unit_strength` is in Disagreements. The follow-up asks only about Beloc-Zok, and the reply shows Beloc-Zok 50 and Concor 5 mg. Concor then pairs with the new 5 mg pack, the 10 mg pack becomes "Photographed, not mentioned", and Disagreements reads "None.". An intake given both photos at once gives identical findings: pairing is one-to-one, and a matching strength scores higher. Fix: a separate reconciler batch; for batch 31, state it in SPEC §8 and pin it.
2. **Minor, tests:** the skip for a medicine an earlier answer this round resolved is no longer pinned. Muse's code handles it, but deleting the skip still passes all 48 tests. Without it, the run raises after the patient was messaged and 3 calls were charged.
3. **Minor, SPEC choice:** a late reply (a `no_reply` step whose request the clinician later answers through `add_photo`) makes `render_brief` refuse the log.
4. **Minor:** a log naming the clinician's own `unreadable` request is credited to Anamnesis. The follow-up never makes such a request now, so refuse any step that isn't `not_photographed`.
5. **Minor, wording:** the `follow_up` docstring says "every missing photo", and the header line reads as complete while dark packs wait for the clinician. `render_brief` is 56 lines with the log check inline.

**The CEO's effect** (round 3):
- **#1:** SPEC §8 states it as a known limit, and the contract pins the invariant behind it: after the follow-up, the findings are those of an intake given every photo at once. A reconciler batch can report the losing pack of the same brand with its own type later.
- **#2:** pinned in the contract.
- **#3:** a `no_reply` or `duplicate` step may name a request that is now `answered` (a late answer); such a log can only understate "received".
- **#4:** taken.
- **#5:** the text names medicines mentioned but not photographed, the docstring is corrected, and the log check becomes a helper.
