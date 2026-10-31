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

## Live result (31 Oct, 00:07–00:09 CET), one call per case and model
| Case | Pattern | Spark 1.3 | Tuned Glimmer (Modal) |
|---|---|---|---|
| A | a negated amount ("ten, not five") | 10 mg ✓ | 10 mg ✓ |
| B | a past amount | 5 mg ✓ | 5 mg ✓ |
| C | another medicine's amount, same turn | 500 mg on Panadol, none on Concor ✓ | the same ✓ |
| D | a tablet count | 2 tablets, no mg ✓ | the same ✓ |
| E | one part of a combination | no amount: fails safe | 875 mg only: fails safe |
| F | another medicine's amount, another turn | ✓ | ✓ |
| G | a stopped medicine | discontinued ✓ | discontinued ✓ |
| H | a negated amount, Egyptian Arabic | 10 mg ✓ | 10 mg ✓ |

- **Wrong findings shown as fact: 0 of 16.** On C and F, the second claim (Panadol, not photographed) adds the expected `missing_modality`. On E, neither model wrote the combination's two parts as a strength, so the intake fails safe (`insufficient_information`).
- **What it means:**
  - **The checks don't test relations.** In five of eight patterns, a wrong tie between an amount and a medicine would pass them and show a wrong finding as fact.
  - **On these eight transcripts, neither extractor made such an error.** That is one run each, on invented text, so it shows the models' behaviour on these traps, not a guarantee.
- **No code change before the freeze.** A negation rule would be a new, multilingual heuristic that drops amounts. SPEC §2's known limits say what the check doesn't test, and the README should say it plainly, with this audit.
- **Spend:** Spark 1.3 $0.08 for 8 calls. Modal: per-call estimates of $0.04, plus the container's time, reconciled from Modal's billing.

## Muse's double-check, and two traps it added (31 Oct, 00:10)
A read-only Muse session checked the audit (`evidence/grills/relation-audit-muse/`). Its verdict: "Audit direction is right but its 'no code change' conclusion is under-evidenced".
- **It confirmed the method from the code:** the value-only check is `claims.py:353-358` with `stated.py:760-773`, and the fail-safe rules behind E, F and G are in `reconcile.py`.
- **It named five more traps.** The two that matter most were added as I and J:

| Case | Pattern | Right reply | Wrong reply, offline | Spark 1.3, live | Tuned Glimmer, live |
|---|---|---|---|---|---|
| I | micrograms said, milligrams written | `strength_mismatch` | **`match`: a false match** | 5 mcg ✓ | 5 mcg ✓ |
| J | a daily total read as one intake ("ten milligrams a day, five in the morning and five at night") | `match` | `intake_differs_from_unit_strength` | no amount: fails safe | **10 mg intake, 5 units: `intake_differs_from_unit_strength`, wrong as fact** |

## What the audit shows
- **The checks test values, not relations.** Seven of the ten traps would pass if a model got them wrong; three of those (A, H, I) would be false matches.
- **Live, 20 calls: no false match, and one wrong finding shown as fact.**
  - The tuned Glimmer read J's daily total as one intake, giving a false *disagreement* that a clinician would query.
  - Spark 1.3 got every trap right or failed safe.
  - That's one run each, on invented text.
- **Decision: no code change before the freeze.**
  - No false agreement was observed, which is the release-gate category.
  - The cheapest guard would be a new multilingual heuristic for negation, units and per-day phrases, with its own failure modes.
  - **After the hackathon:** the ten traps become contract tests first (Muse's suggestion), and any heuristic is gated behind them.
- **The README states the limit,** in the wording Muse proposed: each amount value is checked as said in a cited turn; which medicine, tense, negation or unit it belonged to is not checked. It also gives this audit's numbers.
