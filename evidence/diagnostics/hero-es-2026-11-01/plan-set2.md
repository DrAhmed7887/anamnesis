# The Spanish hero, second set (U13b): written before any call of this set (1 Nov, 16:04 CET)

- **Why:** the first set got 3 of 10, with 0 harmful (`results.md`, fb498b7), under the plan's line of 5. Both causes were in the media. Ahmed chose to fix the media and run ten more.
- **The only changes, both to the media:**
  1. **The voice note gets 0.8 s of silence before it** (`evidence/raw/media/public/voice/U13b.wav`, sha256 05fd80d041ab2d23…, 5.2 s). This is `ffmpeg -af adelay=800:all=1` on `U13.wav`, so the speech is the same samples. In the first set the note started at its first sample, and no transcript had its first word.
  2. **Each registry image is cropped to its box's front face,** as a patient would photograph it. The rotated side panels, with their small print and lot fields, are dropped, and so is most of each top flap. In the first set the reader marked these images partial in 4 runs.
     - `emconcor_cor_5mg_es_front.jpg` is pixels (345, 156)–(692, 478) of `emconcor_cor_5mg_es.jpg`: 347×322, sha256 ee726f8b6a51effc….
     - `lopresor_100mg_es_front.jpg` is (380, 126)–(745, 510) of `lopresor_100mg_es.jpg`: 365×384, sha256 020d7e5597e73d29….
     - A sliver of each top flap's text stays at the crop's top-left corner, because the flaps are slanted.
- **Everything else is as in `plan.md`:**
  - the script, the code (`main`, with nothing under `anamnesis/` or `tests/` changed since f50b8fb) and the default path;
  - the expected findings, the harms, the risks and `score.py`. The scorer now takes the set's case id, with the same rules.
- **The command:** `scripts/intake_live.py --case U13b --repeat 10 --lang es` with `U13b.wav` and the two `_front.jpg` images. `--cap` is the ledger total plus $0.80.
- **Reported, both sets:** the first set stays as it came out. The README and the claims give each set's count.
- **What happens next:**
  - If 5 or more of the 10 count, U13b becomes the hero of the film and the README, with its count, and the first set's beside it.
  - If fewer, U12 stays the film's hero, and both Spanish sets go into the README.
- **Spend:** about $0.45 of Meta. Before it, Meta stands at $82.07 of the $100 line.
