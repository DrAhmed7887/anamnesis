muse muse-spark-1.3, batch 19.1, started 2026-10-27T20:20:42Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Batch 19.1 done. All three gates pass: `ruff check .` clean, `pytest -q` 696 passed, `git status --porcelain tests/contract` empty.

Files changed (6 source, 2 test; nothing under `tests/contract/`, `SPEC.md`, `scripts/`, `evidence/`, `docs/`):

- [numbers.py](anamnesis/providers/numbers.py) (1): `parse_amount_text` replaces `٫` (U+066B) with `.` before validation, so all dot rules apply unchanged. `٬` still fails the amount regex.
- [guardrails.py](anamnesis/core/guardrails.py) (2): added `_ARABIC_ADVICE` matching the six words with an optional leading clitic (`وال|بال|فال|لل|ال|و|ف|ب|ل`), checked against `normalise(text)` so diacritics/tatweel are stripped first. Raw-text `_ADVICE` untouched.
- [reconcile.py](anamnesis/core/reconcile.py) (3, 9): added normalised-spelling `ممتده`, `بطيئه` to both release-word sets; `reconcile_all` docstring now says "by same brand first, then score, then ids".
- [templates.py](anamnesis/schema/templates.py) (4, 5, 9): formulation note is exactly "Reported and pack formulations differ (salt or release form)."; fourth scope line appended; `FIELD_EVIDENCE` deleted.
- [overlap.py](anamnesis/core/overlap.py) (6): `_counted` skips claims whose `_claim_identity` reports a conflict.
- [brief_html.py](brief_html.py) (7, 8): new `_ingredient_html` renders `salt` escaped after the INN; used by strength rows (both sides) and the patient intake row. `_photos_html` raises `ValueError` when a region's photo is missing instead of `continue`.
- [test_qm_fixes_extra.py](tests/unit/test_qm_fixes_extra.py) (new, 17 tests): one focused check per change, e.g. `12٫000`→None, `الخذ`/`يَجِب` caught, `بالممتدة` said while near-miss `ممتاز` is not, hostile salt escaped, stray region raises.
- [test_brief_extra.py](tests/unit/test_brief_extra.py): removed the `FIELD_EVIDENCE` import and usage (no test pinned the old note text or three scope lines).

Final count: 696 passed (was 19 failed / 17 passed on the 19.1 contract file before the fix).

Anything wrong in the brief: nothing blocking. Two notes: (a) change 9 says the turn script "passes" in Node — confirmed, all script/dir tests passed before and after; (b) the brief lists `brief_html.py` strength/intake rows but the pack side has no intake row, so the shared `_ingredient_html` helper covers exactly the three rows named (patient strength, pack strength, patient intake).

## Round 2
muse muse-spark-1.3, batch 19.1 round 2, started 2026-10-27T20:37:21Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Round 2 done. `.venv/bin/ruff check .` passes, `.venv/bin/python -m pytest -q` passes (707 passed), `git status --porcelain tests/contract` prints nothing.

Files changed (round 2 edits): `anamnesis/providers/spark.py`, `anamnesis/core/overlap.py`, `anamnesis/schema/templates.py`, `anamnesis/brief_html.py`, `anamnesis/core/catalogue.py`, `anamnesis/core/reconcile.py`, `anamnesis/core/guardrails.py`, `tests/unit/test_brief_extra.py`.

1. `spark.py`: new `_check_strength_shape` raises `ValueError` inside the `try` when `strength` has keys beyond `ingredients`/`per`/`release` or an ingredient beyond `inn`/`amount`/`unit` (subset checks, so a missing `release` still defaults).
2. `overlap.py`: a conflicted claim now counts by `identity ∩ catalogue.resolve(name_text).inns`, skipped when the name resolves to nothing or shares nothing.
3. `templates.py` gains `FIELD_INN = "Ingredient"`; `brief_html.py` renders the scalar `inn` verbatim, escaped, `dir="auto"`, right after the name/label on both sides; `FIELD_INN` added to the advice test.
4. No code change needed: the current `\b` boundaries already pass `يتناول`, `المتناول`, `تناولت الدواء`, `أخذ` while catching the clitic/mark cases; the new contract test pins this.
5. `ARABIC_CLITICS` defined once in `catalogue.py` and used in `catalogue.py`, `reconcile.py` (replacing `_RELEASE_CLITICS`), and `guardrails.py`; the six Arabic words removed from the raw `_ADVICE` pattern.

Nothing in the brief looks wrong. One observation: item 5's claim that the normalised check catches every raw Arabic hit held up — `normalise` only strips marks/punctuation and folds alef variants, a strict superset for these words, and the full suite confirms no previously-caught string passes now.
