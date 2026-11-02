# The Spanish hero, fifth set (U13e): written before any call of this set (1 Nov, 01:56 CET)

- **Why a fifth set:** set 4 (2 of 10, `results.md`) failed on name matching, not on the media: Voice Transcribe wrote "visoprolol" or joined the verb to the name ("Tomobisoprolol", "Tomovisoprolol"), and the catalogue matched names only as written. Ahmed chose to fix the code and re-test the same voice (1 Nov, evening). Batch 32 (SPEC §3, "Spanish speech") lets `b` and `v` match each other and accepts one attached form of *tomar* before a Latin-script name. It merged into `main` as af84dcc after its gate, the supervisor and the CEO's review. `plan-set4.md` said there would be no fifth set for that code; this set is on new code, so it gets its own plan, as the first hero's sets on later code did.
- **The only change: the code.** The voice note is set 4's file, unchanged: `evidence/raw/media/public/voice/U13d.wav`, sha256 96188b57db9c02a8…, read by the ElevenLabs voice "Rosa". The images are set 3's and set 4's cropped fronts, unchanged.
- **Expected:** the three findings of `plan-set3.md`: bisoprolol `intake_differs_from_unit_strength` against the Emconcor Cor 5 mg box, metoprolol `match` against the Lopresor 100 mg box, and the beta-blocker note.
- **The scorer:** `score.py`, unchanged, run with the case id U13e. It finds the bisoprolol claim by its ingredient when the name has no "concor"; a claim heard as "Tomovisoprolol" is found through the catalogue, as the product now resolves it.
- **Prediction, written now:** the 8 runs of set 4 that missed did so on the name alone, so with the same transcriptions most runs should count. Other things can still miss: a repeated "dos" taken as a 2 mg intake (set 3's r10), or a name heard some third way.
- **Harmful and risks:** as in `plan.md`. A new risk of this code: a misheard word that matches a different catalogue product once `b` and `v` are folded. The catalogue has no such pair (a contract test checks it), and every pairing is reported.
- **The command:** `PYTHONPATH=. uv run python scripts/intake_live.py --case U13e --voice evidence/raw/media/public/voice/U13d.wav --photo evidence/raw/media/public/cima/emconcor_cor_5mg_es_front.jpg --photo evidence/raw/media/public/cima/lopresor_100mg_es_front.jpg --lang es --repeat 10 --cap 18.57`: the adapter ledger's $17.77 plus $0.80.
- **What happens next:**
  - Set 3 stays the Spanish hero's result on batch 31's code. Set 5 is reported beside the four sets, with its count, whatever it is, and its code named.
  - If 5 or more of the 10 count, the film plays this note (the note of sets 4 and 5), shows the first counted U13e run in its test scenes, and gives set 5's count with the other four.
  - If fewer, the film keeps set 3's run and plays no patient voice.
  - There is no sixth set.
- **Spend:** about $0.30 of Meta. Before it, Meta stands at about $84.38 of the $150 credit with the grills, and the line is $100.
