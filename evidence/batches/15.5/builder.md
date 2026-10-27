Claude Sonnet subagent (high effort), batch 15.5, 27 Oct 2026

## Round 1
Contract passes; 443 tests. Files: `anamnesis/agent/media.py` (new), `anamnesis/agent/__init__.py`, `anamnesis/agent/loop.py`.
1. `prepare_image` decodes with Pillow and raises `ValueError("image cannot be decoded")` on bad bytes; a photo with no EXIF and no XMP comes back as the same `(data, mime)`; otherwise `exif_transpose` and a re-encode into a fresh image with nothing from `info` carried over except PNG `transparency`; JPEG stays JPEG (quality 95, `subsampling=0`), anything else becomes PNG; the format is read from the decoded image, not the `mime` argument.
2. `run_intake` prepares all photos first (each size decoded once); SAM, every read, the crop and `intake_id` use only the prepared bytes and mime. An undecodable photo gets one `segment` step `error: image cannot be decoded` (no call ids, no provider call, no spend).
3. Before each read the region's sha256 and frame size are checked against the prepared photo; a mismatch logs a `read` step `error: region does not match the photo`, with no read and no zoom.
4. `_zoom` returns the original reading without cropping once the session is exhausted; the decode-error, region-mismatch and crop-failed steps are all skipped after `budget_exhausted`.
Brief ambiguity noted: "prepares every photo first" versus "not after budget_exhausted" for decode errors; resolved by preparing up front and logging each decode error at that photo's turn unless exhausted.

## Round 2 (supervisor round 1 findings)
451 tests; ruff clean. Files: `anamnesis/agent/media.py`, `anamnesis/agent/loop.py`, `tests/unit/test_zoom_extra.py` (new).
1. MPO counts as JPEG: re-encoded from the primary frame only, as JPEG, mime `image/jpeg`; never returned byte for byte. Unit test: MPO with orientation 6.
2. One unit test per exhaustion guard. Mutation check: replacing each guard with `if True:` fails exactly its test (1 failed, 450 passed, each time). The mismatch steps are now logged after the kept regions are read, so test (b) can see its guard.
3. `_read_photo` keeps only regions whose sha256 and frame match the prepared photo; only kept regions are ranked, read and published; each dropped region gets one `read` step `error: region does not match the photo` unless exhausted. Unit test: a stale region is never published.
4. "Clean" now means: a single-frame JPEG with no comment, no EXIF and only APP0 JFIF / APP14 Adobe segments, or a still PNG with no text chunks, EXIF, ICC or XMP. Everything else is re-encoded with only PNG transparency carried over. Unit tests: JPEG+comment, JPEG+ICC, PNG+tEXt, clean WebP → PNG. An animated PNG is re-encoded as a single frame (flagged to the orchestrator).
5. `_prepare` returns `(photo, size, sha)`, hashing once per photo; `_read_photo` holds the per-photo block; `run_intake` is 46 lines.

## Round 3 (supervisor round 2 minors)
453 tests; ruff clean. Files: `anamnesis/agent/media.py`, `anamnesis/agent/loop.py`, `tests/unit/test_zoom_extra.py`.
1. Strict JPEG check: every `applist` segment must be APP0 or APP14 with a payload starting `JFIF` or `Adobe`. Test: crafted APP1 (`\xffLocation 39.47`) and APP9 (`\xffGPS 39.47,-0.37`) segments come back re-encoded with no `39.47` in the bytes.
2. `n_frames` test: a 2-frame PNG (red, then blue) comes back different, single-frame, pixel (0, 0) red. Mutation check: removing the condition fails it.
3. `_read_photo` logs `error: region does not match the photo` right after segmentation, before any read; the unreachable exhaustion guard on that note is removed. Its unit test asserts the mismatch step comes before `budget_exhausted`, which is still the last step.
