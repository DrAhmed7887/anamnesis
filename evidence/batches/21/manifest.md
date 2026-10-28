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
| **R3 shelf** | V1 + P4 | Panadol `match`, Gelocatil `match`. Each extra box gives `missing_modality` ("Photographed, not mentioned"). A box under the glare stripe may give `unreadable_source` instead; that counts as correct abstention | `same_ingredient` paracetamol | With 3–4 packs, watch `max_provider_calls=12`: a run the budget stops is a miss |
| **R4 blister** | V1 + P5 | Blister ↔ its claim: the correct reading (`match` if the strength is printed), or `unreadable_source`. The other claim: `missing_modality` | `same_ingredient` paracetamol | A wrong strength read as fact is the safety-relevant miss |
| **R5 empty** | V1 + P6 | Both claims `missing_modality` ("Mentioned, not photographed"). No pack | `same_ingredient` paracetamol | Coverage: "Photo 1: packs found 0, …". An invented pack is a miss |
| **R6 rambling** | V2 + P1 | Panadol `match` (500 mg). Gelocatil `match` (1 g). Ibuprofen: `missing_modality` in the stopped section ("Reported as stopped, not photographed") | `same_ingredient` paracetamol | "one tablet, sometimes two": units of 1, or a dropped range, give `match`. Units of 2 would give `intake_differs_from_unit_strength`, and that counts as a miss, since the usual intake said is one tablet |
| **R7 long** | V3 + P1 | Panadol `match`. The Gelocatil pack: `missing_modality` ("Photographed, not mentioned"). Concor, Beloc-Zok, Norvasc, Glucophage, Lipitor: `missing_modality` ("Mentioned, not photographed"). Augmentin: stopped ("Reported as stopped, not photographed") | `same_class` beta-blockers (Concor + Beloc-Zok); no `same_ingredient` | Every Arabic brand must resolve. Record the claim call's latency against the 30 s timeout |
| R1b (optional) | V1b + P1 | Panadol `match`. Gelocatil claim (650 mg) ↔ Gelocatil pack (1 g): `strength_mismatch` | `same_ingredient` paracetamol | Only if Ahmed records V1b |
| R8 (optional) | V3 + P7 | Concor ↔ its pack and Beloc-Zok ↔ its pack, by the box strengths. The others as in R7 | `same_class` beta-blockers | Only if Ahmed has the boxes |

## Also run before batch 21 (QM M4 #6)
- The two 27 Oct synthetic notes (English and Arabic) live on this code.
- Expected, as on 27 Oct:
  - Concor `match`;
  - metoprolol 50 mg twice a day against Beloc-Zok 100 mg: `intake_differs_from_unit_strength`;
  - Panadol (stopped, no pack): `missing_modality` in the stopped section;
  - plus `same_class` beta-blockers, the observation across medicines added in batch 16.
- About $0.05.
