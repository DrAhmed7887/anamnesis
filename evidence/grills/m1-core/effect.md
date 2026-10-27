# Milestone 1: grill of the deterministic core (batches 1–2)

The same brief (`brief.md`) went to Muse Code (`muse.md`, `muse_session.json`) and to GPT-6 Astra (`astra.md`), 27 Oct 2026. Verdicts by Claude Code. "B3" is the hardening batch these findings created; "B4" is the provider adapters.

| # | Muse | Astra | Finding | Verdict | Applied in |
|---|---|---|---|---|---|
| 1 | M1 | A1 | Rule 7: "nothing to compare" is reported as `match`. A missed dose read becomes false reassurance | **Accepted (critical).** New `insufficient_information` type that requires review. Muse's suggestion (`strength_mismatch`) was rejected because it would mislabel the gap | B3 |
| 2 | M2 | A2 | No release form: Beloc-Zok (metoprolol **succinate ER**) 100 mg "matches" plain metoprolol 100 mg | **Accepted:** `release` (`immediate`, `modified`, `unknown`) on `Strength`, set in the catalogue, plus a `formulation_mismatch` type. Known vs modified with the other side unknown → `insufficient_information`. Salt and moiety modelling **deferred** (needs curated equivalence data) | B3 |
| 3 | M3 | A5 | Half-tablet logic ignores the dosage form: capsules and ER tablets can't be split | **Accepted:** r = 0.5 counts as `intake_differs…` only for immediate-release tablets, otherwise `strength_mismatch`. Intake checks only for `per` = tablet or capsule; `ml` or `dose` → `insufficient_information` | B3 |
| 4 | — | A4 | Equal strengths hide a contradictory intake | **Accepted:** the intake check also runs after a strength match | B3 |
| 5 | M4 | A8 | "Fixed templates only" isn't enforced: a `Finding` accepts any note | **Accepted:** templates move into `anamnesis/schema/`, and `Finding` must carry the canonical note and question id for its type. The blocklist gains split, halve, continue, keep taking, safe. The allowlist stays the real control | B3 |
| 6 | M5 | A7 | Greedy first-overlap pairing depends on photo order (Panadol vs Panadol Extra, Concor 5 vs 10) | **Accepted:** pairs are scored (exact INN set and equal strength > exact set > overlap) and the result must not depend on input order. `ambiguous_pairing` **deferred** | B3 |
| 7 | M6 | A3 | Explicit `inn` overrides the strength's ingredients; duplicate INNs collapse; no `paracetamol = acetaminophen` | **Accepted:** the comparison set comes from strength ingredients when present, `inn` is normalised with a synonym table, duplicate INNs are rejected, and different ingredient keys → `ingredient_mismatch` | B3 |
| 8 | M7 | A6 | Resolution: "Beloc Zok" vs "Beloc-Zok"; a sentence naming 2 drugs silently returns 1 | **Accepted:** hyphens and spaces are treated alike; text matching 2+ different products → `None` (unresolved). Unknown qualifiers such as "Panadol Night" and country collisions **deferred**: none exist in the 8-entry catalogue | B3 |
| 9 | M8 | A5 | Liquids and concentrations can't be represented | **Deferred:** no liquids in the demo set. Covered safely by #3 (`ml` → `insufficient_information`) | — |
| 10 | M10 | A9 | Evidence IDs aren't checked against real turns or regions | **Partly accepted:** each finding's IDs must match its evidence sides (B3). The full intake envelope with referential checks goes to batch 5 (agent loop) | B3 / B5 |
| 11 | M10 | A10 | No typed call record or provenance for providers | **Accepted:** `ProviderTrace` with `call_id`; each label reading carries its `region_id` | B4 |
| 12 | — | A11 | `as_needed=False` invents a negative fact | **Accepted:** `as_needed: bool | None = None` | B3 |
| 13 | M10 | — | Empty `transcript` or `speaker` is accepted | **Accepted:** both must be non-empty when present | B3 |
| 14 | M11, M12 | A12 | Circular guardrail tests, a substring check for recursion, extra fields tested on 3 of 8 models, no order test | **Accepted:** new contract checks that miss-case phrases raise, walks the JSON-schema `$ref` graph, tests extra fields on all models, tests order permutations, and checks every question id is mapped | B3 |

**Effect:** 24 findings from the two reviewers merged into 14. Accepted 11, partly accepted 1, deferred 2 (with reasons). The two reviewers agreed on 10 of the 14. **Muse alone** found the specific Beloc-Zok succinate-ER trap (#2), capsule splitting (#3), and the hyphen and multi-drug sentence cases (#8). **Astra alone** found that equal strengths hide intake (#4) and the `as_needed` negative fact (#12).

**Process finding:** Muse Code ran on `muse-spark-1.3-contributor` by default (about $0.20; synthetic code only), which lets Meta train on what it was sent. `scripts/grill.sh` now pins `--model muse-spark-1.3` (Standard) and caps the run at 12 steps.
