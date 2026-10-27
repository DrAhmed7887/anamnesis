# Batch 19, round 2: fix the review findings in the clinician brief

You are the builder for batch 19 of Anamnesis, round 2. Your round-1 change is in the working tree, uncommitted: `anamnesis/brief.py`, `anamnesis/core/overlap.py`, `anamnesis/core/reconcile.py`, `anamnesis/core/catalogue.py`, `anamnesis/core/catalogue.yaml`, `anamnesis/providers/meta.py`, `anamnesis/schema/templates.py` and `tests/unit/test_brief_extra.py`. An independent supervisor reviewed it, and the CEO rendered real pages from it in a browser. Fix the items below and keep everything else as it is.

The contract `tests/contract/test_b19_brief.py` has new cases at the end ("round 2"). SPEC.md changed in §3 Pairing (the bullet "A named brand is compared with its own pack first") and in §7 (the paragraph on refusing media, the heading, amounts, the boxes, turn playback). Read those first.

## The contract's new cases
1. **Refuse media the report wasn't made from.** `render_brief` and `coverage_lines` first recompute `intake_id` exactly as `run_intake` does and raise `ValueError` when it differs. Use the loop's own preparation and hash: `_prepare` and `_intake_id` in `anamnesis/agent/loop.py`. Either import them or move them to a small shared helper the loop also uses. Then prepare every photo once per call, and delete the brief's own `_prepared` and the extra preparation in `coverage_lines`. After the check a region's crop can't fail, so don't swallow a `crop_region` `ValueError` any more: let it raise, rather than leave a link that points nowhere.
2. **A named brand is compared with its own pack first.** In `reconcile_all` the same-brand preference now comes **before** the score: sort by (not same brand, −score, `claim_id`, `observation_id`). Contract: `test_a_named_brand_is_compared_with_its_own_pack_first`.
3. **Headings skip blank lines.** Use the first non-blank line, stripped, of the claim's `name_text`, otherwise of the label text, otherwise "Unnamed pack".

## Review findings (no contract case: the CEO checks 4–7 and 12–16 in a browser)
4. **The boxes hide the photo.** The `<rect>`s have no fill or stroke, so SVG's default black fill paints over each pack. Make every box an outline with a transparent fill, so the whole box stays clickable: `fill: transparent`, a visible stroke such as `#d9480f`, `stroke-width: 3`, `vector-effect: non-scaling-stroke`. Add a unit test that the rule is in the style.
5. **Turn playback.** The script adds a new `timeupdate` listener on every click and removes it only at that turn's own end, so an earlier turn's listener pauses a later one straight away. Register **one** `timeupdate` listener and keep one shared end time. A click sets that end time and `currentTime`, then calls `play()`; the listener pauses at the end and clears it. Following an evidence link to a turn should play that turn too. Still exactly one inline script and no `on…` attributes.
6. **The page scrolls sideways on a phone.** Crops show at their natural size: on a 382 px screen the page is 573 px wide, and a crop from a 12 MP phone photo can be about 1,650 px wide. Give every `img` `max-width: 100%; height: auto`. Nothing else may make the page wider than the screen.
7. **Evidence links run together.** The text reads "Evidence: turn-015595e0869ee-0", with no separator and no labels. Label each kind and separate the links, for example "Heard in: turn-0 (0:00–0:12)" and "Seen in: region 15595e0869ee-0".
8. **Fixed text outside `templates.py`.** Move every remaining fixed string the page prints to `templates.py`: "Units per intake", "Intakes per day", "As needed", "yes", "no", " per ", the alt texts, and the new labels from this round. Add all of them, with the existing field labels, to your advice test.
9. **Amount tests.** `test_brief_amounts_print_as_plain_decimals` compares a Decimal with itself. Replace it with one that renders "100.0" and "0.50" and checks the page.
10. **Across medicines.** The link text must be the claim's `name_text`, linked to that claim's turns, not the turn id.
11. **Shape.** Import `_claim_identity` at the top of `overlap.py`; there is no import cycle. Remove the dead `_UNCONFIRMED` branch in `_section_of`.

## From the CEO's browser check
12. **Turns must look playable.** Start each turn with its time range as a visible `<button type="button">`, for example "▶ 0:00–0:12". Clicking the button or the turn plays that turn only.
13. **A crop needs a caption.** Give each region figure a `<figcaption>` with the photo number, the region id, and the reading's readability (or "not read").
14. **A visible title.** Put an `<h1>` with the brief's title at the top of the header.
15. **Arabic.** Put `dir="auto"` on every element that holds source text (transcripts, names, label text), so Arabic reads right to left and mixed lines keep their order.
16. **Keep it plain.** The page is a clinician's working document, not a dashboard. Keep the style short, give the disagreement section a visible accent (for example a left border), and keep the two sides side by side above about 640 px.

## Rules (same as round 1)
- **Never create, modify or delete anything under `tests/contract/`. A batch that touches it is rejected automatically.**
- Don't edit `SPEC.md`, `scripts/`, `evidence/` or `docs/`. No network, no API keys, no git commits, no new dependencies.
- Run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.
- Keep `brief.py` under about 400 lines. If it grows, move the HTML pieces into a small helper module.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass, and `git status --porcelain tests/contract` prints nothing. Reply with the files you changed, one line per numbered item, the final test count, and anything in this brief you think is wrong.
