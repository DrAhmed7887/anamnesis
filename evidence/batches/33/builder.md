muse muse-spark-1.3, batch 33, started 2026-11-02T11:09:29Z
muse: workspace root: the repository (cwd default)
muse: warning: rules file at CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
Done.

What I built:
- In `_side_salts` ([reconcile.py](anamnesis/core/reconcile.py:282)), each strength/intake `inn` is now also read through `_text_salts` (whole-word aliases + `_loose_salts`), beside the existing exact `part.salt or salt_of(part.inn)`. Both sides share the path. Nothing else changed: no salt table, no `_nominal_pack_amount`, no scalar `inn`, no catalogue matching.
- Own tests in [test_b33_extra.py](tests/unit/test_b33_extra.py:1): 8 tests, generic over `INN_ALIASES`/catalogue — longer alias labels (strength + intake), loose `(as salt)` and brand+salt forms, no-salt labels, scalar exactness, pack-side mismatch via `reconcile_pair`, nominal lookup ignoring longer labels.

Anything wrong: nothing blocking. Two notes: the scalar test passes via the identity conflict (rule 3) before salts are compared, so it doesn't isolate the scalar rule on its own; and longer labels of combination-only moieties (amoxicillin) give `ingredient_mismatch` not `formulation_mismatch` because `_resolve_inn` doesn't resolve them — contract only covers single-INN moieties, so I scoped my pack-side test the same way.

Tests: `ruff check .` passes. `pytest -q`: 2922 passed, 1 error — `test_http_over_a_real_socket...` fails with `PermissionError` binding a local socket, the sandbox-forbidden test the brief names; it is the only failure. B33 contract: 38 passed. `git status --porcelain tests/contract` is empty.
