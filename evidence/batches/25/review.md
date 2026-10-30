# Batch 25 review: the brief's look, and a viewport tag for phones (SPEC §7)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 2 rounds, with its built-in `taste` skill loaded before any style

**What the batch changes:** the clinician brief's look, and only its look.
- **The style:** `_STYLE` in `anamnesis/brief_html.py` is redesigned:
  - findings as cards, with the amber accent on each disagreement card;
  - the two sides divided, each as a label-and-value grid;
  - evidence links as chips, and the review status as a neutral pill;
  - a calmer header;
  - voice turns as quiet time buttons;
  - a striped timeline that scrolls inside its own box;
  - crops side by side.
- **One tag:** the page head gains `<meta name="viewport" content="width=device-width, initial-scale=1">` (`anamnesis/brief.py`). Without it a phone laid the brief out 980 px wide and shrank it, so the narrow-screen rule never applied.
- **One unit-test assertion,** which pinned the old bar on the whole Disagreements section, now pins the accent's new place on each card (`tests/unit/test_brief_extra.py:252`).
- **Why:** Ahmed's go on 30 Oct. The brief is the product's main screen and appears in the film, and it read like a plain document. The batch lands before the freeze (Sat 31 Oct 23:59).

**Who did what:**
- **Claude Code (Opus 5.5), as CEO,** wrote the SPEC paragraph "The look (batch 25)", the brief and the contract (a42676b).
  - **The reference build** (`reference.md`) gave 2,428 passed. It caught 17 mutants and passed the 2 legitimate rules.
  - **Two problems it found in the CEO's own work,** fixed before the build: a unit test pinned the section bar the brief moved, and the page had no viewport tag.
  - **One problem Muse found:** the contract's hidden-text check rejected a legitimate `font-size:0.875rem`. The CEO found the same flaw for `background-color:transparent`. Both checks now match whole declarations (4a7ae6e), re-proven with three new mutants.
- **Muse wrote all the code** in two rounds:
  - **Round 1:** the style, the viewport tag and the one assertion ($0.83).
  - **Round 2:** five style fixes from the reviews ($0.45):
    1. the timeline keeps words and numbers whole and scrolls on screen;
    2. the phone layout applies to screens only;
    3. no heading is left alone at the foot of a printed page;
    4. crops sit side by side;
    5. there is room under the two sides.
- **The held-out guard:** the goal check flagged two paths. Neither exposed held-out data:
  - **Round 1, `evidence/batches/24/manifest.md`:** the matching text is test data quoted inside `tests/unit/test_goal_check.py`, which Muse read. No tool call named any path under `evidence/`.
  - **Round 2, `evidence/spend/muse_ledger.jsonl`:** Muse ran `git diff` on it to see why the tree showed it modified. It holds only cost lines.
- **An independent Opus supervisor** reviewed both rounds (`supervisor.md`):
  - **Round 1: APPROVE.** It re-rendered 14 briefs, all byte-identical outside the style and the tag. Its two findings, the timeline cells and narrow print, went into round 2.
  - **Round 2: APPROVE.** Its 87 renders, 49 of them distinct pages, differ nowhere outside the style and the tag. Its two notes are accepted as they are:
    - crops from real phone photos still take a row each, because a width cap would shrink the zoom view;
    - an opened timeline could clip about 10 px when printed on A5.

**The gate:** pass, 2,428 tests, ruff clean, contract untouched since 4a7ae6e (`gate.json`).

**Checks beyond the gate, by the CEO in the desktop app's browser and headless Chrome:**
- **Identity:** six briefs are identical to the code before the batch outside the style and the viewport tag. These are the contract's five plus an empty intake.
- **Contrast,** measured on every text run of five pages: nothing below WCAG AA. The lowest is the status pill, 6.2:1. Nothing is hidden or under 11 px.
- **A phone (375 × 812, mobile emulation):**
  - the page fits the screen and the two sides stack;
  - the timeline keeps its words whole and scrolls inside its 341 px box;
  - before the batch, a phone showed the whole page 980 px wide and shrunk.
- **Desktop (1280 px):**
  - the sides sit side by side;
  - the test fixture's narrow crops sit three to a row. Crops from real phone photos are wider than half the column, so they still take a row each (supervisor, round 2, #1);
  - the photo's boxes stay exactly on their packs;
  - the page is about 500 px shorter than round 1.
- **Print (Letter):**
  - 7 pages, against 6 before;
  - the sides stay side by side with their divider;
  - no card splits, and no heading ends a page alone.
- **Right to left:** on the Arabic page the name, the `dd` rows and the transcript run right to left, and the amounts stay left to right, as on main.

**Found, not fixed here (after the hackathon):**
- **The goal check's export-wide "Read text file" scan** matches quoted text in tool results. That made round 1's flag.
- **Round 1's goal stayed open:** Muse reported the one sandbox socket test as the only failure but didn't close its goal. Round 2 closed it.

**Cost:** Muse $1.28 ($0.83 + $0.45; `evidence/spend/muse_ledger.jsonl`). Meta so far: $50.37 of $150.

Verdict: PASS
