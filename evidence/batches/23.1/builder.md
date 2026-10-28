muse muse-spark-1.3, batch 23.1, started 2026-10-28T16:39:44Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Batch 23.1 done. All three gate conditions pass.

Files changed:
- [spark.py](anamnesis/providers/spark.py) (items 1–3)
- [spend.py](anamnesis/providers/spend.py) (item 5)
- [test_b23_1_extra.py](tests/unit/test_b23_1_extra.py) (new, item 6)

Per item:
1. Tablet-word carve-out: added `_CONN_WORD_PER` / `_BEFORE_WORD_PER_RE` covering `/`, `per`, `por`, `par`, `لكل`. `_printed_before_volume` now returns False on a tablet word in the gap only when the connector is `in`/`في`; with a per-connector or slash it matches as usual, so "Calpol 250 mg tab/5 ml" drops while dissolving lines keep.
2. `_AFTER_AMOUNT_RE`: one optional bracket group (`?`) became any number (`*`), so "(as trihydrate) (sugar free) per 5 ml" counts outright.
3. `_ML`: `millilitre/milliliter/mililitro` became `millilitres?/milliliters?/mililitros?`, so plural per-1-ml prints are the reading's own.
4. No code change needed: `_AR_SPOON_RE` already matches `معلقتان`/`المعلقتان` via the existing alternation with optional `ال`. Verified by the contract tests plus new unit pins.
5. `SpendGuard.charge_estimate` raises `ValueError("contributor models are not permitted")` when `-contributor` appears in the stripped, casefolded model id, before amount/reason validation and any ledger write. `SessionGuard.charge_estimate` inherits it since it calls the parent first and records after.
6. New `tests/unit/test_b23_1_extra.py` with 15 cases: per-connector drops (`par`, `∕`, `por`, `لكل`), `in`/`في` keeps, triple/mixed brackets, all three plural per-1-ml forms, both nominative duals, contributor refusal (parent + session, ledger empty, totals zero), and a plain-model charge still working.

Final count: `.venv/bin/ruff check .` clean; `.venv/bin/python -m pytest -q` → 1932 passed; `git status --porcelain tests/contract` prints nothing.

Anything wrong in the brief: item 1's connector list omits `∕` and `／` in the prose ("After `/`, `∕`, `／`, `per`..." is in the title paragraph but the contract docstring says "After `/`, `per`, `por`, `par` or `لكل`") — I treated all three slash forms as refusing, per SPEC §2, which names `/` as the connector family. Also item 2's example shows only `()` groups but the contract mixes `()` and `[]`; the `*` fix covers both since `_BRACKET_ANY` already alternated them.
