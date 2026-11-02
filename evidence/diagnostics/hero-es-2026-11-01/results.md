# The Spanish hero, U13 (1 Nov, 15:53–15:59 CET): 3 of 10, 0 harmful

As set out in `plan.md` before any call (db31140, 15:53 CET): ten runs on `main`, on the default path, scored with `score.py`.

| Run | Emconcor (10 mg said, 5 mg box) | Metoprolol, Lopresor 100 mg box | Beta-blocker note | Counts | Heard |
|---|---|---|---|---|---|
| r01 | `intake_differs_from_unit_strength` | `match` | yes | ✓ | "Concor diez miligramos cada mañana y metoprolol cien miligramos dos veces al día." |
| r02 | `intake_differs_from_unit_strength` | `match` | yes | ✓ | "Emconcor diez miligramos … metoprolol metoprolol cien miligramos …" |
| r03 | no claim | `unresolved_name` | no | ✗ | "10 miligramos cada mañana y metoprololrol cien miligramos …" |
| r04 | `missing_modality`: its pack read partial | `match` | yes | ✗ | "Emconcor diez miligramos … metoprolol cien miligramos …" |
| r05 | `intake_differs_from_unit_strength` | `missing_modality`: its pack read partial | yes | ✗ | as r04 |
| r06 | `intake_differs_from_unit_strength` | `match` | yes | ✓ | "Concor diez miligramos …" |
| r07 | no claim | `match` | no | ✗ | "10 miligramos cada mañana y metoprolol cien miligramos …" |
| r08 | `intake_differs_from_unit_strength` | `missing_modality`: its pack read partial | yes | ✗ | as r04 |
| r09 | `unresolved_name` | `match` | no | ✗ | "Emconcorconcor diez miligramos …" |
| r10 | `missing_modality`: both packs read partial | `missing_modality` | yes | ✗ | "Concor diez miligramos …" |

- **Harmful: 0.** No false match, and no wrong strength shown as fact.
- **Two causes for the seven misses, both in the media:**
  - **The note's opening is lost (r03, r07, r09).**
    - None of the ten transcripts has the first word, "Tomo". The synthetic note starts speaking at its first sample, with no silence before it.
    - In r03 and r07 the brand went too, so there was no Emconcor claim and no beta-blocker note. r03 also heard "metoprololrol", which can't ground the ingredient.
    - r09 heard "Emconcorconcor", which doesn't resolve.
  - **The reader marked a registry image partial at both zoom levels (r04, r05, r08, r10).**
    - Its label text had the right name and strength every time, for example "Emconcor® Cor 5 mg … Fumarato de bi…" and "Lopresor® 100 mg … Metoprolol, tart…".
    - A pack read partial is never paired, so those pairs abstained.
    - The images are 1024×576 studio shots in three-quarter view, with small print on the side panels.
- **As expected:** "Emconcor" came back as "Concor" in r01, r06 and r10 (row 4.27), which changed no finding. No reader wrote a Spanish salt name as the ingredient.
- **n = 10, one synthetic voice and two registry images:** these numbers describe the runs, not a rate.
- **Spend:** $0.43487 of Meta for the ten runs, 90 calls. Meta now stands at about $82.07 of the $150 credit with the grills, and the line is $100.
- **The plan's line:** fewer than 5 of 10 count, so the choice of hero goes back to Ahmed before the film changes.
- **The files:** `evidence/live/2026-11-01/report_U13_r01.json` … `_r10.json`, and `runs.jsonl` lines 11–20.

## The second set, U13b (1 Nov, 16:05–16:09 CET): 4 of 10, 0 harmful

As set out in `plan-set2.md` before any call of this set (c71100c, 16:04 CET). The note gained 0.8 s of silence at its start, and each image was cropped to its box's front face. Nothing else changed.

| Run | Heard | Emconcor (10 mg said, 5 mg box) | Metoprolol, Lopresor box | Beta-blocker note | Counts |
|---|---|---|---|---|---|
| r01 | "Toman Concor diez miligramos …" | `intake_differs_from_unit_strength` | `match` | yes | ✓ |
| r02 | "Toman Cocor diez …" | `unresolved_name` | `match` | no | ✗ |
| r03 | "Toman كونكور diez …" | found by the system, not by the scorer (below) | `match` | yes | ✗ as scored |
| r04 | "Concor diez … dos dos veces al día" | `intake_differs_from_unit_strength` | `match` | yes | ✓ |
| r05 | "Toman diez miligramos …" | no claim | `match` | no | ✗ |
| r06 | "Concor diez …" | `intake_differs_from_unit_strength` | `match` | yes | ✓ |
| r07 | "Tomen Koncor diez …" | `unresolved_name` | `match` | no | ✗ |
| r08 | "Toman كوكور عشر miligramos …" | `unresolved_name` | `match` | no | ✗ |
| r09 | "Tomen Korcor diez …" | `unresolved_name` | `match` | no | ✗ |
| r10 | "Concor diez …" | `intake_differs_from_unit_strength` | `match` | yes | ✓ |

- **The crops fixed the reading:**
  - All 20 pack readings were readable; the first set had 5 partial.
  - Metoprolol matched the Lopresor box in 10 of 10.
- **The misses are now all the brand name:**
  - With the silence, the first word is heard ("Toman", "Tomen").
  - But "Emconcor" came back as "Concor" in 4 runs only. Otherwise it was "Cocor", "Koncor" or "Korcor", it was dropped (r05), or it was written in Arabic script (r03, r08). r08 also wrote "diez" as «عشر».
- **r03, as scored and as found:**
  - "كونكور" is a catalogued Arabic spelling of Concor. So the claim paired with the Emconcor box, and the run had all three findings.
  - The scorer finds the claim by a Latin-script name or by its ingredient, so it counted a miss.
  - The registered count stays 4 of 10. Counting r03 would make 5, but the scorer isn't changed after a run.
- **Harmful: 0.** No false match, and no wrong strength shown as fact.
- **Spend:** $0.28617 of Meta for the ten runs, 70 calls. Meta now stands at about $82.35 of the $150 credit with the grills, and the line is $100.
- **The plan's line:** fewer than 5 of 10, so U12 stays the film's hero, and both Spanish sets go into the README.
- **The files:** `evidence/live/2026-11-01/report_U13b_r01.json` … `_r10.json`, and `runs.jsonl` lines 21–30.

## The third set, U13c (1 Nov, 16:22–16:25 CET): 9 of 10, 0 harmful

As set out in `plan-set3.md` before any call of this set (59f19ec, 16:21 CET). The one change: the patient says "bisoprolol" instead of "Emconcor".

| Run | Bisoprolol (10 mg said, Emconcor Cor 5 mg box) | Metoprolol, Lopresor 100 mg box | Beta-blocker note | Counts |
|---|---|---|---|---|
| r01–r09 | `intake_differs_from_unit_strength` | `match` | yes | ✓ |
| r10 | `intake_differs_from_unit_strength` | `strength_mismatch` | yes | ✗ |

- **Heard:** "Toma bisoprolol diez miligramos cada mañana y metoprolol cien miligramos dos veces al día" in r01 and r05–r09, word for word apart from "Toma" for "Tomo". The other four repeated a few words: "miligramos miligramos" (r03, r04), and "dos miligramos dos veces" (r02, r10).
- **r10, the miss:**
  - The repeated "dos miligramos" was taken as the metoprolol intake, 2 mg, so the pair showed `strength_mismatch` against the 100 mg box.
  - It is a false disagreement that a clinician would catch by hearing the turn. It isn't harmful by the registered definition: no false match, and no wrong strength read from a pack.
  - r02 had the same repeat and kept 100 mg.
- **The reading:** all 20 pack readings were readable again.
- **Harmful: 0.**
- **Spend:** $0.26647 of Meta for the ten runs, 70 calls. Meta now stands at about $82.62 of the $150 credit with the grills, and the line is $100.
- **The plan's line:** 5 or more of 10, so U13c becomes the hero of the film and the README, with its count. The first two Spanish sets, 3 and 4 of 10, are reported beside it.
- **The files:** `evidence/live/2026-11-01/report_U13c_r01.json` … `_r10.json`, and `runs.jsonl` lines 31–40.

## The three sets together
- **What changed between them:** only the media.
  - Set 2 added a lead-in silence to the note and cropped the images to the box front.
  - Set 3 had the patient say the generic name instead of the brand.
  - The code was the same throughout.
- **What they show:**
  - In this synthetic Spanish voice, Voice Transcribe hears "bisoprolol" and "metoprolol" far more reliably than the brand "Emconcor".
  - The reader marks the uncropped studio shots partial more often than the cropped fronts.
  - n = 10 per set, one synthetic voice and two registry images, so these describe the runs, not rates.

## The fourth set, U13d (1 Nov, 20:45–20:48 CET): 2 of 10, 0 harmful

As set out in `plan-set4.md` before any call of this set (2c37ec0, 20:44 CET). The one change: the voice, "Rosa" from ElevenLabs' voice library (peninsular Spanish), so the film could play the note it was tested on. It is a different test from sets 1–3, reported beside them and never added to them.

| Run | Bisoprolol (10 mg said, Emconcor Cor 5 mg box) | Metoprolol, Lopresor 100 mg box | Beta-blocker note | Counts |
|---|---|---|---|---|
| r04, r08 | `intake_differs_from_unit_strength` | `match` | yes | ✓ |
| r01–r03, r05–r07, r09, r10 | no bisoprolol finding: the claim's name didn't resolve | `match` | no | ✗ |

- **Heard:** "bisoprolol" came back as its own word in only r04 and r08. Otherwise Voice Transcribe joined it to the verb ("Tomobisoprolol", r01, r09, r10), wrote it with a v ("visoprolol", r03), or both ("Tomovisoprolol", r02, r05–r07). In Spanish, b and v are pronounced alike.
- **What followed:** the claim's name didn't match the catalogue, so the pair ended `unresolved_name` or `missing_modality`, and there was no bisoprolol finding and no beta-blocker note.
- **Metoprolol:** `match` in all 10. All 20 pack readings were readable.
- **Harmful: 0.** No false match, and no wrong strength read from a pack.
- **Spend:** $0.29168 of Meta for the ten runs, 70 calls. Meta now stands at about $82.94 of the $150 credit with the grills, and the line is $100.
- **The plan's line:** fewer than 5 of 10, so the film keeps set 3's run and plays no patient voice. Set 3 stays the Spanish hero's result. There is no fifth set.
- **What it shows:** names are matched as written. A Spanish "b" heard as "v", or a name run into the word before it, leaves the claim unresolved, and the brief says so. Accepting such spellings would be a product change for after the hackathon; none was made here.
- **The files:** `evidence/live/2026-11-01/report_U13d_r01.json` … `_r10.json`, and `runs.jsonl` lines 41–50.

## The fifth set, U13e (2 Nov, 01:57–02:01 CET), batch 32's code: 0 of 10 as registered, 10 of 10 read from the product's findings, 0 harmful

As set out in `plan-set5.md` before any call of this set (468bcc2 and its date fix 4ed7bae, 01:56 CET). The one change from set 4: the code, `main` with batch 32 merged (af84dcc). The voice note is set 4's, unchanged.

| Run | Heard as | Bisoprolol (10 mg said, Emconcor Cor 5 mg box) | Metoprolol, Lopresor 100 mg box | Beta-blocker note |
|---|---|---|---|---|
| r01–r03, r05–r10 | "Tomovisoprolol" | `intake_differs_from_unit_strength` | `match` | yes |
| r04 | "Tomobisoprolol" | `intake_differs_from_unit_strength` | `match` | yes |

- **What the product did:** in all 10 runs it resolved the name as heard to bisoprolol, paired it with the Emconcor box and flagged 10 mg said against the 5 mg unit; metoprolol matched; the beta-blocker note came out. The claim kept its name as heard.
- **Harmful: 0.** All 20 pack readings were readable.
- **The registered count is 0 of 10, and that is a fault of the scorer, written down here as it happened.** `score.py`, run unchanged as the plan said, finds the bisoprolol claim only by "concor" in its name or by its `inn` as written, so it never found a claim named "Tomovisoprolol" and scored every run "no claim". The same plan also said the claim would be "found through the catalogue, as the product now resolves it", which the unchanged scorer doesn't do. The plan contradicts itself, and the error is the CEO's.
- **A second reading, written after the runs:** `score_catalogue_view.py` is `score.py` with one change: when it can't find the claim by name or `inn`, it looks the claim's name up in the catalogue. On set 5 it gives **10 of 10**. On the other sets it changes only set 2, from 4 to 5 of 10: in r03 the brand came back in Arabic script ("كونكور"), which the product resolved and flagged correctly, and which the registered scorer, looking for Latin "concor", missed. Sets 1, 3 and 4 are unchanged (3, 9 and 2 of 10).
- **The plan's line for the film depends on which count is meant.** By the registered scorer, fewer than 5, so no patient voice; by the reading the plan described, 10 of 10. That choice is Ahmed's, and it is recorded below when he makes it.
- **Ahmed's choice (2 Nov, after the results):** the film plays the set-5 note and shows set 5 with both counts together: 10 of 10 from the product's findings, and 0 of 10 by the registered scorer, which missed the renamed claim. The first hero was reported the same way (9 of 10 by the system's own categories, 0 of 10 as registered).
- **Spend:** $0.31445 of Meta for the ten runs, 70 calls. Meta now stands at about $84.69 of the $150 credit with the grills, and the line is $100.
- **The files:** `evidence/live/2026-11-02/report_U13e_r01.json` … `_r10.json`, and that day's `runs.jsonl` lines 1–10.
