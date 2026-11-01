# Batch 31: the follow-up live, pre-registered (U11)

Written and committed before the first call. The runner is `scripts/follow_up_live.py`.

- **The case:** U11 (`evidence/batches/21/manifest.md`:76). It is one Egyptian ibuprofen 400 mg box from the Cairo University set (CC BY 4.0), photographed twice: `bjy2svvmn8_pk025_a.jpg` with the voice note, then `bjy2svvmn8_pk025_b.jpg`. The voice note is synthetic: "I take ibuprofen four hundred milligrams when I have pain."
- **The staged patient:** the script itself, because there is no patient app. It answers the first request with pk025_b and sends nothing for any later one.
- **The code:** `main` at batch 31's merge. The follow-up asks only for medicines the patient mentioned but didn't photograph (SPEC §8; supervisor 31 #2).

## Expected
The first half comes from U11's live run on 28 Oct (`evidence/batches/21/u11-u12.md`:5–18, row 2.5).
1. **The intake on pk025_a:**
   - the reader says partial, and partial again after the 2× zoom;
   - so `unreadable_source` for the pack (o0), and `missing_modality` for the ibuprofen claim (c1);
   - `requestable` lists o0, then c1.
2. **Round 1:**
   - The follow-up's only target is c1. o0 is the clinician's.
   - It opens r1 for c1, and the patient gets: "Please send one photo of the pack of the medicine you mentioned as “ibuprofen”." (the claim's `name_text`; on 28 Oct, ibuprofen).
   - The reply is pk025_b. SAM finds the pack (on 28 Oct, with "package"), and the reader reads ibuprofen 400 mg per tablet.
   - The claim ↔ the new pack gives `match`.
3. **Round 2:** nothing is left for the follow-up to ask, so the run stops.
4. **What o0 does:** it stays `unreadable_source` and is not superseded. Its photo shows the same box, but nothing tells the code that. The clinician sees it and decides.
5. **The log:** `[round 1, r1, c1, answered]`. The review is `draft`, and the header says "Anamnesis sent the follow-up itself, for medicines mentioned but not photographed: photos asked for 1, received 1." The approved brief is rendered offline.

## What counts as a miss
- a finding for c1 other than `match`;
- any request other than r1;
- an approved review coming out of `follow_up`;
- any model call on pk025_a during the follow-up;
- more than $0.25 spent on the follow-up.

## Known variation
Label reading varies from run to run (row 4.29: the label-side miss in r09).
- If pk025_a reads well enough for c1 to pair, there is nothing for the follow-up to ask, and it asks nobody.
- If pk025_b reads as partial, c1 stays unpaired. Round 2 asks for it again, the patient sends nothing, and the request stays open.

Either way, the run is reported as it came out.

**Cost:** about 5 cents (28 Oct: $0.03337 for the intake and $0.01382 for the re-photo).

## Amendment, 1 Nov 14:52 CET: after the first run, before any other
- **The first run (14:47 CET)** came out on the second known-variation branch. pk025_b read partial twice, so c1 stayed unpaired. Round 2 asked again (r2), the patient sent nothing, and the review waits on the patient. That run stays the registered result, and `live.md` reports it first.
- **Why more runs:** one run says little about a reading that varies. On 28 Oct the same crop of pk025_b read ibuprofen 400 mg.
- **The repeat:** three more runs with the same command and code, named `U11_r02`, `U11_r03` and `U11_r04`, with `--cap 16.70`. Each is scored against the same misses as above.
- **How it is reported:** every run, first run first. The summary is "k of 4 runs matched", never the best run alone. The film may show any of the four only with that count beside it.
- **Cost:** about 17 cents.
