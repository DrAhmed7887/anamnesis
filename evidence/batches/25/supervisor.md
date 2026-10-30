# Batch 25 supervisor (independent Opus subagent)

## Round 1

SUPERVISOR: APPROVE

**Checked, no finding**
- **Scope:** only three places differ from HEAD: `_STYLE` (brief_html.py:71–130), the head line (brief.py:121–123) and test_brief_extra.py:252. There is no test_b25_extra.py. The gate's fourth file is the spend ledger.
- **Identity:** I rendered 14 briefs on HEAD and on the build:
  - the contract's five;
  - an empty intake, as a draft and approved;
  - Arabic speech with a disagreement plus unreadable, unphotographed and stopped items, as a draft, with two requests open, and approved;
  - a withdrawn request, a voice and segmenter failure, an undecodable photo, and an exhausted budget.

  Outside `<style>` and the viewport tag, all 14 are byte-identical. HEAD matches the contract's hashes. The tag appears once, right after charset.
- **Hard rules:**
  - None of these appear: `url(`, `@import`, `@font-face`, `content`, a hiding declaration, red other than the prescribed amber, rgba, opacity, blur, gradients, animation, transitions, fixed/sticky, shadows, a colour-scheme block.
  - Beyond the word list: no `clip`, `text-indent`, zero sizes, `overflow:hidden`, negative offsets or transforms.
  - The photo, image and `.pre` rules are unchanged, and no new rule reaches `.photo`, `svg`, `rect` or `pointer-events`.
  - The sides are two columns, one column below 640 px, and two in print. At 375 px nothing makes the page wider.
  - Print: white background, no shadows, `article{break-inside:avoid}`. 57 rules, braces balanced.
- **Contrast (WCAG):**

  | Colour | Where | Ratio |
  |---|---|---|
  | #111 | on #fff, #f1f1f1, #f8f8f8, #f5f5f5 | 18.9, 16.7, 17.8, 17.3 |
  | #595959 | h4, scope lines, figcaption, reference line, turn buttons (own #fff) | 7.0 |
  | #595959 | status pill, colour from `#scope p`, on #f1f1f1 | 6.2 |
  | #0b5cad | links and chips | 6.7 (5.9 on any tint) |
  | #d9480f | accent | 4.3 |
  | #767676 | borders | 4.5 on #fff, at least 4.0 on the tints |

- **Right to left:** no rule sets `direction` or `unicode-bidi`. `article` and the side `div`s have no `dir`, so on Arabic cards the accent stays on the left edge. The pack divider stays between the columns, or on top when stacked. Arabic `h3`, `dd` and `span` align right inside their own boxes, as on main, and `bdi` is untouched.
- **Unit test:** one line changed, and it pins `#disagree article{border-inline-start:4px solid #d9480f}`. The 111 b19, b20, b25 and brief unit tests pass.

**Findings**
1. **Medium, not blocking: the brief only says the timeline "may" scroll.** brief_html.py:73, with 109–116.
   - **Cause:** `overflow-wrap:anywhere` on `body` is inherited into the timeline cells. Unlike `break-word`, `anywhere` lets a cell shrink to the width of one character. The auto-layout table therefore always fits its box, and `overflow-x:auto` never comes into play.
   - **Evidence:** estimated from the CSS with SF font metrics, not rendered. At 375 px the nine columns get 27–40 px each, so "$0.00100", "Cost", "Model" and "fixture:test" break mid-word.
   - **Also:** cost cells break on A4, and on desktop with live model ids (muse-voice-transcribe-1.0) and 4–5 digit token counts. "$0.01234" gets a 79 px column. Main never split a number.
   - **Fix:** add `white-space:nowrap` to the right-align rule (115–116), plus `@media screen{#timeline table{overflow-wrap:normal}}`. On screen the table then scrolls inside `#timeline`. Print still wraps text, so nothing is cut off and no number splits.
2. **Low.** brief_html.py:87–89, against 127–129.
   - **Cause:** when printed narrower than 640 CSS px (A5, or A4 at a large scale), the stacking block still applies. The print block restores two columns but not the divider.
   - **Effect:** the pack column gets a top rule and top padding, and there is no divider between the columns.
   - **Fix:** `@media screen and (max-width:640px)`.

**CEO's note:** finding 1 is the timeline failure the CEO's review saw rendered at 375 px ("tr / an / sc / ri / be"). Both findings go into round 2, with three small fixes from the CEO's own review.

## Round 2

SUPERVISOR: APPROVE

**Findings**
1. **Low**, `anamnesis/brief_html.py:119`. Crops keep the photo's full resolution: `anamnesis/agent/crop.py:11` cuts at source pixels, and `anamnesis/agent/media.py:35` never shrinks a photo. So a crop from a real phone photo is usually wider than half the 928 px column, and it still takes a whole row, as in round 1. Only the test-fixture crops sit side by side. Those are 142 px images, but each figure is about 276 px wide because the caption sets its width. They fit 3 per row on desktop, so the showcase goes from 4 rows to 2. On a phone they stay 1 per row. Fix: none this round. To shorten live briefs, you could cap the figure (`max-width:min(100%,24rem)`), but the crop would show less zoom. Your call.
2. **Info**, `brief_html.py:109,116`. In print, the numbers that can't wrap make the timeline need about 430 px with live 5-digit counts (estimated from the system font's widths). A4 (652 px) and Letter (674 px) fit. A5 portrait (about 417 px) could cut off about 10 px, because `overflow-x:auto` clips in print. This only happens when the timeline is open. Fix: accept it, or remove `#timeline`'s padding in print.

**Items**
1. Timeline cells: held. `nth-child(1)` also catches the total row (one cell spanning all columns), which does no harm.
2. 640 px block for screens only: held.
3. `section>h2{break-after:avoid}`: held.
4. Crops side by side: held (see finding 1).
5. `.sides` bottom margin: held.

**Checks**
- **Nothing else changed:** outside `_STYLE`, the parsed code of `brief_html.py` is identical to round 1 and to HEAD. The round 2 diff is lines 81, 85, 87, 116–117 and 119. `brief.py` and `test_brief_extra.py` were last written at 14:37, in round 1. Nothing else under `anamnesis/` or `tests/` changed after 14:45.
- **Page outside the style:** I recorded every `render_brief` call in the 13 brief test files, on copies of HEAD and of round 2. That was 87 renders and 49 distinct pages, with 0 differences outside `<style>` and the viewport tag. The five contract hashes match, and so does the empty-intake page. The b25 contract passes and ruff is clean. The gate passed with 2428 tests.
- **Hard rules 1–9:** nothing loads or hides, there is no `content`, and there is no motion, fixed, sticky or shadow. The photo-box and `img` rules are byte-identical (lines 123–127), and there are 59 rules. No colour or background was added. The lowest text pair is still #595959 on #f1f1f1, at 6.2:1.
- **What the fixes could break:**
  - Number splits: `white-space:nowrap` switches off `overflow-wrap:anywhere`, so no number cell splits, on screen or in print.
  - Crops: a crop's width stays within the column minus 1rem, and the image's percentage `max-width` lets it shrink, so no crop is wider than the screen.
  - Photo boxes: the photo figure is untouched, and `[id^="region:"]` can't match `photo:N`.
  - 375 px: the table needs about 660 px and scrolls inside `#timeline`'s 309 px box.

**CEO's decision on the two findings:** both are accepted as they are.
1. Capping crops would shrink the click-to-zoom view, which exists to show the pixels the reader saw (SPEC §7).
2. The timeline is collapsed unless someone opens it, and A4 and Letter fit.
