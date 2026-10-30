# Batch 25 reference build (CEO)

**What it proves:** the contract can be met, the full suite stays green with a new style and the viewport tag, and each rule catches its own break.

**The contract on the code before the batch** (main 63002d3; contract a42676b): 2 of the 11 contract tests fail, `test_the_style_is_new` and `test_the_page_is_laid_out_at_the_screens_width`. The other 9 pass by design: they pin what must not change.

**The reference,** in a scratch clone of the contract commit:
- **The code:**
  - a new `_STYLE` of 48 rules, following `briefs/25.md`;
  - the viewport tag in `anamnesis/brief.py`'s page head;
  - the one unit-test pin that names today's section bar, `#disagree{border-left:` (`tests/unit/test_brief_extra.py:252`), changed to the accent's new place, `#disagree article{border-inline-start:4px solid #d9480f}`.
- **Result:** 2,428 passed, ruff clean.
- **The hashes are stable:** the five pages hash the same under `PYTHONHASHSEED` 0, 1, 2, 12345 and random.

**On a phone** (375 × 812, mobile emulation, in the desktop app's browser, timeline opened):

| | Page laid out at | The two sides | The timeline table |
|---|---|---|---|
| **Before** (main) | 980 px, shrunk to fit | side by side, 456 px each | inside the 980 px page |
| **The reference** | 375 px | stacked, 306 px | 820 px wide, scrolling inside its own 343 px box; the page doesn't scroll sideways |

At 1280 px the reference keeps the two sides side by side (461.5 px each).

**Mutants,** each applied to the reference and run against `tests/contract/test_b25_style.py`. All 14 are caught:

| Mutant | Caught by |
|---|---|
| m1 a word outside the style (`HEARD_IN` "Heard at") | the five page hashes |
| m2 a class on the sides (`class="sides card"`) | the five page hashes |
| m3 a script line (`audio.volume=1`) | the five page hashes |
| m4 `@import url(x.css)` | `test_the_style_loads_nothing` |
| m5 `@font-face` with `src:local(x)` | `test_the_style_loads_nothing` |
| m6 `h3::before{content:"Warning: "}` | `test_the_style_adds_no_words` |
| m7 `fill:none` on the photo boxes | `test_a_photo_box_stays_clickable_across_its_whole_area` |
| m8 `#scope p{display:none}` | `test_the_style_hides_nothing` |
| m9 `#review-status{opacity:.4}` | `test_the_style_hides_nothing` |
| m10 `</style><script>…</script><style>` inside the style | every test (two `<style>` elements) |
| m11 the old style back | `test_the_style_is_new` |
| m12 no viewport tag | `test_the_page_is_laid_out_at_the_screens_width` |
| m13 a viewport that blocks zooming (`maximum-scale=1`) | the viewport test and the five hashes |
| m14 another tag in the head | the viewport test and the five hashes |

**Two problems it found in the CEO's own work, both fixed before the build:**
1. **The unit-test pin.** The brief asked Muse to move the amber accent from the Disagreements section onto each card, and to edit no test. But `tests/unit/test_brief_extra.py:252` pins the section bar. The brief now names that one assertion and asks Muse to repoint it.
2. **The missing viewport tag.** Without it a phone lays the page out 980 px wide, so no style could make the 640 px rule apply. The tag joined the batch as its only change outside the style, pinned by the contract (`a42676b`, amended before any build).

**What the contract can't see:** how the page looks. The review judges that: screenshots before and after, contrast measured in the browser, the phone and print layouts, and the supervisor.
