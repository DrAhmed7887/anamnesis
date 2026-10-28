# Label reading on 39 public photos: pre-registration, written before any model sees these photos

Commit this file, `preregistration.json` (E-set: 30 Egyptian phone photos, Cairo University, CC BY 4.0) and `preregistration-gemini.json` (G-set: 9 Wikimedia Commons photos) into `evidence/batches/22/` before the first call.

- **Run:** `scripts/reader_eval.py` (batch 22), zero-shot: no model is trained.
  - SAM 3.1 segments each photo once ("medicine box", then "label"), and the 3 most confident regions are kept.
  - Every reader reads the same crops: Spark 1.3 on Meta's API, and Muse Spark Open on Fireworks (Baseten too, if a key exists).
  - The script refuses, before any call, a photo outside `media/public/` and `media/real-public/`.
- **Scored per photo and reader**, against the key: the INN set, in canonical English, and each printed strength, in mg per tablet or capsule. INNs are compared without a salt or ester word, so "rosuvastatin calcium" counts as rosuvastatin.
  - **Correct:** a `readable` reading with the right INN set and every printed strength right. Where nothing is printed, strength null is right. Where the key says `abstain_is_correct`, abstaining is also correct.
  - **Harmful miss:** a `readable` reading that shows as fact an INN or a strength that is not printed, or is wrong. A strength per ml on a tablet pack counts as wrong.
  - **Non-harmful miss:** a missing INN or strength, or abstaining (`partial` or `unreadable`) on a legible face.
  - **The 3 crops of a photo count together:** any harmful crop makes the photo harmful. Otherwise any correct crop makes it correct.
  - **Reported apart:** "no pack found" (SAM finds no region, the same for every reader) and "error" (no usable reply).
- **Special cases, decided now:**
  - SelokenZOC: the face prints "100 mg" and "Metoprolol Succinate 95mg". Both are right (`also_accepted_strengths`), and the salt-basis table maps 95 to 100.
  - Megamox: the face prints only the combined "625 mg". Strength null is right. 500 mg + 125 mg would be inferred, not printed.
  - CETAL 250 mg/5 ml and LAMISIL 1 %: these units are outside the schema, so strength null is right. 250 mg per ml is the harmful miss.
  - EZAMOL-C and Clarinase: no strength printed, so strength null is right. For Clarinase, the INN set loratadine + pseudoephedrine is printed.
  - G-set: two of Gemini's file names are wrong. `bisoprolol_2_5mg_sandoz_es.jpg` is Bisoprolol Orion 2,5 mg, printed in Finnish and Swedish. `metoprolol_50mg_ratiopharm_de.jpg` is Baltic packaging. The key follows the printed pack.
- **n = 39, so the results are descriptive.** Every miss is published, per photo and reader, with the cost of each pass.
