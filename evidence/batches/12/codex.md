codex gpt-6-luna, batch 12, started 2026-10-27T11:16:32Z

Implemented billing integrity and retries across Voice, SAM, Spark labels, and claim extraction. Billing-uncertain failures are logged at the pre-call estimate; 4xx and 429 responses aren’t charged. Retried calls return traces with prior charged call IDs and costs.

Updated [the shared retry helper and trace fields](<repo>/anamnesis/providers/base.py:34), [ledger writes](<repo>/anamnesis/providers/spend.py:34), provider handling, and [SPEC.md](<repo>/SPEC.md:84). Added [ledger unit tests](<repo>/tests/unit/test_ledger_extra.py:1) and updated the timeout test for the new behavior. `tests/contract/` remains untouched.

Verification passed: `uv run ruff check .` and `uv run pytest -q` (343 passed). No commit made.
tokens used
130,536
Implemented billing integrity and retries across Voice, SAM, Spark labels, and claim extraction. Billing-uncertain failures are logged at the pre-call estimate; 4xx and 429 responses aren’t charged. Retried calls return traces with prior charged call IDs and costs.

Updated [the shared retry helper and trace fields](<repo>/anamnesis/providers/base.py:34), [ledger writes](<repo>/anamnesis/providers/spend.py:34), provider handling, and [SPEC.md](<repo>/SPEC.md:84). Added [ledger unit tests](<repo>/tests/unit/test_ledger_extra.py:1) and updated the timeout test for the new behavior. `tests/contract/` remains untouched.

Verification passed: `uv run ruff check .` and `uv run pytest -q` (343 passed). No commit made.
