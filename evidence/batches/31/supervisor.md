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
