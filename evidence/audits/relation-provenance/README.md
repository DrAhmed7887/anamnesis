# Relation-level provenance audit (31 Oct)

**Why:** GPT-6 Astra's win grill (`evidence/grills/win-grill-astra/`) said the provenance checks "prove words occurred, not that the finding follows". Ahmed said yes to an hour's audit before the freeze.

**What:** eight invented transcripts, each with one pack reading.
- **Each case has two replies:** the claim a careful listener would write ("right"), and one claim with a relation error ("wrong").
- **Both go through the product's real path:** its own checks (`parse_claims_json`), then the full intake with the real reconciler, on the brief tests' fake providers.
- **The run:** `audit.py`, offline, no model call.

## Offline result: what the checks do with a wrong reply
| Case | Pattern | Right reply | Wrong reply | The wrong reply, shown as fact? |
|---|---|---|---|---|
| A | a negated amount ("ten, not five") | `intake_differs_from_unit_strength` | `match` | **yes: a false match** |
| B | a past amount ("used to take ten") | `match` | `intake_differs_from_unit_strength` | yes |
| C | another medicine's amount, same turn | `insufficient_information` | `strength_mismatch` | yes |
| D | a tablet count read as milligrams | `intake_differs_from_unit_strength` | `strength_mismatch` | yes |
| E | one part of a combination | `match` | `insufficient_information` | no: fails safe |
| F | another medicine's amount, another turn | `insufficient_information` | `insufficient_information` | no: the amount is dropped |
| G | a stopped medicine read as active | `discontinued_but_present` | `insufficient_information` | no: fails safe |
| H | a negated amount, Egyptian Arabic | `intake_differs_from_unit_strength` | `match` | **yes: a false match** |

- **So:** the checks test that an amount is said in the cited turn, not what it's said about (SPEC §2, "Known limits").
- **Five of the eight errors would pass** and show a wrong finding as fact, if a model made them. Two of those (A, H) would be false matches.
- **Combinations, other turns and stopped medicines** fail safe.

## The live probe, written before any call
`probe_live.py` sends the same eight transcripts once to Spark 1.3 and once to the tuned Glimmer, through the product's own extractors. Each model's claims then go through the same intake, and its findings are compared with the careful listener's. The question is whether the real models make these errors. The transcripts are invented text, never a person's speech. Spend: about $0.10 of Meta, and about $0.60 of Modal with its cold start.
