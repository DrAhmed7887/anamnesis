# Pre-B16 grill and the zoom problem (27 Oct 2026): triage

Ahmed asked for one last grill of the idea and the code before B16, run by a team of agents, plus a fix for "the zoom problem", all on the worktree branch `batch/15.5-zoom` so `main` stays untouched.

## The zoom problem: what the live check found (`evidence/live/2026-10-27/zoom_before/`)
Four staged 12 MP phone photos (`scripts/make_hard_media.sh`: a drawer of three packs, a blister foil with low-contrast print and a small far-away pack, each saved upright and as a real phone saves a portrait shot, landscape pixels plus EXIF Orientation 6). Expected readings were written to a manifest before any model saw them. Spend $0.09.

| # | Finding | Verdict | Where |
|---|---|---|---|
| Z1 | **Wrong provenance on portrait photos (release-gate class).** SAM applies EXIF orientation (it returned a 3024×4032 frame); Spark reads the stored sideways pixels. On `drawer_portrait.jpg` the region on Concor was read as "Beloc-Zok 100 mg", the region on Norvasc as "Concor 5 mg", and Norvasc was never read | **Accepted, blocker** | Batch 15.5: `prepare_image` turns every photo upright and strips metadata before any model sees it |
| Z2 | The crop-zoom refuses every 90° photo (`error: crop failed`) and, on a 180° photo, crops the wrong pixels while keeping the region id (reproduced offline) | **Accepted** | Batch 15.5 (same fix) + a guard: a region is read only from the photo it was found on |
| Z3 | Phone photos carry GPS and camera tags; they went to Meta unchanged | **Accepted** (privacy, ahead of the B17 data-handling note) | Batch 15.5: all EXIF and XMP dropped |
| Z4 | The zoom never fired: Spark read every upright label at the full 12 MP frame, foil print and the small pack included (about 4,300 input tokens per read) | **Noted, honest result** | The zoom stays the fallback for genuinely unreadable reads. Per Astra #4, show it in the demo only if a real B17 photo triggers it and the crop reading is correct |
| Z5 | `foil_portrait.jpg`: SAM found no region for either concept, so nothing was read and nothing was reported | **Accepted for B16** | The coverage block must say "no pack found on photo N", never stay silent |
| Z6 | "medicine box" returned 0 regions on all 4 photos (and on the synthetic photo before); "label" found them | Noted | B17: reorder or replace the concepts only with real-photo evidence |

## After the fix (`evidence/live/2026-10-27/zoom_after/`, same 4 photos, $0.12)
| # | Finding | Verdict | Where |
|---|---|---|---|
| Z7 | Portrait photo: **3/3 labels on the right pack** (before: 1/3). All 8 packs SAM found are read correctly | **Fixed** (Z1, Z2) | 15.5 |
| Z8 | A forced crop read of every region, outside the loop: **8/8 correct at 465–1,001 input tokens**, against about 4,300 for the full-photo read | **Recommendation:** read the crop first. The reader then sees only the region's pixels (provenance by construction, closing C4 and J5) at about a quarter of the input tokens. It changes SPEC §4 step 4 and supersedes two B14 contract tests, so it needs its own contract commit | B16a |
| Z9 | The loop still logged no `zoom_read` step: every first read was `readable` | Noted (Z4) | Demo: the on-screen zoom is the brief's click-to-region view plus the crop the reader saw, not a model re-read |

## Idea grill, GPT-6 Astra (`astra.md`)
| # | Finding | Verdict | Where |
|---|---|---|---|
| A1 | Retire the stale playbook claims: "first", fatal-error prevention, six-minute savings, FHIR, autonomous rotation, fabricated benchmarks, compliance | **Accepted** | Demo prep: one claims checklist against SPEC. Rotation is now deterministic preparation, never "autonomous" |
| A2 | 50 mg intake vs a 100 mg tablet is not necessarily a disagreement; don't open the video with it | **Accepted** | B17 staging: annotate one case with an explicitly stated tablet strength that conflicts with the pack |
| A3 | Pairing needs identity overlap, so a claim and a photo of different medicines give two `missing_modality` findings, not `ingredient_mismatch` | **Accepted as disclosure** (by design: nothing says they're the same item) | B16 brief wording: "mentioned, not photographed" and "photographed, not mentioned" |
| A4 | Judge-readable evidence: a compact case table (expected vs observed, false agreement, abstention, link correctness, latency, cost) | **Accepted** | `zoom_live.py` summaries are the start; B17 adds the staged real cases |
| A5 | A credible public artifact: sample brief, results, architecture, replay instructions, labelled cached replay | **Accepted** | Packaging step |
| A-stop | Stop: new video infrastructure, class-map expansion, another broad grill cycle | **Accepted** | This is the last broad grill; from here, targeted reproduction only |

## Idea grill, Claude Opus judge stand-in (`judge.md`)
| # | Finding | Verdict | Where |
|---|---|---|---|
| J1 | The video gets 2 of about 20 hours, the fewest of any step; give it 6 by cutting B17 to 4 cases and the usability check to 1 h at most | **Accepted as a recommendation. Ahmed decides** | Revised plan below |
| J2 | Hero case: Ahmed's own (fictional) Egyptian Arabic note and two real over-the-counter boxes with the same ingredient (Panadol + Gelocatil): "two brand names, one medicine" | **Accepted** | B16 builds the same-ingredient check (already in scope) plus one synthetic catalogue entry (Gelocatil, ES, paracetamol); B17 stages the case |
| J3 | Judges have nothing to click: host the B16 brief as a static replay that needs no key | **Accepted** | B16 writes a self-contained static HTML brief; packaging hosts it |
| J4 | Repeat runs: annotate first, run the hero live 10× (about $0.30), report "same findings in N/10" | **Accepted** | B17 |
| J5 | The first read sends the whole photo with the box as text coordinates; check each reading belongs to its box, and read crops first if one describes a neighbour | **Already reproduced live (Z1)** and fixed for rotated photos in 15.5 | The 15.5 after-run reads a crop of every region beside the full-frame read, on all 4 staged photos, to decide crop-first with evidence |
| J6 | Stop: unbacked playbook claims (FHIR, guardrail chat, open-weight table, "fatal bradycardia", "saves 6 minutes", an invented "93.3% recall", a fake domain, a wrong repo URL), the automated video pipeline, and self-testing presented as a usability check | **Accepted** (same as A1 and A-stop) | Claims checklist. One outside pharmacist by 31 Oct, or report no usability check. **Ahmed decides** |
| J7 | Overclaim: SPEC line 3 called text-to-speech audio "Egyptian Arabic with code-switching" | **Fixed now** in SPEC (synthetic macOS voices, no human speech yet) | Batch 15.5 branch |
| J8 | An account matter for Ahmed, left out of the public copy | **Open. Needs Ahmed** (not verified here) | Before submission |

## Code grill, Claude Opus code reviewer (`code.md`; probes re-run by the orchestrator)
| # | Finding | Class | Verdict | Where |
|---|---|---|---|---|
| C1 | `units_per_intake` ignored: half of a non-splittable Lipitor 20 mg → `match`, no review | (a) harmful false agreement | **Accepted, blocker** | B16a |
| C2 | Crop cut from stored pixels on rotated photos | (b) | **Fixed** in 15.5 (found independently by the code grill, the judge's J5 and the live check) | 15.5 |
| C3 | Model strings (`name_text`, `inn`, `country`) reach the report unchecked; cited turns only checked to exist | (b)+(c) advice leakage | **Accepted, blocker** before the brief shows these strings | B16a: `name_text` must occur in a cited turn (normalised); `country` ISO-2 only; `assert_no_advice` over every model string before the report |
| C4 | A label that names two products resolves to no brand, so release is unknown and a claim can `match` | (a) | **Accepted** | B16a: a label naming 2+ products is an extraction conflict (`insufficient_information`); crop-first reads decided by the 15.5 after-run |
| C5 | Bare-string numbers: "2,5 mg" drops the pack, "1-2" drops every claim, an equivalence line is rejected | (e) | **Accepted** (EU packs print decimal commas) | B16a: accept the decimal comma; an unparseable optional field becomes null instead of failing the reply |
| C6 | Extraction `max_tokens` 4000 includes reasoning; live notes already at 66–69%; a longer note loses every claim | (e) | **Accepted**, must land before B17 records a longer real note | B16a: raise `max_tokens` and the estimate; don't retry a length stop |
| C7 | Caps checked against a fixed $0.03 estimate; one call can overshoot a session cap | (d) minor | **Accepted** with the token correction in `code.md` | B16a, with C6's estimate |
| C8 | A guessed claim-side `release: modified` gives `match` | (a) plausible | **Accepted** | B16a: prompt says "unknown unless stated"; trust a claim-side release only with a release word or brand in `name_text` |

## Proposed plan to submission (Ahmed decides)
About 20 focused hours plus reserve to Wed 4 Nov 20:00 CET.
1. **Merge batch 15.5** into `main` (5 min, on Ahmed's word).
2. **B16a, hardening (about 2 h):** crop-first reads (Z8); C1, C3, C4, C5, C6+C7, C8; plus QM M3 r2 #2, #3, #5, which were already assigned to B16.
3. **B16b, the clinician brief (about 5 h):** one self-contained static HTML file, so it can be hosted (J3). Disagreements first; source values side by side; the photo with the SAM box, click-to-zoom on the region and the crop the reader saw; the turn-level audio link; a coverage block (skipped photos, photos with no pack found, unread regions: Z5); the scope lines; same ingredient across products (J2, plus one synthetic Gelocatil entry) and same-class overlap; the narrowed `match` wording; A3 wording.
4. **B17, real media, cut to 4 cases (about 3 h, J1):** the hero (Ahmed's own fictional Arabic note, Panadol + Gelocatil), Concor + Beloc-Zok, a rambling note, glare or several packs. Annotate first; run the hero 10 times (J4).
5. **Usability (1 h at most):** one outside pharmacist by 31 Oct, or report none (J6).
6. **Video (about 6 h, J1):** screen recording, voiceover, captions; the judge's 20-second hook.
7. **Package (about 1.5 h):** README, claims checklist (A1, J6), hosted replay, case table (A4).
Total about 18.5 h, leaving some reserve. Open for Ahmed: the merge, this plan (video at 6 h), the usability check, and J8.
