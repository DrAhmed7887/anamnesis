# Anamnesis

A pre-visit telehealth intake agent for the Meta Global AI Developer Hackathon (Oct–Nov 2026). Patients send a voice note and photos of their medicine packs. Clinicians get a one-page brief in which every fact links back to the audio turn and the image region it came from.

- Contract: [`SPEC.md`](SPEC.md)
- How it was built: [`evidence/`](evidence/). Each batch has its brief, the builder's log, an automated gate and a review. Each milestone has its Muse Code and Astra grills, plus an `effect.md` table of what they changed.
- Run the tests (offline, no keys): `uv run pytest`

All data is synthetic. This is not a medical device and gives no medical advice.
