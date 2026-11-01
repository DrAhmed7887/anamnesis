# Batch 31: the follow-up live on U11, matched in 2 of 4 runs

As set out in `live-plan.md` before any call (79c95a6, 14:46 CET), with three more runs added by its amendment before they ran (a7d3a2f and 91c0cfc, 14:48). The code is `main` with batch 31 merged (8ee370a); the commits after it change only docs. The runner is `scripts/follow_up_live.py`. The staged patient is the script: it answers the first request with pk025_b and sends nothing after that.

| Run | Asked | The reply's reading (read, then 2× zoom) | c1 after | Review | Follow-up cost |
|---|---|---|---|---|---|
| U11 (registered) | r1, then r2 in round 2 | partial, partial | `missing_modality` | waits on the patient (r2 open) | $0.02421 |
| U11_r02 | r1, then r2 in round 2 | partial, partial | `missing_modality` | waits on the patient (r2 open) | $0.02425 |
| U11_r03 | r1 | partial, readable | `match` with o1 | draft | $0.02246 |
| U11_r04 | r1 | partial, readable | `match` with o1 | draft | $0.02157 |

- **The intake on pk025_a, in every run:** partial at both zoom levels, so `unreadable_source` for the pack (o0) and `missing_modality` for the ibuprofen claim (c1). `requestable` listed o0, then c1.
- **The follow-up, in every run:**
  - Its only target was c1, the medicine the patient mentioned. The unreadable first pack (o0) stayed with the clinician.
  - The patient got the template with the claim's name: "Please send one photo of the pack of the medicine you mentioned as “ibuprofen”." In r03 the claim's name came back as "Ibuprofen".
  - SAM found the new pack with "package". No model call touched the first photo during the follow-up.
  - No review came out approved, and each follow-up cost 2.2–2.4 cents and took 14.5–18.6 s.
- **The two open runs:** the reader gave ibuprofen 400 mg per tablet from the reply, but marked it partial at both zoom levels, so the pack wasn't paired. Round 2 asked again, the patient sent nothing, and the request stays open. That is the plan's second known-variation branch (`live-plan.md`:34).
- **Against the registered misses:**
  - U11, the registered run, misses two: c1 isn't `match`, and a request other than r1 was opened. r02 misses the same two.
  - r03 and r04 miss none.
  - None of the four gave an approved review, a call on pk025_a during the follow-up, or a follow-up over $0.25.
- **The briefs:** the after-brief says "Anamnesis sent the follow-up itself, for medicines mentioned but not photographed: photos asked for 2, received 1." in the two open runs, and "… photos asked for 1, received 1." in r03 and r04. Those two also have an approved brief, made offline.
- **A first attempt, refused before any call:** at 14:46 CET the ledger cap refused the first call, because `--cap` was left at its $5.00 default with the ledger at $16.29. Nothing was sent and $0 was spent. Its two lines stay at the top of `runs.jsonl` (lines 1–2), and the registered run overwrote its reports.
- **n = 4, with one synthetic voice and two public photos:** these numbers describe the runs, not a rate.
- **Spend:** $0.20199 of Meta for the four runs (44 calls). Meta now stands at about $81.63 of the $150 credit with the grills, and the line is $100.
- **The files:** `evidence/live/2026-11-01/report_<run>-fu-before.json`, `report_<run>-fu-after.json`, `followup_<run>.json`, and `runs.jsonl` lines 3–10.
