# The Spanish hero, fourth set (U13d): written before any call of this set (1 Nov, 20:44 CET)

- **Why a fourth set:**
  - Set 3 (9 of 10, `results.md`) stays the registered result. `plan-set3.md` said there would be no fourth set, and this one isn't a second try at that score.
  - Ahmed wants the film to play the patient's voice note (1 Nov, evening). Set 3's note is a macOS `say` voice, which the macOS licence keeps out of any published file (`docs/CLAIMS.md` §8). A note made with ElevenLabs can be played, and the film may play only a note that was tested, so this set tests one.
- **The only change: the voice.**
  - The script is set 3's, word for word: "Tomo bisoprolol diez miligramos cada mañana y metoprolol cien miligramos dos veces al día."
  - It is read by the ElevenLabs voice-library voice "Rosa" (peninsular Spanish, `eleven_multilingual_v2`), made by `make_voice_set4.py` like set 3's note apart from the voice: 16 kHz mono 16-bit with no metadata, after 0.8 s of silence. The file is `evidence/raw/media/public/voice/U13d.wav`, sha256 96188b57db9c02a8…, 7.7 s (about 6.9 s of speech, against about 4.6 s in set 3's note).
  - The images are set 3's cropped fronts, unchanged.
- **Expected:** the three findings of `plan-set3.md`: bisoprolol `intake_differs_from_unit_strength` against the Emconcor Cor 5 mg box, metoprolol `match` against the Lopresor 100 mg box, and the beta-blocker note.
- **The scorer:** `score.py`, unchanged, run with the case id U13d.
- **Harmful and risks:** as in `plan.md`. The slower read gives Voice Transcribe more room to repeat a word, as in set 3's r02 and r10.
- **The command:** `PYTHONPATH=. uv run python scripts/intake_live.py --case U13d --voice evidence/raw/media/public/voice/U13d.wav --photo evidence/raw/media/public/cima/emconcor_cor_5mg_es_front.jpg --photo evidence/raw/media/public/cima/lopresor_100mg_es_front.jpg --lang es --repeat 10 --cap 18.28`: the adapter ledger's $17.48 plus $0.80. The code is `main`: nothing under `anamnesis/` or `tests/`, and nothing in `scripts/intake_live.py`, has changed since f50b8fb.
- **What happens next:**
  - Set 3 stays the README's Spanish hero result. Set 4 is reported beside the three sets, with its count, whatever it is.
  - If 5 or more of the 10 count, the film plays U13d's note and shows the first counted U13d run in its test scenes, and the film's results give set 4's count too.
  - If fewer, the film keeps set 3's run and plays no patient voice.
  - There is no fifth set.
- **Spend:** about $0.30 of Meta. Before it, Meta stands at about $82.65 of the $150 credit with the grills, and the line is $100.
