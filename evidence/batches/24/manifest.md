# Batch 24: the Spanish and German live cases, expected results pre-registered

**Status:** written 29 Oct 2026, before any call on these cases. It is committed before the first live call, and the commit order is the proof. After that the expected results don't change, and a run that disagrees is reported as a miss.
- **The plan:** `evidence/grills/plan-2026-10-29/plan.md` §3, as triaged in `effect.md` (#9 and #12), with Ahmed's go.
- **One correction to the plan's table:** S1 is `unresolved_name`, not `missing_modality`, until batch 24b. Batch 24a drops an INN the patient didn't say, and Emconcor is outside the catalogue until 24b adds it.

**What the cases test:** the Spanish and German path, end to end, on the code after batch 24a merges.
- Voice Transcribe on Spanish and German speech;
- the claim extractor on those transcripts;
- batch 24a's number words and its grounding of ingredient fields;
- the photo path on four Commons packs.

English and Egyptian Arabic stay the tested core. These 8 cases are a first check: n = 8, descriptive only.

## Run conditions
- **Code:** `main` after batch 24a's merge, with the commit recorded in the results. Batch 24b (Emconcor, Sortis, Nolotil) isn't merged yet.
- **Spend check first:** `uv run python scripts/spend_check.py --next meta=0.60`.
- **One intake per case:** `PYTHONPATH=. .venv/bin/python scripts/intake_live.py --case <id> --voice evidence/raw/media/public/voice/<id>.wav [--photo <file>] --lang es|de --cap <ledger total before the first case + 0.60>`.
- **Spend:** at most $0.60 for the 8 cases.
- **No retries for a better result.** A run stopped by an error is reported as that error. It may run once more, with the reason noted.
- **After batch 24b, if it merges:** S1 and G3 run once more on the code after 24b, with the expectations below. That's 2 more intakes.

## Media
- **Voice notes:**
  - made with `scripts/make_es_de_media.sh`: macOS `say`, voice Mónica (es_ES) for S1–S4 and Anna (de_DE) for G1–G4, 16 kHz mono 16-bit WAV, with no metadata;
  - Mónica, not the plan's Flo: Mónica is macOS's standard Spain-Spanish voice, and Flo one of its novelty voices;
  - Mónica's output is identical on every build. Anna's differs between builds (tested twice). So the files below are the ones used, and the script isn't rerun before the runs.
- **Photos:**
  - four Wikimedia Commons files, already in `evidence/raw/media/public/` and checked by eye in batches 21 and 22;
  - two of their file names are wrong (batch 22, `preregistration-notes.md`): `bisoprolol_2_5mg_sandoz_es.jpg` is Bisoprolol Orion 2,5 mg, printed in Finnish and Swedish, and `metoprolol_50mg_ratiopharm_de.jpg` is Baltic packaging. The key follows the printed pack.
- **Data handling:** `docs/DATA_HANDLING.md`, as amended in this commit. The notes and photos go only to Meta's Model API, and the notes never appear in the video or a hosted brief.

| File | SHA-256 |
|---|---|
| `voice/S1.wav` | `b8a5ffbec548bb9f0512555491d4e9cc7e20055ab3250c69fefef7c987f652dc` |
| `voice/S2.wav` | `d4e9b9cef82148c1448b764b59ec63beff80b87f98738b036ea0d4605c4e89bb` |
| `voice/S3.wav` | `662715087ce6033aab7e803a205ead2ab7a8abe4d9bea71566dcfc3b7e2ac262` |
| `voice/S4.wav` | `0a277601b2d72bd776e14f05831fb322f2d671afca42b792a8426c8a49cbce06` |
| `voice/G1.wav` | `7730fb786336cc0eae80926bd33ebb5fb48406038321c3ef40fc7a9a8bc4465a` |
| `voice/G2.wav` | `be2eb8c99a4a0e19af0ae7e348e7ba00764fef4c281cca1f9347dea4a172ac0c` |
| `voice/G3.wav` | `d0ddd740e6758c574308c4f778e718dece95db9bb8ae6291d0dc12452fcb4731` |
| `voice/G4.wav` | `5ebdc87ece7d96e9d784789747596031958712cc8c85e7bff2169b525484e498` |
| `gemini-commons/bisoprolol_2_5mg_sandoz_es.jpg` | `580ccf7ce33d5b6a0605768198d1295f1a79d80ea56294d412b7eaead65a13b7` |
| `gemini-commons/metoprolol_50mg_ratiopharm_de.jpg` | `ed50302abb08e17c96336267f0dd2bc33857db506d1ffb0a58074ea1fabc46b3` |
| `commons/panadol_500mg_fi.jpg` | `891c62e0e206d294d7a13bed5ca0dc8eaaa9c738400327bb77b3fe468b2d06e8` |
| `commons/sortis_40mg_cz.jpg` | `2663adb47c781b009f29ca2a9b647a6decb9ae7a54467c21359302b190e901eb` |

## Scoring
Scoring works as in batch 21.
- **The findings decide correct or miss.** A case is correct only if each listed finding appears with that type on that claim–pack pair, and nothing extra appears. Where the table lists an abstention as also correct, it counts as correct.
- **The claim is scored separately:** its name, amounts and listed regimen fields, and its status. An amount the product dropped is a miss on the claim, not a harmful one.
- **The transcript is scored separately:** the medicine name and every number must appear in it, as words or as digits. Which form came back is recorded, because only words exercise batch 24a's number words.
- **Harmful:** a false `match`, or a wrong strength or ingredient shown as fact. Abstaining (`unreadable_source`, `insufficient_information`, `unresolved_name`) is never counted as harmful.

## The rules the expectations rest on
SPEC §3, with batch 24a. `expected_check.py` runs the reconciler on each case's likely claim and pack shapes, with no model call; its output is `expected_check.out`.
- **An unsaid INN is dropped** (batch 24a, "Ingredient fields are grounded"). So "Emconcor" and "Sortis", outside the catalogue until batch 24b, can't resolve through an INN the model adds.
- **An INN said as the name resolves** ("bisoprolol", "Metoprolol", "Ibuprofen"). Release and splittability are implied only by a brand name (SPEC.md:157).
- **Leftovers:** a claim whose name can't be resolved gives `unresolved_name`; any other leftover claim gives `missing_modality`.
- **A pack read as `partial` can't pair.** It gives `unreadable_source`, and its claim is left as `missing_modality`.
- **Half a tablet** of a product with unknown splittability gives `insufficient_information` (rule 8). Panadol's splittability is unknown in the catalogue.

## Cases
| Case | Voice note | Photo: what it prints (source, licence) | The claim | Expected findings | Also correct | Earlier readings of the photo |
|---|---|---|---|---|---|---|
| S1 | "Tomo Emconcor cinco miligramos una vez al día." | none | Emconcor; 5 mg; once a day; active; no INN | `unresolved_name` | | |
| S2 | "Tomo bisoprolol dos coma cinco miligramos por la mañana." | `bisoprolol_2_5mg_sandoz_es.jpg`: Bisoprolol Orion 2,5 mg, bisoprolol fumarate, in Finnish and Swedish (Commons, `File:Bisoprolol 2,5 mg.jpg`, CC BY-SA 4.0) | bisoprolol; 2.5 mg; active | `match` (bisoprolol 2.5 mg; the claim names no salt, so fumarate raises no conflict) | The pack `unreadable_source` and the claim `missing_modality`, if the reader judges the pack partial | Batch 22: Spark 1.3 read bisoprolol 2.5 mg |
| S3 | "Tomo Gelocatil de un gramo cuando tengo dolor." | none | Gelocatil; 1 g; as needed | `missing_modality` ("Mentioned, not photographed") | | |
| S4 | "Tomo medio comprimido de Panadol de quinientos." | `panadol_500mg_fi.jpg`: Panadol 500 mg, Finland; box and two tablets (Commons, CC BY-SA 4.0) | Panadol; strength 500 mg per tablet; half a tablet per intake; no intake amount | `insufficient_information` (half a tablet, splittability unknown) | `unreadable_source` and `missing_modality`, if partial | Batch 21, U4: 500 mg per tablet, both runs |
| G1 | "Ich nehme Metoprolol fünfzig Milligramm zweimal täglich." | `metoprolol_50mg_ratiopharm_de.jpg`: Metoprolol-ratiopharm 50 mg, metoprolol tartrate, Baltic packaging, no release form printed (Commons, `File:Metoprolol-ratiopharm.JPG`, public domain) | Metoprolol; 50 mg; twice a day | `match` (metoprolol 50 mg; tartrate raises no conflict) | `unreadable_source` and `missing_modality`, if partial | Batch 22: all three readers judged it partial; Spark 1.3 and Spark Open on Baseten read 50 mg |
| G2 | "Ich nehme morgens eine halbe Tablette Beloc-Zok hundert Milligramm." | none | Beloc-Zok; strength 100 mg per tablet; half a tablet per intake; no intake amount | `missing_modality` | | |
| G3 | "Ich nehme Sortis vierzig Milligramm am Abend." | `sortis_40mg_cz.jpg`: Sortis 40 mg, atorvastatin, Czech Republic; box and blister (Commons, CC BY-SA 4.0) | Sortis; 40 mg; no INN | The claim `unresolved_name`; the pack `missing_modality` ("Photographed, not mentioned") | The pack `unreadable_source`, if partial | Batch 21, U7: read once, then judged partial. Batch 22's intakes: `unreadable_source` with Spark 1.3 and with Spark Open |
| G4 | "Ibuprofen vierhundert habe ich abgesetzt." | none | Ibuprofen; 400 mg; discontinued | `missing_modality` ("Reported as stopped, not photographed") | | |

**After batch 24b, if it merges:**
- **S1:** `missing_modality` ("Mentioned, not photographed").
- **G3:** `match` (atorvastatin 40 mg). If the pack is read as partial: the pack `unreadable_source` and the claim `missing_modality`.

## Watch for
- **S1 and G3 test the grounding.** An INN the model adds ("bisoprolol", "atorvastatin") must be dropped. Before 24b, S1's `missing_modality` or a G3 claim `match` or `missing_modality` would mean an unsaid INN was kept (`expected_check.out`, the "pre-24a" rows).
- **S4 and G2: a computed intake.** The patient never says 250 mg or 50 mg. If the model computes one, the product drops it, and the strength with it ("a dropped claim amount takes the other one with it"). The finding stays as listed, but the claim misses its strength.
- **S2 and S4: the decimal comma and "medio".** These must survive the stated-amount check. Today "2,5 mg" already states 2.5.
- **G1:** "zweimal täglich" states no amount, so the count of two comes from the model alone.
- **Voice Transcribe:** Emconcor and Sortis aren't among the catalogue's keywords until batch 24b.
