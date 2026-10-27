# Batch 15.5 review: phone photos keep their provenance (+ QM M3 r2 #1)

Built-by: Claude Sonnet subagent (high effort), 3 rounds driven by the Opus 5.5 supervisor (see supervisor.md, builder.md)

Orchestrator: Claude Code (Opus 5.5). Inserted before B16 at Ahmed's request, on the worktree branch `batch/15.5-zoom`; `main` untouched. Gate: pass, 453 tests (421 before; the contract failed first, then went green; 10 builder unit tests added for gaps the supervisor found). Contract lock held.

Verdict: PASS (supervisor APPROVE)

## Why this batch exists
"The zoom problem" turned out to be a provenance bug. A live check on four staged 12 MP phone photos (`evidence/live/2026-10-27/zoom_before/`, $0.09) showed that SAM applies a photo's EXIF orientation and Spark does not: on a portrait photo, 2 of 3 labels were attached to the wrong pack and the third pack was never read. Offline, the crop-zoom refused every 90° photo and, on a 180° photo, cut the wrong pixels while keeping the region id. The code grill and the idea judge found the same weakness independently.

## What changed
- **Step 0, `prepare_image`** (`anamnesis/agent/media.py`): every photo is turned upright for all 8 EXIF orientations and stripped of all metadata (EXIF with GPS and camera tags, XMP, IPTC, ICC, comments, PNG text, extra frames such as an HDR gain map) before any model sees it. A clean upright JPEG or PNG passes byte for byte, so the frozen demo photo keeps its hash and region ids. JPEG and MPO stay JPEG (q95, 4:4:4); everything else becomes PNG. Deterministic and idempotent. Undecodable photos (HEIC without a converter, junk) are never sent to a model; the step log says so.
- **A region is read only from its own photo:** regions whose hash or frame don't match the prepared photo are dropped before ranking and never published; each leaves one step.
- **QM M3 round 2 #1:** nothing is logged after `budget_exhausted`, not even a failed crop.

## Checks
- Contract mutants (orchestrator): removing preparation fails 15 contract tests, removing the photo check fails 2, removing the exhaustion guard in `_zoom` fails 1.
- Supervisor: every round-1 fix reverted in a scratch copy fails exactly one test; 13 edge formats, the 4 staged photos and animated PNGs are deterministic and idempotent with no metadata left.
- Frozen demo path: `packs.png` is unchanged by preparation (`15595e0869ee`, as in the live reports).

## Process note
The supervisor and the orchestrator found the MPO case (phone HDR JPEGs opening as `MPO`, then re-encoded as large PNGs) independently; the contract had missed it. Lesson: test preparation against the file types phones actually write, not only the ones Pillow writes by default.
