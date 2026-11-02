# M8 audit by Muse Code (28 Oct evening): what changes

Muse Code (`muse-spark-1.3`) ran headless, read-only, in its own worktree, on `main` at 7abdd89, with contributor mode off and no foreign personal context. The brief is `brief.md`, the reply `muse.md`, the goal record `goal.md` and the cost `usage.json`.

- **How it worked:**
  - It pinned the audit as its goal with its goal tool.
  - It wrote a seven-step plan before opening any code, and kept to it ("No plan changes").
  - It closed the goal complete. 31 of its 32 main-agent model calls ran under the goal (`goal.md`).
  - It read the 15 `effect.md` files first, then traced the code. It couldn't run the tests, because its worktree has no `.venv` and installs were barred, so it read them instead.
- **Its verdict:** `AUDIT: 7 findings (0 blockers, 0 majors)`. Every finding was checked against the source before triage, and all 7 hold.
- **Two slips in its own summary:**
  - It says today's `main` never ran end to end live. Tonight's U1–U8 runs did, but they are in `evidence/live/2026-10-28/`, which it didn't open.
  - It puts the real-media runs on Wednesday. They are on Thursday.
- **Cost:** $1.18937 (estimated, from Muse's billing records). Meta now stands at $30.27 of $150.

| # | Area | Decision | What changes |
|---|---|---|---|
| 1 | demo path | **Taken.** | `intake_live.py` refuses a negative `--top-k` before any call. SAM's `top_regions` refused it only mid-run, after the transcription, claim and segmentation calls had been charged, and no report was written. |
| 2 | demo path | **Taken, before any R run.** | The manifest's R6 note said a dropped intake range gives `match`. SPEC §2 drops the strength together with it, so a range gives `insufficient_information`, a miss that fails safe. The note is corrected, and R6's expected findings stay as they were. |
| 3 | demo path | **Taken, before any R run.** | R3's note now gives the call budget as batch 23 made it: 2 + (3 concepts + 2 × top_k) per photo, so 11 here. It also adds what Muse didn't say: only the 3 most confident regions are read, so on the shelf photo a mentioned pack outside them is a miss. |
| 4 | demo path | **Taken, before any R run.** | New case R9: V1 + P2 + P3 in one intake, the only staged case with two photos. It reuses photos already planned, so it needs no extra recording. |
| 5 | spec vs code | **Taken.** | `reader_eval.py`'s docstring still named the old, wider folders after M7 #6 narrowed the check. It now names the three allowed folders. |
| 6 | spec vs code | **Taken, as SPEC wording.** | SPEC §2 said a country is kept "only as an ISO 3166-1 alpha-2 code", but the code keeps any two letters. SPEC now says that. The code is unchanged. |
| 7 | safety | **Taken.** | `intake_live.py` re-writes every voice note to its audio frames alone before any call, so no metadata chunk is sent or embedded in a brief. `docs/DATA_HANDLING.md` records the rule. |

**#7 in detail:**
- **The existing WAVs:** both carried a `LIST` chunk. It held only ffmpeg's encoder tag (`Lavf62.12.100`), no personal data.
- **The test:** a crafted WAV with a made-up name in a `LIST` chunk. After the re-write the chunk is gone and the audio is identical, as it is for the existing voice notes.

**Nothing goes to batch 24 from M8.** Every fix was in the engine's own scripts and documents.
