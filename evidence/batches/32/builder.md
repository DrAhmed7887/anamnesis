muse muse-spark-1.3, batch 32, started 2026-11-01T20:43:18Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Done. Batch 32 is complete.

What I built
- [catalogue.py](anamnesis/core/catalogue.py:108): in `Catalogue._matches`, Latin-script names now match with each `b`/`v` as `[bv]`, and accept exactly one joined `tomamos|tomas|toman|tomo|toma` prefix inside the match span, mirroring `ARABIC_CLITICS`. Whole-word boundaries unchanged; Arabic names take the exact same path as before. Six lines added, two removed; no other source touched. `resolve`, `covers`, `is_ambiguous`, `matches_brand`, `mentions_moiety`, and `brand_entry` all follow with no changes of their own.
- [test_b32_extra.py](tests/unit/test_b32_extra.py): 9 catalogue-wide tests (all 73 Latin names, not case-specific): b/v swap resolves identically, every tomar form joined resolves and covers, double prefixes/trailing letters/other prefixes never match, separated "tomo X" still resolves, brand/moiety/ambiguity helpers follow, and all Arabic clitic forms resolve as before.

Anything wrong in the brief, SPEC, or contract
- Nothing blocking. One observation: the SPEC's safety condition (no two Latin names of different products equal once `v`→`b`) is exactly the right guard for full b/v equivalence, and the contract checks it — verified it holds, so no new ambiguity is introduced. The `tomas` form is accentless, matching the SPEC's literal list.

Final test count
- `.venv/bin/ruff check .`: clean.
- `.venv/bin/python -m pytest -q`: 2862 passed, 1 error — the error is solely `test_finetune_fireworks.py::test_http_over_a_real_socket...`, which fails with `PermissionError` binding a local socket that this sandbox forbids, as the brief anticipated.
- `git status --porcelain tests/contract`: empty. Only `anamnesis/core/catalogue.py` modified and `tests/unit/test_b32_extra.py` added. (An untracked `evidence/batches/32/` directory pre-existed; I left it untouched and unopened.)

## Round 2
muse muse-spark-1.3, batch 32 round 2, started 2026-11-02T00:38:13Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Round 2 done. All three supervisor findings are addressed with changes to two files only.

**What changed**

- [catalogue.py](anamnesis/core/catalogue.py): `_matches` now tags each `INN_ALIASES` name with whether it carries a salt, and salt-bearing names match exactly as written — no `b`/`v` fold, no attached *tomar* form. Unsalted Latin names keep the round-1 rule. The five forms moved into a module constant `TOMAR_FORMS` beside `ARABIC_CLITICS`, with a `SPEC §3` docstring line.
- [test_b32_extra.py](tests/unit/test_b32_extra.py): salt-bearing names are excluded from the fold/attach tests (b/v swap, joined *tomar*, `mentions_moiety`, and the two-prefixed-products ambiguity test, which also needs both prefixed names to match), and a new `test_a_salted_name_is_matched_only_as_written` checks each salted alias resolves bare but is not covered swapped or with any of the five forms attached.

**Anything wrong:** before the fix the 5 new round-2 contract cases failed exactly as the review described (salt lost → false `match`); after it they pass, and the over-matching pins (`pisoprolol`, `Norpasc`, `tomóbisoprolol`, etc.) stay unresolved. One caveat on the gates: the full suite shows **2876 passed, 1 error** — the error is `test_http_over_a_real_socket…` failing at `socket.bind` with `PermissionError`, i.e. this session's sandbox blocking real sockets. That test imports only stdlib plus `finetune.fireworks`, touches nothing I changed, and is outside the files I'm allowed to edit. `ruff check` passes and `git status --porcelain tests/contract` prints nothing.

**Final count:** 68/68 batch-32 tests pass (58 contract + 10 unit); full suite 2876 passed plus the one sandbox-blocked socket error.Ruff passes (exit 0) and `tests/contract` is clean, but pytest still exits 1 with 2876 passed and the same single sandbox-blocked socket error in `test_finetune_fireworks.py`; I changed nothing, since that file is outside the brief's allowed scope and the failure is the sandbox denying `socket.bind`, not the code.Batch 32 round 2 is complete. All three supervisor findings are fixed, with changes to exactly the two allowed files.

**What changed**

- [catalogue.py](anamnesis/core/catalogue.py)
  - `_matches` now records whether each `INN_ALIASES` name carries a salt, and salt-bearing names (`metoprolol succinate`, `bisoprololfumarat`, …) match exactly as written: no `b`/`v` fold, no attached *tomar* form. Unsalted Latin names keep the round-1 rule, so `visoprolol` and `Tomovisoprolol` still resolve while `tomometoprolol succinate` no longer covers the salt alias and falls back to `insufficient_information`.
  - The five *tomar* forms moved into a `TOMAR_FORMS` module constant beside `ARABIC_CLITICS`, with a `SPEC §3` docstring line in the same style.
- [test_b32_extra.py](tests/unit/test_b32_extra.py)
  - Salt-bearing names (a `SALTED` set built the same way as the contract's) are skipped in the fold/attach tests: b/v swap, joined *tomar*, `mentions_moiety`, and the two-prefixed-products ambiguity test, which also requires both prefixed names to match.
  - New `test_a_salted_name_is_matched_only_as_written`: each salted alias resolves bare, but neither its b/v-swapped form nor any of the five forms joined to it is covered.

**Verification**

- Before the fix, the 5 new round-2 contract cases failed exactly as the review described (lost salt → false `match`); after it, all pass, and the over-matching pins (`pisoprolol`, `wisoprolol`, `Peloc-Zok`, `Norpasc`, `tomóbisoprolol`, `tomebisoprolol`, `tomababisoprolol`) stay unresolved.
- `.venv/bin/ruff check .` passes (exit 0); `git status --porcelain tests/contract` prints nothing.
- Batch-32 tests: 68/68 pass (58 contract + 10 unit). Full suite: **2876 passed, 1 error** — the error is `test_finetune_fireworks.py::test_http_over_a_real_socket…`, which binds `127.0.0.1:0` at fixture setup. I proved the cause is this session's sandbox, not the code: a bare one-line `bind(('127.0.0.1', 0))` with no product code fails with the identical `PermissionError`. That test imports only stdlib plus `finetune.fireworks`, is outside the brief's allowed files, and will pass in any unsandboxed run; no in-scope change can affect it.

**Anything that looked wrong:** nothing in the batch itself — the salt-loss mechanism, the fix, and the contract's expectations all line up (`_resolve_inn_part` needs a whole-`inn` cover, which the exact-as-written rule now denies to misspelled salts).Batch 32 round 2 is complete. The supervisor's three findings are fixed with changes to exactly the two allowed files, and the remaining full-suite error is proven environmental and out of scope.

**What changed**

- [catalogue.py](anamnesis/core/catalogue.py)
  - `_matches` now records whether each `INN_ALIASES` name carries a salt, and salt-bearing names (`metoprolol succinate`, `amlodipine besilate`, `bisoprololfumarat`, …) match exactly as written: no `b`/`v` fold, no attached *tomar* form. Unsalted Latin names keep the round-1 rule, so `visoprolol` and `Tomovisoprolol` still resolve, while `tomometoprolol succinate` no longer covers the salt alias and the pair falls back to `insufficient_information` instead of a false `match`.
  - The five *tomar* forms moved into a `TOMAR_FORMS` module constant beside `ARABIC_CLITICS`, with a `SPEC §3` docstring line in the same style.
- [test_b32_extra.py](tests/unit/test_b32_extra.py)
  - Salt-bearing names (a `SALTED` set built the same way as the contract's) are skipped in the fold/attach tests: b/v swap, joined *tomar*, `mentions_moiety`, and the two-prefixed-products ambiguity test, which also requires both prefixed names to match.
  - New `test_a_salted_name_is_matched_only_as_written`: each salted alias resolves bare, but neither its b/v-swapped form nor any of the five forms joined to it is covered.

**Verification**

- Before the fix, the 5 new round-2 contract cases failed exactly as the review described (lost salt → false `match`); after it, all pass, and the over-matching pins (`pisoprolol`, `wisoprolol`, `Peloc-Zok`, `Norpasc`, `tomóbisoprolol`, `tomebisoprolol`, `tomababisoprolol`) stay unresolved.
- `.venv/bin/ruff check .` passes (exit 0); `git status --porcelain tests/contract` prints nothing.
- Batch-32 tests: 68/68 pass (58 contract + 10 unit). Full suite: **2876 passed, 1 error**.

**The 1 error is environmental and pre-existing, not a code failure.** It is `test_finetune_fireworks.py::test_http_over_a_real_socket…`, which binds `127.0.0.1:0` in fixture setup. Evidence: a bare one-line `bind(('127.0.0.1', 0))` with no product code fails with the identical `PermissionError`, proving this session's sandbox denies all socket binds; the test file was last committed before this session (`f60c48c`) and is unmodified; it imports only stdlib plus `finetune.fireworks`, which is untouched. No in-scope change can affect it, and editing that file or narrowing the run would violate the brief's hard rules — so an exit-0 full-suite run is unattainable from inside this sandbox, while the suite will pass cleanly in any unsandboxed run.
