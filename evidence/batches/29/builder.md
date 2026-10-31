muse muse-spark-1.3, batch 29, started 2026-10-31T14:11:17Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Done. Batch 29 is built and the goal is closed.

**What I built**
- In [claims.py](anamnesis/providers/claims.py): added `_COMBINATION_SENTENCE` (the SPEC §2 sentence, word for word) and `_SPARK_CLAIM_PROMPT = _SYSTEM_PROMPT + " " + sentence`. `MetaClaimExtractor` now sends `_SPARK_CLAIM_PROMPT` as its system message. `_SYSTEM_PROMPT` is untouched, so `glimmer.py` and `finetune/common.py` (both built on it) are unchanged, as is the schema, parser, and checks.
- In [test_b29_extra.py](tests/unit/test_b29_extra.py): 4 tests pinning the sentence text, the single-space join, the exact system message Spark sends (via mock transport, generic turn, empty-claims reply), and that Glimmer/fine-tune keep the trained prompt without the sentence.

**Anything wrong in the brief, SPEC, or contract**
- Nothing blocking. One naming wrinkle worth knowing: `glimmer.py` imports claims' `_SYSTEM_PROMPT` under the alias `_SPARK_SYSTEM_PROMPT`, which now reads stale (Spark's prompt is the longer one). I left it alone since the brief says those files don't change, and named the new constant `_SPARK_CLAIM_PROMPT` to avoid colliding with that alias.
- I verified no earlier contract or unit test pins `MetaClaimExtractor`'s exact system message or an exact claim-call estimate — all are substring checks on the untouched `_SYSTEM_PROMPT` or bounds derived from the sent body — so the longer message breaks nothing.

**Final test count**
- `.venv/bin/ruff check .`: passes.
- `.venv/bin/python -m pytest -q`: 2702 passed, 1 error — `test_finetune_fireworks.py::test_http_over_a_real_socket_…` errors binding a local socket (`PermissionError`), the sandbox-forbidden network test the brief names. It is the only failure and is unrelated to this change.
- `git status --porcelain tests/contract`: prints nothing.
