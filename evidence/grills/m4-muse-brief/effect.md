# Milestone M4 (batches 15.5–19: Muse builds, the clinician brief): quality manager triage

Ahmed asked for the Gemini 4 quality manager before the next batch, through Antigravity or the Google Cloud credit. The prompt (`evidence/grills/QM_PROMPT.md`) was updated first: it now describes the CEO / Muse / supervisor pipeline, includes the Muse ledger and goal checks, and adds area 8, "what is missing".

**How it ran:**
- **Round 1, evidence half** (`qm.md`): Gemini 4 Argon (Medium) via `agy`, free on the AI Pro quota.
  - Antigravity cut the 315 KB package off at about 191 KB. Gemini saw every grill table, doc, ledger and batch file up to the contract test list, but no code; it flagged the cut itself.
  - The run then used up the agy quota.
- **Round 1, code half** (`qm-code.md`): SPEC, the contract test names and the code (173 KB, end marker seen).
  - Run through `gemini-4-argon` on Vertex AI, billed to the Google Developer Program credit (the active gcloud project's billing account).
  - 50,772 input and 2,201 output tokens, **$0.12 est.**
- **Fixes to the tooling:** `qm.sh` now has `evidence` and `code` halves, an end-of-package marker (the model must say PACKAGE TRUNCATED if it can't see it), a size warning, and `QM_VIA=vertex` (`scripts/vertex_ask.py`).

## Evidence half (`qm.md`): VERDICT PASS
| QM # | Finding | Verdict | Where |
|---|---|---|---|
| 1 | Pin the JS turn playback and `dir="auto"` before the brief is hosted | **Accepted** (supervisor 19 r2 #1–#2) | Batch 19.1 contract |
| 2 | README says Spark Open on Baseten is "planned", but `decisions.md` records the open-weight comparison as cut | **Accepted, fixed now** | README: cut, reconsidered only if time remains (Ahmed decides) |
| 3 | Feminine Arabic release words (`ممتدة`, `بطيئة`, with clitics) aren't recognised, so a said release falls back to the brand's | **Accepted, minor.** It fails toward `insufficient_information`, never toward `match` | Batch 19.1 contract |
| 4 | `pre-b16/effect.md` still says B16a/B16b/B17; log the pre-B16 Muse grill spend | **Mapping accepted, fixed now** (`pre-b16/effect.md`, "Where the plan landed"). **Spend: rejected**, because no Muse grill ran before B16: the idea grills were Astra and Claude, and the code grill was Claude | done |
| 5 | Batch 19 leftovers: docstring, unused `FIELD_EVIDENCE`, a `continue` that should raise | **Accepted** (supervisor 19 r2 #3) | Batch 19.1 |
| 6 | The saved live reports predate crop-first reads (batch 18) | **Accepted.** One live rerun of the two synthetic intakes with today's code (about $0.05 Meta) | Before batch 21 |
| 7 | Data-handling note, the 4 staged real-media cases (hero ×10), claims checklist, usability check or a stated "none" | **Accepted**, already planned. The data-handling note comes **before** any real photo is taken | Batch 21 and packaging |

**Deadline risks:**
- real human speech and real photos are untested;
- the video, the hosted replay and the case table aren't started;
- the QM package was cut off (fixed in `qm.sh`).

## Code half (`qm-code.md`): VERDICT HOLD
| QM # | Finding | Verdict | Where |
|---|---|---|---|
| 1 | **blocker:** a combination claim with an `intake_amount` can never reach `match`, even when its strength equals the pack's | **Rejected, by design.** SPEC §3 rule 8 says so explicitly: one amount can't be checked against a combination. Probe: Augmentin 875/125 claimed with an 875 mg intake gives `insufficient_information`, which fails safe | none |
| 2 | Overlaps use a conflicted claim's identity set | **Accepted, major.** Probe: "Concor" with a metoprolol strength, plus Beloc-Zok, gives `same_ingredient metoprolol` and lists Concor as metoprolol. A conflicted claim is already flagged `insufficient_information`, so it should not feed an observation | Batch 19.1: SPEC §7 and contract |
| 3 | The Arabic decimal sign `٫` (U+066B) isn't a decimal mark | **Accepted, minor.** Probe: `٥` and `٢,٥` parse, `٢٫٥` is dropped, which fails safe | Batch 19.1 contract |
| 4 | An intake ratio of 2 with `units_per_intake` 0.5 on a non-splittable tablet gives `intake_differs_from_unit_strength`, not `strength_mismatch` | **Noted, by design** (SPEC §3 rule 8, C1 order). Both results go to clinician review with the intake question; no false agreement | none |
| 5 | The brief drops salts from strength and intake rows, so a salt-only `formulation_mismatch` shows the same text on both sides | **Accepted, major.** `brief_html.py` never renders `salt` (grep). Also found while checking: the `formulation_mismatch` note says "release forms differ" when only the salts differ | Batch 19.1: render salts, a salt-or-release note, contract |
| 6 | A zoomed region's figure shows the crop before enlargement, but SPEC says "exactly the pixels the reader saw" | **Accepted, minor:** a SPEC wording fix (the zoom read saw the same crop at 2×) | Batch 19.1 SPEC |
| 7 | `label_text` is shown verbatim and exempt from the advice check; Arabic advice words with attached clitics slip past the blocklist | (a) **By design:** label text is quoted source text, and real packs print directions. (b) **Accepted, minor.** Probe: `وتناول` and `فيجب` pass `assert_no_advice` | Batch 19.1 contract |
| 8 | `DRUG_CLASSES` has one class; state the scope on the brief | **Accepted:** a fourth scope line naming what the checks across medicines cover | Batch 19.1 contract |

**Deadline risks:**
- real speech can break turn segmentation and the exact grounding check;
- missing salts would show in the hero brief;
- several photos at once may hit `max_provider_calls=12`, which matters for batch 21's multi-pack photos.

**CEO verdict.** The HOLD's only blocker (#1) is behaviour the SPEC chose on purpose, and it fails safe. No release-gate class (harmful false agreement, wrong provenance, advice leakage, spend-cap failure, frozen demo path) is reproduced. Two accepted majors touch the demo path, though: #2 (overlaps from conflicted claims) and #5 (salts hidden in the brief). They land in a small batch 19.1 together with the minors. The code half then reruns for round 2.
