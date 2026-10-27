muse muse-spark-1.3, batch 19, started 2026-10-27T19:15:00Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Batch 19 is done. All three gates pass: `ruff check` clean, **628 tests passed**, `tests/contract` untouched.

Files changed:

- [anamnesis/providers/meta.py](anamnesis/providers/meta.py): (1) `spark_call_estimate` adds `len(json.dumps(body["response_format"]))` to the character count when present.
- [anamnesis/core/catalogue.yaml](anamnesis/core/catalogue.yaml): (2) appended the Gelocatil entry (ES, paracetamol, immediate, splittable null, both Arabic aliases, synthetic).
- [anamnesis/core/catalogue.py](anamnesis/core/catalogue.py): (3) added public `brand_entry` wrapping `_brand_entry`.
- [anamnesis/core/reconcile.py](anamnesis/core/reconcile.py): (3) `reconcile_all` sorts by score, then same-brand preference (claim `name_text` and pack `label_text`+country resolving to the same brand), then `claim_id`, then `observation_id`.
- [anamnesis/core/overlap.py](anamnesis/core/overlap.py): (4) new; `OverlapKind`, frozen `Overlap`, `DRUG_CLASSES` with only beta-blockers, and `cross_medication` per SPEC §7 (claims only, discontinued excluded, unresolvable skipped, product from brand lookup else normalised name, ingredient-then-class ordering).
- [anamnesis/schema/templates.py](anamnesis/schema/templates.py): (5) scope lines, overlap notes, section headings/order, None/Unnamed-pack/missing-side strings, A3 labels, field labels, coverage formats. All pass `assert_no_advice`.
- [anamnesis/brief.py](anamnesis/brief.py): (6) new, 384 lines; `coverage_lines` and `render_brief` with header, 8 ordered sections, finding articles with side-by-side sides, overlap articles, coverage list, prepared-photo figures with SVG boxes, region crops, one audio element, turn list, exactly one inline script, no `on*` attributes, all source strings escaped, plain-decimal amounts, deterministic output.
- [tests/unit/test_brief_extra.py](tests/unit/test_brief_extra.py): (7) new; 11 tests covering fixed-text advice safety, overlap ordering, coverage edge cases, escaping, and the estimate/brand helpers.

Anything I think is wrong in the brief: change 1 says label reads keep `max_tokens: 4000` as if that constrains the estimate, but `spark_call_estimate` already reads `max_tokens` from the body, so the estimate change interacts with both call types by construction — the "nothing else changes" clause is really about not touching the call sites, which I didn't. Also the coverage spec's "no `segment` step" rule keys off the prepared-sha prefix, so an undecodable photo that still logged a bare 12-hex target can never hit the budget line — correct, since undecodability is checked first, but worth knowing the ordering does real work there.

## Round 2
muse muse-spark-1.3, batch 19 round 2, started 2026-10-27T19:35:25Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Done. Ruff passes, pytest passes (638 passed), `tests/contract` untouched.

Files changed: [brief.py](anamnesis/brief.py) (slimmed to 125 lines), [brief_html.py](anamnesis/brief_html.py) (new, 334 lines, holds the HTML pieces), [reconcile.py](anamnesis/core/reconcile.py), [overlap.py](anamnesis/core/overlap.py), [templates.py](anamnesis/schema/templates.py), [test_brief_extra.py](tests/unit/test_brief_extra.py).

1. `render_brief`/`coverage_lines` recompute `intake_id` with the loop's own `_prepare`/`_intake_id` and raise `ValueError` on mismatch; photos prepared once per call, `_prepared` deleted, `crop_region` errors propagate.
2. Pairing sorts by (not same brand, −score, `claim_id`, `observation_id`).
3. Headings use the first non-blank stripped line of `name_text`, else label text, else "Unnamed pack".
4. Boxes get `fill:transparent`, `#d9480f` stroke, `stroke-width:3`, `vector-effect:non-scaling-stroke` in the stylesheet, pinned by `test_boxes_are_transparent_outlines`.
5. One `timeupdate` listener with one shared end time; clicks set end + `currentTime` and play; `#turn:` links play their target too; still one inline script, no `on…` attributes.
6. Every `img` gets `max-width:100%;height:auto`; no other rule sets a fixed width.
7. Evidence reads "Heard in: turn-0 (0:00–0:12)" / "Seen in: region …", comma-separated within a kind, semicolon between kinds.
8. All page strings (`STRENGTH_PER`, `REGIMEN_*`, `YES`/`NO`, alt texts, `HEARD_IN`/`SEEN_IN`/etc.) live in `templates.py` and are all in the advice test with the `FIELD_*` labels.
9. `test_brief_amounts_print_as_plain_decimals` now renders `100.0`/`0.50` and asserts the page shows `100 mg`/`0.5` without trailing zeros.
10. Across-medicines links show the claim's `name_text`, one link per turn.
11. `_claim_identity` imported at the top of `overlap.py`; dead `_UNCONFIRMED` branch and constant removed.
12. Each turn starts with `<button type="button">▶ 0:00–0:12</button>`; button clicks bubble to the turn's player.
13. Each region figure has `<figcaption>` with photo number, region id, and readability or "not read".
14. Header starts with `<h1>` carrying `BRIEF_TITLE`.
15. `dir="auto"` on headings, name/strength/intake/label fields, across links, and transcript spans.
16. Style stays short with a `#d9480f` left-border accent on `#disagree`; sides stay side by side above 640 px.

One thing I think is wrong: item 1's premise "after the check a region's crop can't fail" holds only for reports actually produced by `run_intake` — a hand-built report with a valid `intake_id` but bogus region geometry can still fail the crop. Letting it raise is still the right behavior, but the guarantee is slightly overstated.
