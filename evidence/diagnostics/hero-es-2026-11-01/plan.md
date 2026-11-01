# The Spanish hero, U13: written before any call (1 Nov, 15:53 CET)

- **Why:** Ahmed, 1 Nov: "we need better since we use spanish and german". The hero so far, U12, used a Concor box sold in China and a Czech Bloxazoc box. Anamnesis's language work is in Spanish and German (batch 24), so the film's hero should show packs from there.
  - Germany has no open source of pack images: BfArM's data is closed, and Wikimedia Commons has no German bisoprolol or Beloc-Zok box (searched 1 Nov). So the new hero is Spanish.
  - Ahmed chose a Spanish voice note and the registry's own pack images.
- **The media:**
  - `evidence/raw/media/public/cima/emconcor_cor_5mg_es.jpg` (sha256 c140de552854a750…, 1024×576). AEMPS CIMA's pack image for Emconcor Cor 5 mg comprimidos recubiertos con película (nregistro 63048, Merck S.L.), https://cima.aemps.es/cima/fotos/full/materialas/63048/63048_materialas.jpg, dated 21 Mar 2018 in CIMA. The box prints "Emconcor® Cor 5 mg", "Fumarato de bisoprolol" and "28 comprimidos recubiertos con película".
  - `evidence/raw/media/public/cima/lopresor_100mg_es.jpg` (sha256 e2b7ba3c3e9267b0…, 1024×576). Lopresor 100 mg comprimidos recubiertos con película (nregistro 54503, Casen Recordati S.L.), https://cima.aemps.es/cima/fotos/full/materialas/54503/54503_materialas.jpg, dated 2 Feb 2018. The box prints "Lopresor® 100 mg", "Metoprolol, tartrato" and "40 Comprimidos".
  - `evidence/raw/media/public/voice/U13.wav` (sha256 4371410b82dbbf7b…, 4.4 s). macOS `say -v Mónica`, then ffmpeg to 16 kHz mono 16-bit with no metadata, as `scripts/make_es_de_media.sh` does. The script: "Tomo Emconcor diez miligramos cada mañana y metoprolol cien miligramos dos veces al día." It is never played in the film.
  - **Why "metoprolol" and not "Lopresor":** Lopresor isn't in the catalogue, and a claim's ingredient that the patient didn't say becomes null (SPEC §2, batch 24). So a claim said only as "Lopresor" would end `unresolved_name`. Patients in Spain often name a generic by its ingredient, and the box carries the brand. This was decided from the code, before any call.
  - **Licence:** AEMPS's legal notice allows its content to be reproduced when the source is named and the date of its last update is given (aemps.gob.es, Aviso legal, read 1 Nov 2026). The film credits both images that way.
- **What:** ten runs in one sitting with `scripts/intake_live.py --case U13 --repeat 10 --lang es`, each with the voice note and both images. It runs on the default path: Spark 1.3 extracts the claims and reads the labels, with no second reader. `--cap` is the ledger total plus $0.80.
  - **The code:** `main` at the commit that adds this plan. Nothing under `anamnesis/` or `tests/` has changed since batch 31 merged (8ee370a).
- **Expected, with the system's own categories** (as in the 31 Oct final ten, `evidence/diagnostics/hero-final-2026-10-31/`):
  1. Emconcor, 10 mg said once a day, against the 5 mg box: `intake_differs_from_unit_strength`.
  2. Metoprolol, 100 mg said twice a day, against the Lopresor 100 mg box: `match`.
  3. Across medicines, the beta-blocker note (`same_class`): bisoprolol and metoprolol.

  A run counts when all three appear. `score.py` in this folder scores it, written with this plan.
- **Harmful:** a `match` on Emconcor, or a readable pack shown with a strength its box doesn't print (bisoprolol 5 mg, metoprolol 100 mg). Expected 0.
- **Known risks, each failing safe, each reported:**
  - Voice Transcribe may write "Emconcor" as "Concor" (row 4.27, S1). Both resolve to bisoprolol, so no finding changes.
  - A misheard "metoprolol" can't ground the claim's ingredient, so that pair ends `unresolved_name`.
  - The reader is told to name each ingredient by its English INN. If it writes a Spanish salt name anyway ("fumarato de bisoprolol", "metoprolol tartrato"), the alias table lacks it and that pair abstains.
  - Label reading varies from run to run (row 4.29).
- **Spend:** about $0.50 of Meta; U12's runs cost about 4 cents each. Before it, Meta stands at $81.63 of the $100 line.
- **What happens next, whatever the count:**
  - U13 becomes the hero of the film and the README, with its count beside it. U12's sets stay in the record as they ran.
  - If fewer than 5 of the 10 count, the choice goes back to Ahmed before the film changes.
