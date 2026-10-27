# Batch 15.5 supervisor (Opus 5.5, high effort, read-only)

Prompt: `evidence/grills/BATCH_SUPERVISOR_PROMPT.md`. The supervisor was not told the orchestrator's opinion.

## Round 1: SUPERVISOR: CHANGES

1. **major** `anamnesis/agent/media.py`: Pillow opens a JPEG that carries an MPF second image (Ultra HDR and gain-map JPEGs from Pixel, Samsung and iPhone HDR exports) as format `MPO`, so a rotated or EXIF-bearing one was re-encoded as PNG with mime `image/png`. Ran it: the staged `drawer_portrait.jpg` saved as MPO grew from 1,749 KB to 6,637 KB as PNG, before base64 and once per SAM and Spark call. Fix: treat `{"JPEG", "MPO"}` as JPEG; unit test. *(The orchestrator had found the same case independently before this review.)*
2. **major** `anamnesis/agent/loop.py`: neither new `if not session.exhausted:` guard (undecodable-photo note, region-mismatch note) is covered. Ran it: with both replaced by `if True:`, all 443 tests still passed. Both paths are reachable. Fix: two unit tests.
3. **minor** `anamnesis/agent/loop.py`: `regions.update(...)` ran before the photo check, so a refused region was still published in `report.regions`, and a stale region reusing a real id could overwrite it. Fix: filter first.
4. **minor** `anamnesis/agent/media.py`: "clean" looked only at EXIF and XMP; a JPEG with a COM comment or ICC profile, or a PNG with a `tEXt` chunk such as `Location=39.47,-0.37`, came back byte for byte. SPEC says "drops all metadata". Fix: stricter rule, or narrow the SPEC. *(Orchestrator: stricter rule; SPEC §4 step 0 now lists every kind.)*
5. **minor** `anamnesis/agent/loop.py`: `run_intake` about 58 lines with 4-level nesting; the prepared bytes were re-hashed per region. Fix: hash once, a per-photo helper.

Checked and fine in round 1: the contract fails if the fix is reverted; offline probes kept region ids and hashes consistent, recorded all spend, and never turned a disagreement into `match`; preparation is idempotent on the 4 staged photos and 13 edge formats (CMYK, P with transparency, 16-bit grey, WebP, TIFF, animated GIF, truncated files); truncated and junk bytes raise `ValueError`; no scope creep; `tests/contract/` untouched.

## Round 2: SUPERVISOR: APPROVE
All five round-1 findings fixed, each with a test that fails when its fix is reverted (checked by reverting each fix in a scratch copy: exactly one test failed each time; the comment, PNG-text and clean-WebP tests also fail against the round-1 media code). The stricter clean rule is deterministic and idempotent on the 13 edge formats, the 4 staged photos and two animated PNGs; JPEG and MPO stay JPEG; animated PNGs become frame 0, which every model then sees. Ranking now picks only from regions that match the photo, so up to 3 good regions are read.

Minors (non-blocking):
1. `media.py`: the JPEG segment fallback `startswith(b"\xff")` lets a crafted APP1/APP9 payload such as `b"\xffLocation 39.47"` pass as clean (fail-open for crafted files; phones don't write it). Fix: strict marker + signature check, unit test.
2. `media.py`: the `n_frames == 1` check is untested (deleting it leaves 451 green). Fix: a 2-frame PNG test.
3. `loop.py`: mismatch steps are logged after the reads, so when the budget runs out during the reads a dropped region leaves no step. Logging them before the reads keeps the audit trail at no call cost. *(Orchestrator: taken; the guard on that note becomes unreachable and is removed.)*

## Round 3: SUPERVISOR: APPROVE (no findings)
Each round-2 minor reverted in a scratch copy fails exactly one test (crafted-segment JPEG, two-frame PNG, mismatch logged before the budget runs out); the unmodified copy passes 453. The removed exhaustion guard is unreachable: `exhausted` is only set where `session.call` returns `None` (over budget, or `SpendCapExceeded`, of which `SessionCapExceeded` is a subclass), so a segment call that returns regions never leaves the session exhausted. Nothing else changed.
