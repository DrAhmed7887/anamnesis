muse muse-spark-1.3, batch 24.1, started 2026-10-29T22:42:55Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Batch 24.1 is implemented and audited. Everything in the brief passes; one gate command cannot go green inside this sandbox for a pre-existing environmental reason.

**Done and verified**
- Catalogue ([catalogue.py](anamnesis/core/catalogue.py), [catalogue.yaml](anamnesis/core/catalogue.yaml)): `atc`/`rxcui` fields with defaults, all nine codes tables entries (RxCUIs as quoted strings), plus Emconcor, Sortis, Nolotil (synthetic, no aliases). No `snomed`/`vtm`/SNOMED id anywhere in the touched files.
- Brief ([templates.py](anamnesis/schema/templates.py), [brief_html.py](anamnesis/brief_html.py), [brief.py](anamnesis/brief.py)): codes line under the two sides (claim name, else pack label when claimless; ATC-only/RxNorm-only/multi-RxCUI handled; escaped; no links), reference line once after the last section only when codes shown, exact strings, no NLM. `_finding_html` takes `catalogue` with a default; old 4- and 5-arg calls verified working.
- Tests: new [test_b24_1_extra.py](tests/unit/test_b24_1_extra.py) covers ATC-without-RxCUI, pack-only finding codes, and single reference line with three coded findings.
- Checks observed: `.venv/bin/ruff check .` → all pass; `tests/contract` → 1727 passed, 0 skipped/xfailed; `git status --porcelain tests/contract` → empty; first-nine catalogue order still matches `FINETUNE_BRANDS`; finetune/ untouched.

**One finding, not caused by this batch**
`.venv/bin/python -m pytest -q` gives 2410 passed plus 1 error in `tests/unit/test_finetune_fireworks.py::test_http_over_a_real_socket...`, which binds a localhost TCP socket. The sandbox denies it (`PermissionError: Operation not permitted`). I proved it pre-existing by stashing all my changes and re-running that test on the untouched tree — identical error — then restoring. An unsandboxed retry was denied (approval prompts disabled). Per the brief I left that unrelated test alone.

**Next step for the main agent:** re-run `.venv/bin/python -m pytest -q` outside this sandbox; if green, the goal is met and can be closed. The goal is left active at 95%.Batch 24.1 is implemented, audited, and green everywhere except one gate command that this sandbox cannot satisfy. The goal is marked blocked for that reason alone.

**What was built**
- Catalogue: `CatalogueEntry` gained `atc: str | None = None` and `rxcui: tuple[str, ...] = ()`, loaded from optional YAML keys ([catalogue.py](anamnesis/core/catalogue.py)). All nine existing entries carry their exact ATC/RxCUI codes with RxCUIs as quoted strings, followed by Emconcor, Sortis, and Nolotil with the specified inns, release, splittability, countries, and codes ([catalogue.yaml](anamnesis/core/catalogue.yaml)). No `snomed`/`vtm`/SNOMED id in the catalogue or code (grep-verified).
- Brief: each finding box shows one codes line under the two sides when its claim's `name_text` (or, when claimless, its pack's `label_text`) resolves to a coded entry — `Catalogue codes: ATC … · RxNorm …`, only the codes present, RxCUIs joined with `", "`, escaped, no links. One reference line per page after the last section iff any codes line was shown, with the exact WHO/AEMPS-CIMA/RxNav/NOTICE wording and no NLM. Both strings live in [templates.py](anamnesis/schema/templates.py); `_finding_html` takes `catalogue` from `render_brief` with a default keeping old callers working ([brief_html.py](anamnesis/brief_html.py), [brief.py](anamnesis/brief.py)).
- Tests: new [test_b24_1_extra.py](tests/unit/test_b24_1_extra.py) covers an ATC-only entry, a pack-only finding showing its pack's codes, and a single reference line on a three-coded-finding page.

**Evidence observed**
- `.venv/bin/ruff check .` → all checks pass.
- `tests/contract` → 1727 passed, 0 skipped/xfailed; `git status --porcelain tests/contract` → empty.
- `.venv/bin/python -m pytest -q` → 2410 passed, 1 error in `tests/unit/test_finetune_fireworks.py::test_http_over_a_real_socket...`, which binds a localhost TCP socket. The sandbox denies it (`PermissionError: Operation not permitted`). Proven pre-existing: with all my changes stashed, the untouched tree fails that test identically; an unsandboxed retry was denied (approval prompts disabled). That test is unrelated to this batch, so I left it alone per the surgical-change rule.
- Compatibility checks: entries without codes load as `(None, ())`; old 4- and 5-arg `_finding_html` calls work; reference string is character-exact; first-nine catalogue order still matches `FINETUNE_BRANDS`; `finetune/`, `NOTICE`, `SPEC.md`, scripts, and docs untouched.

**To close the gate:** re-run `.venv/bin/python -m pytest -q` outside this sandbox. If it is fully green there, batch 24.1 is done.
