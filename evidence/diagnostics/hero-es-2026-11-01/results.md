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
