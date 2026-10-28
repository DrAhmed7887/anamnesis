# Data handling for the staged real-media tests (batch 21)

Until now, Anamnesis has run only on synthetic media: rendered photos and macOS text-to-speech voices. Batch 21 adds the first real phone photos and a real human voice. This note sets the rules before anything is recorded (supervisor review of 27 Oct, item 9). It covers every photo and voice note used in tests, the demo and the video.

## What may be recorded
- **Packs.** Real medicine boxes and blister strips, photographed on a plain surface.
  - Prefer over-the-counter packs that Ahmed bought himself. Never use a family member's current prescription.
  - No pack with a pharmacy dispensing label, unless the label is fully covered with paper before the photo is taken. Covering means covering, not blurring afterwards.
- **Voice.** Only Ahmed's own voice, reading a fictional script.
  - The patient in the script is invented: the medicines, amounts and history are nobody's real history, Ahmed's included.
  - No other voices: no family, no children, no background conversation or TV.
- Ahmed records everything on his own phone and consents to sending it to Meta's Model API, as described below.

## What must never be in a photo or a recording
- Names, addresses, dates of birth, phone numbers, prescription or insurance numbers, pharmacy or prescriber names.
- Faces or other people, children, documents, screens, mail, house numbers, or anything that shows where the photo was taken.
- Real symptoms or diagnoses of a real person.

If something slips in, the file is retaken, never edited afterwards.

## Where the files live
- **Raw files** go to `evidence/raw/media/real/` on the Pro. That folder is git-ignored: no raw photo or recording is committed, synced to Drive or put in Notion.
- **Photos.** Before any model sees a photo, the pipeline turns it upright and strips all its metadata, GPS included (SPEC §4 step 0). Turning off Location for the camera is still recommended. iPhone HEIC files are converted to JPEG locally with `sips`.
- **Voice notes** are converted locally to 16 kHz mono WAV with their metadata removed (`ffmpeg -map_metadata -1`), the only format Voice Transcribe accepts.
- **Deletion:** after judging, on Ahmed's word, the raw files move to the Trash.

## What leaves the machine
- **Only to Meta's Model API**, on Ahmed's account:
  - the prepared photo and the crops cut from it, to SAM 3.1 and Muse Spark 1.3;
  - the WAV, to Muse Voice Transcribe.
- **Standard models only**, never a `*-contributor` id. Meta's pricing page says contributor mode lets Meta train on prompts, files and responses. Our notes (`docs/muse/`) don't record what Meta keeps in standard mode, so anything sent counts as having left our control.
- **Public test photos only, for the open-weight comparison (batch 22):** the Wikimedia Commons and Cairo University CC BY photos may also go to Fireworks or Baseten, to be read by Meta's open-weight Muse Spark Open. **Ahmed's own photos and voice never go there.**
- **The reviewers never see the media.** The batch supervisor (Claude) and the quality manager (Gemini) get code and text evidence only.

## What is committed or published
- **Committed:**
  - the expected results, written down before any model sees a file;
  - the transcripts of the fictional scripts;
  - each run's findings, cost and latency;
  - the summary tables.
- **Never committed:** photos, audio, crops, or a clinician brief that embeds them. Briefs stay in `evidence/raw/briefs/`.
- **Published only with Ahmed's yes:** a hosted demo brief or video that uses his voice or the real photos needs his explicit yes for that file.

## How results are reported
- As staged tests with real packaging and a fictional history. They are not a validation, not clinical use, and involve no real patient.
- The expected results come first, and every run is reported as it came out (correct, wrong or missed), failures included.
- Spend is capped at $1 on the Meta ledger for all staged runs (`SpendGuard`), and each intake has its own session cap.
