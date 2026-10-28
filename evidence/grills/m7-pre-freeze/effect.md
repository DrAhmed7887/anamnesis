# M7 pre-freeze check (Gemini 4, 28 Oct evening): what changes

Two Gemini 4 Argon passes on Vertex, on `main` at c744fc7 (batches 1–23.1 and the 28 Oct scripts):
- **The QM review** (`qm.md`) covered batches 21–23.1 and every module in `anamnesis/`: 267k tokens for $0.54616. **VERDICT: PASS**, with 2 major and 5 minor findings.
- **The grill** (`grill.md`; prompt in `grill-prompt.md`) covered the code, `SPEC.md`, `docs/DATA_HANDLING.md`, the contract test names and the scripts that make live calls or guard data: 97k tokens for $0.24847. It claimed 11 breaks, 2 of them critical and 5 high.
- **Every claimed break was run against the code before triage**, offline (`verify_grill.py`, output in `verify_grill.out`). **Neither critical one reproduces. Two high ones are real:** #6, fixed here, and #3, which fails open on a wording packs don't print and stays a known limit. This line first said "one high one is real" (corrected 28 Oct, as the judge-facing session pointed out).

## The QM review
| # | Severity | Decision | What changes |
|---|---|---|---|
| 1 | major | **Already planned.** | The judge-facing README draft (judge/claims-video, 3f7ce35) replaces `main`'s stale README when that branch merges on Tue. |
| 2 | major | **Already planned.** | Ahmed's recordings come next, then the R cases, the hero's 10 runs and R2's live pause. The agentic bonus line waits on R2 (claims row 6.4). |
| 3 | minor | **Already planned; Ahmed's call.** | Invariant 3 stays at risk until Tue's filtered public repo drops the M1 Muse export. The `CLAUDE.md` "synthetic data only" wording is Ahmed's decision, and it is on his list. |
| 4 | minor | **Routed** to the judge-facing session. | The README's Limitations name the known fail-open and untested classes that the QM lists. |
| 5 | minor | **Taken, in `SPEC.md` §2.** | The water lead-in skips only round brackets, as the code does (`_skip_fillers`, `_followed_by_water`). The SPEC said "brackets". The code's narrower rule fails closed: a square bracket keeps the volume counting. |
| 6 | minor | **Nothing to change.** | Neither the README draft nor `docs/CLAIMS.md` cites the batch 21 run's cost, so the superseded $0.36897 in commit 8800944's message reaches no reader. `live-after.md` has the corrected $0.36826. |
| 7 | minor | **Already planned.** | The LICENSE, the claims table on `main`, the hosted brief and the video are on the plan for Mon–Wed. The declined usability check is already in the README draft's Limitations. |

## The grill: each claimed break, run against the code
| # | Claimed | Verdict | What the code does |
|---|---|---|---|
| 1 | critical: «ملي» isn't read as a volume, so "250 mg / 5 ملي" keeps 250 mg per ml | **False.** | The strength drops to null. «ملي» counts (SPEC §2), pinned since batch 23 round 6. |
| 2 | critical: "Each 5 ml contains 250 mg per dose" keeps a wrong strength | **Not a wrong strength.** | It keeps 250 mg per dose, which is what that label prints, and the tablet variant drops. One odd case does keep a strength: "Each 5 ml contains 250 mg/ml" read per dose keeps 250 mg per dose. No pack prints that, but it shows that a per-1-ml print counts as the own unit of a per-dose reading. That goes on the next batch's list. |
| 3 | high: a volume in words ("Each five ml contains 250 mg") is missed | **Real, low.** | It keeps 250 mg per ml, so it fails open. Packs print volumes in digits, so this stays a known limit unless a real pack shows it. |
| 4 | high: "amoxicillin clavulanic acid" makes a false `match` with a plain amoxicillin pack | **False.** | It comes out `unresolved_name`: the name doesn't resolve, so it fails safe. The grill's other case, "metoprolol" 100 mg against a "Metoprolol succinate 95 mg" pack, gives `match` by design. The claim names no salt or release, so the two sides don't disagree. |
| 5 | high: a `-contributor` price key gets past the open-weight reader | **Fails closed.** | Construction accepts it, but the read raises on the price table before any request. No request was sent and nothing was charged. Only the error is unclear. |
| 6 | high: `reader_eval.py`'s photo check is wider than the data rule | **Real. Taken now.** | It allowed anything under `media/public/`, DailyMed included. `docs/DATA_HANDLING.md` lets only Commons and Cairo CC BY photos go to Fireworks or Baseten. No such photo was ever sent: every photo of the comparison, its pilots and its diagnostics is in `public/gemini-commons` or `real-public`. Its folders now match `intake_live.py`'s, and path tricks (`..`, symlinks) were already refused. |
| 7 | high: advice in a claim's `name_text` reaches the patient's photo request | **Not reachable live.** | The claim extractor refuses a reply whose `name_text` holds advice (`assert_no_advice`, `claims.py`:146; SPEC.md:30), so no live claim carries it. The grill's input needs a hand-built claim. |
| 8 | medium: two regions with the same id | **Not realistic.** | An id is the photo's first 12 hex digits plus the object number. Two different photos in one intake would need a 48-bit collision. |
| 9 | medium: one call can cost more than the session's cap | **By design.** | The guard checks an upper-bound estimate before each call and charges the actual cost after. The input estimate is characters ÷ 2 plus 5,000 per image, and the output estimate is the reply cap. A crop takes 465–1,001 input tokens. |
| 10 | medium: a combination's INN names resolve to a single-INN brand | **False.** | `resolve` returns nothing for "amoxicillin clavulanic acid" and its variants. It also returns nothing for an Arabic INN spelling (`أملوديبين`). An unresolved name fails safe. |
| 11 | low: odd number inputs (`1e-05`) | **Fails closed.** | It returns `None`, so the amount isn't stated. "١,٥" reads as 1.5, and "1.000" stays ambiguous, as SPEC §2 says. |

## For the next batch (all low, and all fail closed or unrealistic)
- **Tighten the per-dose own-unit form,** so that a per-1-ml print doesn't excuse a per-dose reading beside another volume (#2).
- **Read volumes written in words** (#3).
- **Two clearer refusals:**
  - refuse a `-contributor` price key when the reader is built (#5);
  - run `assert_no_advice` over the photo request's own text (#7).
- **A contract pin** for a square bracket after a water word (QM #5).

**Spend:** $0.79463 (estimated) on the Google credit, which now stands at $2.54 of $50.95.
