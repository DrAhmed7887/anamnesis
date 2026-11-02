# Batch 25, round 2: five fixes to the brief's style

You are the builder for round 2 of batch 25 of Anamnesis. Round 1's style is in the working tree, uncommitted. Build on it: change only what this brief lists, in `_STYLE` (`anamnesis/brief_html.py`). Everything round 1's brief said still holds, including the hard rules and "no other line in `anamnesis/` changes".

Round 1 was reviewed twice. The CEO rendered it at 1280 px, at 375 px on a phone, and in print. An independent supervisor checked the CSS, re-rendered 14 briefs and approved it. It looks right, and every text colour passes AA (the lowest is 6.2:1). Five things need fixing.

## 1. The timeline keeps its words and numbers whole (must)
**The failure:**
- At 375 px the table squeezes its nine columns, and its words break letter by letter: "tr / an / sc / ri / be", and "$ / 0. / 0 / 0 / 1 / 0 / 0" for `$0.00100`.
- On desktop, live model ids such as `muse-voice-transcribe-1.0`, 4–5 digit token counts and costs such as `$0.01234` would split too.
- `overflow-wrap:anywhere` on `body` is inherited into the cells, so an auto-layout table can shrink every column to one character. `overflow-x:auto` on `#timeline` therefore never comes into play.

**The fix:**
- **Numbers never split:** add `white-space:nowrap` to the existing right-align rule for the number cells (columns 1 and 6–9).
- **On screen, words stay whole too:** `@media screen{#timeline table{overflow-wrap:normal}}`. The table then keeps its natural width and scrolls inside `#timeline`; the page never scrolls sideways at 375 px.
- **In print,** text cells may still wrap, so nothing is cut off at the page edge.

## 2. The phone layout is for screens only
**The failure:** printed narrower than 640 CSS px (A5, or A4 at a large scale), the `max-width:640px` block still applies. The print block restores two columns but not the divider, so the pack column gets a top rule and top padding and no divider.

**The fix:** make that block `@media screen and (max-width:640px)`.

## 3. Print: no heading alone at the foot of a page
**The failure:** printed on Letter paper, "Across medicines" ends page 1 alone, and its card starts page 2. That happens because a card never splits.

**The fix:** keep each section's `h2` with what follows it (`break-after: avoid`).

## 4. Region crops side by side
**The failure:** each crop in `#photos` (`figure[id^="region:"]`) takes a whole row. Four narrow crops make the page about 1,300 px longer.

**The fix:** let the crop figures sit side by side and wrap, for instance `display:inline-block; vertical-align:top` with a gap. The photo figure (`figure[id^="photo:"]`) and its boxes stay full width and unchanged.

## 5. Room under the two sides
**The failure:** the line after the sides (the codes line, or the evidence line) touches the bottom of the columns.

**The fix:** give `.sides` a bottom margin.

## Rules
- **Only `_STYLE` changes in this round.** Keep round 1's viewport tag and unit-test assertion as they are.
- **Never create, modify or delete anything under `tests/contract/`, any `conftest.py`, `pyproject.toml` or `uv.lock`.** The contract was updated after round 1 (commit a4cc468): its hidden-text check now matches whole declarations, so `font-size:0.875rem` is fine.
- Don't edit `SPEC.md`, `scripts/`, `evidence/`, `docs/`, `NOTICE` or `finetune/`.
- Work only inside this repository. No network, no API keys, no git commits, no new dependencies.
- Run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.
- **One test needs a local network socket that your sandbox forbids.** If it is the only failure, say so and close your goal.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass from the repo root, and `git status --porcelain tests/contract` prints nothing.

Reply with a short report:
- what you changed for each numbered item;
- any new colour pair, with its contrast ratio;
- the final test count.
