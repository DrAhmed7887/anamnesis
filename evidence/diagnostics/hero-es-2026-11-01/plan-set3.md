# The Spanish hero, third set (U13c): written before any call of this set (1 Nov, 16:21 CET)

- **Why:** the second set got 4 of 10, with 0 harmful (`results.md`, 956af17).
  - The cropped images read 20 of 20, and every miss was the brand "Emconcor" misheard in the synthetic Spanish voice ("Cocor", "Koncor", "Korcor", dropped, or written in Arabic script).
  - Ahmed chose a third set in which the patient says the generic name.
- **The only change: the patient says "bisoprolol" instead of "Emconcor".**
  - The script: "Tomo bisoprolol diez miligramos cada mañana y metoprolol cien miligramos dos veces al día."
  - It is made as the second set's note was: `say -v Mónica`, ffmpeg to 16 kHz mono 16-bit with no metadata, then 0.8 s of silence before it (`adelay=800:all=1`). The file is `evidence/raw/media/public/voice/U13c.wav`, sha256 52eacd67cf949f11…, 5.4 s.
  - The images are the second set's cropped fronts, unchanged.
  - **The evidence for the change:** batch 24's Spanish note S2 ("Tomo bisoprolol dos coma cinco miligramos por la mañana.") was transcribed with "bisoprolol" and matched (`evidence/batches/24/live.md`:13, :35).
- **Expected, as in `plan.md`, with the first claim now said by its ingredient:**
  1. Bisoprolol, 10 mg said once a day, against the Emconcor Cor 5 mg box: `intake_differs_from_unit_strength`.
  2. Metoprolol, 100 mg said twice a day, against the Lopresor 100 mg box: `match`.
  3. The beta-blocker note (`same_class`).

  The brief then pairs two generic names with two brand boxes.
- **The scorer:** `score.py` is unchanged. When a claim's name has no "concor", it finds the first claim by its ingredient, bisoprolol.
- **Harmful and risks:** as in `plan.md`.
  - A misheard "bisoprolol" can't ground the claim's ingredient, so that pair ends `unresolved_name`.
  - Label reading varies from run to run, though the second set read 20 of 20.
- **The command:** `scripts/intake_live.py --case U13c --repeat 10 --lang es`, with `U13c.wav` and the two `_front.jpg` images. `--cap` is the ledger total plus $0.80. The code is `main` as before: nothing under `anamnesis/` or `tests/` has changed since f50b8fb.
- **What happens next:**
  - If 5 or more of the 10 count, U13c becomes the hero of the film and the README, with its count. The first two Spanish sets are reported beside it.
  - If fewer, U12 stays the film's hero, and all three Spanish sets go into the README.
  - There is no fourth set.
- **Spend:** about $0.35 of Meta. Before it, Meta stands at $82.35 of the $100 line.
