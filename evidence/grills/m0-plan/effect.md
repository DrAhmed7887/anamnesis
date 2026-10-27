# Milestone 0: grill of the Day 1 plan

Grilled by Muse Code (`muse-spark-1.3`, `muse.md`) and GPT-6 Astra (`astra.md`), 27 Oct 2026. Verdicts by Claude Code (reviewer).

| # | Source | Finding | Verdict | Applied in |
|---|---|---|---|---|
| 1 | Astra + Muse | A forced `photo → region → spoken span` chain breaks: one turn can cite two boxes, and a box can have no speech | Accepted: independent `audio_evidence` and `visual_evidence` lists, plus `missing_modality` | `SPEC.md` §1, §3; batch 1 |
| 2 | Astra + Muse | A 60-drug international catalogue is a data project | Accepted: 10 synthetic adversarial cases | batch 2 |
| 3 | Muse | The case list: 2 clean, 2 strength mismatches, dose vs frequency, a combination, a brand alias, a ratio, unreadable, negation | Accepted as written | batch 2 |
| 4 | Muse | Store boxes normalized to 0–1000 | **Rejected.** SAM 3.1 returns inclusive source pixels plus `w,h`, so we store exactly that (lossless). The goal of an auditable box is kept through `image_sha256` and `object_id` | `SPEC.md` §1 |
| 5 | Muse | SAM oversegments blister packs: keep only the top regions | Accepted: top-3 | `SPEC.md` §4 |
| 6 | Muse | The refine loop can run forever | Accepted: `max_grounding_iters = 2`, then abstain | `SPEC.md` §4 |
| 7 | Muse | "50 mg twice daily" vs a 100 mg pack gets conflated | Accepted: `intake_amount` is kept separate from `strength`, plus the `intake_differs_from_unit_strength` type | `SPEC.md` §2, §3 |
| 8 | Muse | Negation: "I stopped Concor" while the box is on the table | Accepted: `status` plus `discontinued_but_present` | `SPEC.md` §2, §3 |
| 9 | Muse | Same brand, different strength by country | Accepted: a `country` field on `PackObservation` | `SPEC.md` §2 |
| 10 | Muse | Log model id, latency and tokens on every call | Accepted, with `cost_usd` added | `SPEC.md` §5; batch 3 |
| 11 | Muse | Use `tool_choice="required"` with care | Moot: Meta allows only `auto`, so we use one tool | `SPEC.md` §4 |
| 12 | Astra | Day 1 offline, $0, 3 reviewed commits | Accepted | plan |
| 13 | Astra + Antigravity | Drop the 7K narrative spec | Accepted: a 1-page contract table | `SPEC.md` |
| 14 | Astra | Inspect provider response shapes before freezing the schemas | Accepted: shapes taken from `docs/muse/sam-3-1.md` and `muse-voice-transcribe.md` | `SPEC.md` §1 |

Muse's effect so far: 9 of its 11 findings were accepted (#4 rejected, #11 moot). It added 4 things the Astra review missed: #5, #6, #8 and #9.
