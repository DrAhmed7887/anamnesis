muse muse-spark-1.3, batch 21, started 2026-10-28T09:23:44Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Batch 21 done. All three gates pass: `ruff check .` clean, `pytest -q` 985 passed, `git status --porcelain tests/contract` empty.

Files changed (8 source, 3 test):

- [numbers.py](anamnesis/providers/numbers.py) (1): `_AMOUNT_RE` now allows only ASCII, Arabic-Indic, and extended Arabic-Indic digits; fullwidth/Devanagari no longer parse, `٫` still reads as a dot.
- [stated.py](anamnesis/providers/stated.py) (1, 2, 5): `_DIGIT_RUN` uses the same three sets and treats `٬` as a run separator like `,` (so `١٬٠٠٠` states nothing); new `_since_thousand`/`_split_hundreds` close the earlier number when a hundred arrives with 100+ since the last thousand, moving trailing plains after the last `and` to the new number.
- [templates.py](anamnesis/schema/templates.py) (3): formulation question is now exactly "What salt or release form is shown on your medicine pack?"
- (4) Pins: no code change; salt-in-free-text and escaped `dir="auto"` Ingredient rows still pass.
- [brief_html.py](anamnesis/brief_html.py) (6): `_ingredient_html` wraps each amount+unit in `<bdi dir="ltr">`, one per combination ingredient.
- [claims.py](anamnesis/providers/claims.py) / [meta.py](anamnesis/providers/meta.py) (7): replaced the one amount sentence in each prompt with the digits/label-text/English-INN wording; all other sentences unchanged, lines within 110 chars.
- [medication.py](anamnesis/schema/medication.py) (8): added the 35 French/Spanish/German/Latin alias keys (casefolded), each salt form mapping to its English moiety+salt.
- [reconcile.py](anamnesis/core/reconcile.py) (9): `_pair_score` returns 3 for a strength-less claim whose intake reconciles as `match` with the pack.
- [test_stated_extra.py](tests/unit/test_stated_extra.py), [test_qm_fixes_extra.py](tests/unit/test_qm_fixes_extra.py): updated the three pinned cases (`١٬٠٠٠`→`set()`, two `<bdi>` strength rows). New [test_b21_extra.py](tests/unit/test_b21_extra.py) holds 10 focused tests (codepoints used for confusable glyphs).

Nothing in the brief looks wrong. Two readings worth pinning: for (5) I count only explicit `and` as the separator for moving plains (a `و` on the incoming hundred itself separates with nothing moving); for (9) "would reconcile as match" is the full `_pair_type`, not intake-only. Both pass every pinned test including both pack orders.

## Round 2
muse muse-spark-1.3, batch 21 round 2, started 2026-10-28T09:51:31Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Done. Gate passes: `ruff check .` clean, `pytest -q` 1004 passed, `git status --porcelain tests/contract` empty.

Files changed (round 2 only):
- [stated.py](anamnesis/providers/stated.py)
- [medication.py](anamnesis/schema/medication.py)
- [test_b21_extra.py](tests/unit/test_b21_extra.py)

Per item:
1. Replaced `last_and` with `_hundred_cut(words, token)`: cut before final plain 1–9 unless hundred carries `و`.
2. Plain ≥100 with run ≥100 closes via `_close`; nothing moves, thousand run stays single.
3. `_word_amounts` 45 lines; `_since_thousand` delegates to `_run_value`; literal `و`; removed `_split_hundreds`/`last_and`.
4. `_DIGIT_RUN` is `(?<![\d.,٬])…(?!\d)`; foreign-adjacent runs state nothing.
5. `_inn_and_salt` uses `normalize("NFC", name).strip().casefold()`; NFD aliases resolve.
6. Prompts untouched; advice sentences already present and pinned by contract.

Final count: 1004 passed.

Possible brief gap: item 2 says “plain worth 100 or more (ميتين, تلتمية…تسعمية)” but the plain table also holds `الفين`=2000, which my `>=100` also splits; no contract case covers it.

## Round 3
muse muse-spark-1.3, batch 21 round 3, started 2026-10-28T10:02:39Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Round 3 done. Gate passes: `ruff check .` clean, `pytest -q` 1018 passed, `git status --porcelain tests/contract` empty.

Files changed (this round): [stated.py](anamnesis/providers/stated.py), [test_b21_extra.py](tests/unit/test_b21_extra.py).

1. «ألفين» closes thousands: `_run_value` moves plains ≥1000 into the total with current reset, `_since_thousand` restarts after the last thousand word or plain ≥1000 (and its `_` loop var renamed to `value` since it is now read).
2. Filler "a": in `_word_amounts`, a hundred word preceded by filler `a` cuts after all words so far, so nothing moves.
3. Atomic digit run: `_DIGIT_RUN` wraps the run in `(?>...)` so decimals touching a foreign digit state nothing instead of backtracking to the head.
4. Tests: added `test_alfain_closes_the_thousands_part` and `test_nothing_moves_after_the_filler_a` to `tests/unit/test_b21_extra.py`.

Final test count: 1018 passed.

Anything wrong in the brief: only a nit — it says the project runs Python 3.12, but the venv here is 3.13.9 (atomic groups work in both, so the fix is unaffected). One edge the brief leaves implicit: if a nonzero current ever precedes a plain ≥1000 (e.g. unnatural "خمسة ألفين"), my literal reading discards that current on reset rather than folding it in; no natural input hits this, and each word still states its own value.
