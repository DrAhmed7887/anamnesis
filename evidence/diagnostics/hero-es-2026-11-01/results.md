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
