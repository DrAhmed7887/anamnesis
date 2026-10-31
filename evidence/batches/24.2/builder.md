muse muse-spark-1.3, batch 24.2, started 2026-10-30T04:41:14Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Batch 24.2 done.

A finding box now shows its catalogue codes only when that side agrees with its own name, reusing the reconciler's identity check. Conflicting claim ("Concor" + atorvastatin) and pack sides show no codes line, and the WHO reference line appears only when a codes line remains.

Changed:
- [reconcile.py](anamnesis/core/reconcile.py:68): added public `claim_identity_conflict` / `pack_identity_conflict` wrappers around `_claim_identity` / `_pack_identity`.
- [brief_html.py](anamnesis/brief_html.py:211): `_codes_entry` returns None when the wrapper reports a conflict (claim side, or pack side when no claim).
- [test_b24_2_extra.py](tests/unit/test_b24_2_extra.py:31): `test_panadol_extra_with_single_ingredient_strength_shows_no_codes_line` — Panadol Extra with only paracetamol in its strength shows no codes line and no reference.

Verified:
- `.venv/bin/ruff check .` → All checks passed.
- Focused run (`test_b24_2_codes_conflict`, `test_b24_1_codes`, new extra) → 24 passed.
- Full `.venv/bin/python -m pytest -q` → 2416 passed, 1 error: `test_finetune_fireworks.py::test_http_over_a_real_socket...` fails with `PermissionError` binding a local socket, which the sandbox forbids. That is the only failure; the gate runs outside the sandbox.
- `git status --porcelain tests/contract` → empty. Only the two source files plus the new unit test are touched.
