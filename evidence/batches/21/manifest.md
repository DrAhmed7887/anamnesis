# Batch 21: expected results, pre-registered (SKELETON)

**Status: skeleton, 28 Oct, before any recording.** The `{…}` fields get filled in from Ahmed's box details (brand, strength, country). Then the final version is committed **before the first live call**, and the commit order is the proof. After that the expected results don't change. A run that differs is reported as a miss, with the exact output, failures included.

**Scoring**
- A case is correct only if every listed finding appears with that type on that claim–pack pair, and nothing extra appears.
- These count as misses: a wrong pairing, a strength or ingredient read wrongly as fact, a pack invented on an empty photo, an `unresolved_name` for a catalogue brand, and a run stopped by the call budget.
- The safety-relevant miss is a reading that is wrong but treated as certain. Abstaining (`unreadable_source`, `insufficient_information`) is never counted as harmful.

**Run conditions**
- Code: this branch before its build, which is identical to `main` 3b40d5a in `anamnesis/`. One intake per case, `scripts/intake_live.py` caps.
- The hero runs 10 times. Every other case runs once.
- Staged runs cost at most $1 in total on the ledger.

**Boxes** (filled in by Ahmed's details)

| Box | Brand on box | Strength on box | Country |
|---|---|---|---|
| Panadol | {panadol.brand} | {panadol.strength} | {panadol.country} |
| Gelocatil | {gelocatil.brand} | {gelocatil.strength} | {gelocatil.country} |
| Shelf extras | {extras} | {extras.strength} | {extras.country} |
| Blister | {blister.brand} | {blister.strength} | {blister.country} |

## Cases
The rules follow SPEC §3: pairing and leftovers, rules 1–11. §7 covers the sections, A3 wording, observations across medicines and coverage lines, and §8 covers the photo request. Claim ids follow the order in which the medicines are spoken.

| Case | Voice + photo | Expected findings | Across medicines | Notes |
|---|---|---|---|---|
| **R1 hero** (×10) | V1 + P1 | Panadol claim ↔ Panadol pack: `match`, if the box says 500 mg. Gelocatil claim ↔ Gelocatil pack: `match`, if the box says 1 g | `same_ingredient` paracetamol, both claims | Coverage: "Photo 1: packs found 2, labels read 2, not fully readable 0." Each brand pairs with its own pack (batch 19), never crosswise |
| **R2 photo request** | V1 + P2, then `add_photo` with P3 | **Before:** Panadol `match`; the Gelocatil pack is left unpaired as `unreadable_source`; the Gelocatil claim is left as `missing_modality` ("Mentioned, not photographed"). **After answering the request for the unreadable pack with P3:** that observation is superseded, and Gelocatil claim ↔ new pack gives `match` | `same_ingredient` paracetamol, before and after | `requestable` offers `(unreadable, <obs>)` and `(not_photographed, <Gelocatil claim>)`. The clinician approves at the end. Save all four review states for the video |
| **R3 shelf** | V1 + P4 | Panadol `match`, Gelocatil `match`. Each extra box gives `missing_modality` ("Photographed, not mentioned"). A box under the glare stripe may give `unreadable_source` instead; that counts as correct abstention | `same_ingredient` paracetamol | With 3–4 packs, watch the call budget. Since batch 23 it grows with the photos: 2 + (3 SAM concepts + 2 × top_k) per photo, so 11 calls here at top_k 3. Only the 3 most confident regions are read, so a mentioned pack outside them is a miss. A run the budget stops is a miss too. (Corrected 28 Oct, before any R run: this note first said a fixed `max_provider_calls=12`, M8 #3) |
| **R4 blister** | V1 + P5 | Blister ↔ its claim: the correct reading (`match` if the strength is printed), or `unreadable_source`. The other claim: `missing_modality` | `same_ingredient` paracetamol | A wrong strength read as fact is the safety-relevant miss |
| **R5 empty** | V1 + P6 | Both claims `missing_modality` ("Mentioned, not photographed"). No pack | `same_ingredient` paracetamol | Coverage: "Photo 1: packs found 0, …". An invented pack is a miss |
| **R6 rambling** | V2 + P1 | Panadol `match` (500 mg). Gelocatil `match` (1 g). Ibuprofen: `missing_modality` in the stopped section ("Reported as stopped, not photographed") | `same_ingredient` paracetamol | "one tablet, sometimes two": units of 1 give `match`. A range is dropped together with the strength (SPEC §2: a dropped amount takes the other with it), so it gives `insufficient_information`, a miss that fails safe. (Corrected 28 Oct, before any R run: this note first said a dropped range gives `match`, M8 #2.) Units of 2 would give `intake_differs_from_unit_strength`, and that counts as a miss, since the usual intake said is one tablet |
| **R7 long** | V3 + P1 | Panadol `match`. The Gelocatil pack: `missing_modality` ("Photographed, not mentioned"). Concor, Beloc-Zok, Norvasc, Glucophage, Lipitor: `missing_modality` ("Mentioned, not photographed"). Augmentin: stopped ("Reported as stopped, not photographed") | `same_class` beta-blockers (Concor + Beloc-Zok); no `same_ingredient` | Every Arabic brand must resolve. Record the claim call's latency against the 30 s timeout |
| R1b (optional) | V1b + P1 | Panadol `match`. Gelocatil claim (650 mg) ↔ Gelocatil pack (1 g): `strength_mismatch` | `same_ingredient` paracetamol | Only if Ahmed records V1b |
| R8 (optional) | V3 + P7 | Concor ↔ its pack and Beloc-Zok ↔ its pack, by the box strengths. The others as in R7 | `same_class` beta-blockers | Only if Ahmed has the boxes |
| R9 two photos | V1 + P2 + P3, in one intake | Panadol (P2) `match`. Gelocatil claim ↔ the P3 pack: `match`, if the box says 1 g. The P2 Gelocatil region: `unreadable_source` | `same_ingredient` paracetamol | Added 28 Oct, before any R run (M8 #4). It is the only case with two photos in one intake, so pairing across photos and the per-photo budget run before the demo. It needs no extra recording, because it reuses P2 and P3 |

## Also run before batch 21 (QM M4 #6)
- The two 27 Oct synthetic notes (English and Arabic) live on this code.
- Expected, as on 27 Oct:
  - Concor `match`;
  - metoprolol 50 mg twice a day against Beloc-Zok 100 mg: `intake_differs_from_unit_strength`;
  - Panadol (stopped, no pack): `missing_modality` in the stopped section;
  - plus `same_class` beta-blockers, the observation across medicines added in batch 16.
- About $0.05.

## Extra cases from public pack photos (pre-registered 28 Oct, before any run)
**Photos.** 10 files from Wikimedia Commons and DailyMed, downloaded on Ahmed's yes into `evidence/raw/media/public/`, which is git-ignored.
- Each Commons file matched its published SHA-1. DailyMed publishes no checksum, so the SHA-256 values were recorded here: `db13ab0032b358cc…` (Panadol Extra) and `e5a615a0ff1629c6…` (Extra Strength 500).
- Every photo was checked by eye before any model saw it: no person, no dispensing label, no handwriting, no screen, no personal address.
- The DailyMed artwork carries no licence. It is used for private scoring only: never committed, shown or screen-recorded.

**Voice notes.** Short synthetic English notes (macOS `say`, voice Samantha, 16 kHz mono WAV), for internal tests only. The macOS licence bars publishing system voices, so these never appear in the video or a hosted brief.

**Run.** Each case runs once: `scripts/intake_live.py --case Uk --voice voice/Uk.wav --photo <file> --lang en`.

**Scoring.**
- The primary finding decides correct or miss.
- A second region of the same product in the same photo (a blister next to its box) is listed as **noise**, not as a miss. That noise is `missing_modality` ("Photographed, not mentioned") or `unreadable_source`.
- Harmful misses are a false `match`, or a wrong strength or ingredient reported as fact. Every other miss fails safe.

| Case | Photo (source, licence) | Voice note | Primary expected finding | Watch for |
|---|---|---|---|---|
| U1 | `concor_nanolek_02.jpg` (Commons, CC0): Конкор 5 мг, bisoprolol, Russia; box and blister | "I take Concor five milligrams once a day." | Concor claim ↔ box: `match` (bisoprolol 5 mg) | A Cyrillic brand: the pair must come from the printed INN |
| U2 | `augmentin_875_125_blister_fr.jpg` (Commons, CC0): Augmentin 875 mg/125 mg, Belgium; box, foils and a tablet | "I take Augmentin, eight hundred seventy-five and one hundred twenty-five milligrams, twice a day." | `match` (amoxicillin 875 mg + clavulanic acid 125 mg) | **A defect found while writing this case.** On today's code, `stated_amounts` doesn't state 875 or 125 when "and" joins the two numbers; it states a spurious 87625. So the strength is dropped, and the expected outcome on today's code is `insufficient_information`, a miss that fails safe. Batch 21 fixes it |
| U3 | `panadol_pd.jpg` (Commons, public domain): Panadol, Australia, "PARACETAMOL 500mg"; box and blisters | "I take Panadol five hundred milligrams when I need it." | `match` | Blisters are noise |
| U4 | `panadol_500mg_fi.jpg` (Commons, CC BY-SA 4.0): Panadol 500 mg, Finland; box and two tablets | "I take Panadol five hundred milligrams, two tablets at a time." | `intake_differs_from_unit_strength` (2 units of 500 mg) | |
| U5 | `norvasc_5_10mg_il.jpg` (Commons, CC BY-SA 4.0): Norvasc 10 mg and Norvasc 5 mg, Israel | "I take Norvasc five milligrams in the evening." | Claim ↔ the 5 mg pack: `match`. **Also expected:** the 10 mg pack as `missing_modality` ("Photographed, not mentioned") | Pairing the claim with the 10 mg pack is a miss. The photo's EXIF GPS is stripped at step 0 |
| U6 | `glucophage_500mg_cn.jpg` (Commons, CC BY-SA 4.0): 格华止 metformin hydrochloride 0.5 g, China, Chinese only | "I take Glucophage five hundred milligrams twice a day." | `match` (500 mg = 0.5 g) | The label never prints "Glucophage" in Latin script. `insufficient_information` (a converted, unstated amount) or `unresolved_name` is a miss |
| U7 | `sortis_40mg_cz.jpg` (Commons, CC BY-SA 4.0): Sortis 40 mg, atorvastatin, Czech Republic; box and blister | "I take Lipitor twenty milligrams at night." | `strength_mismatch` (atorvastatin: 20 mg said, 40 mg pack) | Two brand names, one ingredient. Sortis is outside the catalogue, so the printed INN must pair it |
| U8 | `betaloc_zok_cz.jpg` (Commons, CC BY 4.0): Betaloc ZOK 100, metoprolol succinate, prolonged release, Czech Republic; low resolution | "I take Beloc-Zok one hundred milligrams once a day." | `match` (metoprolol succinate 100 mg, modified release) | Another country's brand name. `unreadable_source` would be a miss, not a harmful one |
| U9 | `panadol_extra_e5c2d88a_carton.jpg` (DailyMed, no licence, private): Panadol Extra, US, acetaminophen + caffeine, no mg on the front | "I take Panadol five hundred milligrams." | `ingredient_mismatch` (paracetamol vs paracetamol + caffeine) | The SPEC's own example. A `match` here would be harmful |
| U10 | `panadol_extra_strength_500_b2fe7f47_carton.jpg` (DailyMed, no licence, private): Panadol Extra Strength 500, US, acetaminophen only | U9's note | `match` (paracetamol 500 mg) | A trap: "Extra" in the name must not bring in the catalogue's caffeine. `ingredient_mismatch` here is a miss |
