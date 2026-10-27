# Batch 19 supervisor (Claude Opus 5.5, high effort, read-only)

Prompt: `evidence/grills/BATCH_SUPERVISOR_PROMPT.md`. The builder was Muse Code (`muse-spark-1.3`). The supervisor is a different model family and was not told the CEO's opinion. It probed offline, in scratch copies of the code from before and after the batch.

## Round 1: SUPERVISOR: CHANGES
1. **major** `anamnesis/brief.py` `_STYLE` and the `<rect>` markup. The SVG boxes have no fill or stroke, so each one fills solid black by default and paints over the pack it marks: the photo the clinician should check against is hidden. Seen by rendering `figure#photo:1` of the contract showcase as a standalone SVG. Fix: an outline-only box with a transparent fill, so the whole box stays clickable.
2. **major** `anamnesis/brief.py` `_SCRIPT`. Every click adds another `timeupdate` listener, and one is removed only when its own end time is reached. Clicking turn A, then a later turn B, lets A's listener pause B straight away (simulated in Node: turn-0, then turn-2 at 1 s, paused at 9.25 s). Fix: one listener with a shared end time. Deleting `audio.pause()` passes the whole suite.
3. **major** `anamnesis/brief.py` `render_brief`, `coverage_lines`. Nothing ties the report to the photos and audio it is rendered with, though `intake_id` exists for exactly that. The showcase report rendered with a different recording is accepted, so the turns play against the wrong audio. With a different photo it is also accepted: 4 links point nowhere, and coverage says, wrongly, "Photo 1: not examined; the call budget ran out first." Fix: recompute `intake_id` with the loop's own preparation and refuse a mismatch. This also removes the brief's second and third copies of photo preparation.
4. **major** (in the reconciler before this batch; a SPEC decision) `anamnesis/core/reconcile.py` `reconcile_all`. Sorting by score before the brand preference can still hide a disagreement. Claim "Panadol" 1 g, packs "Panadol 500 mg" and "Gelocatil 1 g": the result is `c1:o1 match`, Panadol's claim against Gelocatil's pack, while the Panadol pack becomes "photographed, not mentioned". The same happens before the batch. Ranking the same brand ahead of the score gives `c1:o0 strength_mismatch`, and all 628 tests still pass.
5. **minor** `anamnesis/brief.py` heading. `splitlines()[0]` gives an empty `<h3>` for a label that starts with a blank line ("\nNorvasc 5 mg").
6. **minor** `anamnesis/brief.py`. Some fixed text is outside `templates.py`, so no advice test sees it: "Units per intake", "Intakes per day", "As needed", "yes"/"no", " per ", and the alt texts. This goes against brief item 5 and SPEC §7. It is advice-free today.
7. **minor** Test gaps. The plain-decimal unit test compares a Decimal with itself. These mutants pass the suite although the code is correct today: the pack country unescaped, the `turn_id` attribute unescaped, `all` replaced by `any` on segment errors (a photo whose first concept errors and whose second finds nothing must read "no pack found"), and the 2+ members rule dropped (Concor + "bisoprolol" would gain a `same_class`).
8. **minor** Shape. `overlap.py` imports `_claim_identity` inside the function. In `across` the link text is the turn id, where SPEC says the claim's `name_text` is the link. `_section_of` has a dead branch.

Mutations caught: brand preference removed, reply schema not counted, rect without +1, transcript unescaped, discontinued claims counted, label unescaped, crop margin 0.2. Survived: JS pause removed, country unescaped, any-for-all on segment errors, 2+ members rule dropped, `turn_id` attribute unescaped.

**CEO triage:** all 8 accepted; #1–#4 block the merge.
- **New contract cases for round 2**, in `test_b19_brief.py`:
  - #3: the brief refuses media the report wasn't made from (another recording, another photo, no audio, photos in another order);
  - #4: a named brand is compared with its own pack first, a SPEC §3 change;
  - #5: the heading skips blank lines;
  - #7: the four surviving mutants;
  - amounts with no trailing zeros ("100.0" prints as "100", the safe-notation rule for doses).
- **#1 and #2 are checked by eye in a browser after round 2.** The suite can't run CSS or JavaScript; Muse adds unit pins.
- **#6 and #8 go into the round brief.**
- **The CEO's own browser check**, rendering both synthetic live intakes with round 1's code, found #1 independently and six more layout defects. All go into round 2: the page scrolls sideways on a phone (382 px screen, 573 px page); evidence links run together; turns don't look playable; crops have no captions; there's no visible title; Arabic source text has no `dir="auto"`.

## Round 2: SUPERVISOR: APPROVE
All eight round-1 findings are fixed. The supervisor reran each of its failing inputs on the round-2 tree:
- **Boxes:** outlines.
- **Playback:** the Node simulation passes. One `timeupdate` listener; turn-2 clicked during turn-0 keeps playing and pauses at 13 s; an evidence link plays its turn.
- **Wrong media:** another recording, another photo, no audio, a duplicated photo list and a changed image mime are all refused by both functions.
- **Pairing:** "Panadol" 1 g is a `strength_mismatch` with its own pack (before the batch: `match` with Gelocatil's). A brute-force run of 1,944 two-claim, two-pack paracetamol cases found no order dependence.
- **Heading:** the blank-line label gives "Norvasc 5 mg".
- **#6–#8:** done.

Hostile turn ids, labels and audio mime produce no new tags, no `on…` attributes and no dangling links. The output is identical across hash seeds.

1. **minor** `anamnesis/brief_html.py` `_SCRIPT`: no test runs the playback script, so these mutants pass the suite: `audio.pause()` deleted, the end time never set, link playback removed. The behaviour is correct today (Node, and the CEO's browser check).
2. **minor** Nothing tests `dir="auto"`: stripping it from every `<dd>` passes the suite.
3. **minor** Leftovers: the `reconcile_all` docstring still says "by score"; `FIELD_EVIDENCE` is unused; `_photos_html` still skips (`continue`) a region whose photo wasn't prepared, which a report from `run_intake` can't reach now that the intake check runs.

Mutations caught: country unescaped, any-for-all on segment errors, 2+ members rule dropped, `turn_id` attribute unescaped, intake check removed, score before brand, rect fill rule removed, img max-width removed, trailing zero kept, heading from the raw first line. Survived: the three JS mutants and `dir="auto"` removed.

**CEO triage:** all three accepted, none blocking; they go into the next batch's contract.
- The playback behaviour is verified twice: in Node by the supervisor, and in a real browser by the CEO with real clicks on a 4-turn, 16 s recording.
- Turn 1, then turn 3 mid-play: turn 3 kept playing (10.97 s) and stopped at its end (13.22 s for a 13.0 s end).
- An evidence link to turn 2 played from 4 s.
