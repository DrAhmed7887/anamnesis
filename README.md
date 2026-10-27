# Anamnesis

A pre-visit telehealth intake agent for the Meta Global AI Developer Hackathon (Oct–Nov 2026). Patients send a voice note and photos of their medicine packs. Clinicians get a one-page brief in which every fact links back to the audio turn and the image region it came from.

- Contract: [`SPEC.md`](SPEC.md)
- How it was built: [`evidence/`](evidence/). Each batch has its brief, the builder's log, an automated gate and a review. Each milestone has its Muse Code and Astra grills, plus an `effect.md` table of what they changed.
- Run the tests (offline, no keys): `uv run pytest`

## Built with
**Meta models in the product** (live calls, each logged with its model id and cost in [`evidence/spend/ledger.jsonl`](evidence/spend/ledger.jsonl)):
- **Muse Voice Transcribe** turns the patient's voice note into timed turns.
- **SAM 3.1** finds each medicine pack in the photo: the region every pack fact links back to.
- **Muse Spark 1.3** extracts the patient's claims from the transcript and reads each pack label, both into strict JSON schemas.

**Meta tooling in the build:** from batch 16 on, all code is written by **Muse Code** (`muse-spark-1.3`, standard mode with contributor mode off). Each Muse session's tokens and cost are in [`evidence/spend/muse_ledger.jsonl`](evidence/spend/muse_ledger.jsonl) and `evidence/batches/<n>/usage.json`. Claude Code is the CEO: it writes the spec, the acceptance tests in `tests/contract/` (which Muse may not edit) and the reviews, and an independent Opus supervisor reviews every batch. Batches 1–12 were built with Codex and batches 13–15.5 with Claude Code ([`evidence/decisions.md`](evidence/decisions.md)).

**Partners:** Baseten's hackathon credit has been received. Muse Spark Open (open weights) on Baseten is planned as a second claim extractor for an open-weight comparison; it isn't used yet.

All data is synthetic. This is not a medical device and gives no medical advice.
