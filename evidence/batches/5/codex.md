codex gpt-6-sol, batch 5, started 2026-10-27T10:15:50Z

Implemented the live Meta adapters in [meta.py](<repo>/anamnesis/providers/meta.py) and added mocked-transport unit tests in [test_meta_extra.py](<repo>/tests/unit/test_meta_extra.py). The adapters validate inputs, check SpendGuard before calls, charge returned usage, and redact API keys from errors.

Verification: `ruff check .` passed; `pytest -q` passed with **195 tests**. No contract tests were changed, no tests used the network, and nothing was committed.
tokens used
48,958
Implemented the live Meta adapters in [meta.py](<repo>/anamnesis/providers/meta.py) and added mocked-transport unit tests in [test_meta_extra.py](<repo>/tests/unit/test_meta_extra.py). The adapters validate inputs, check SpendGuard before calls, charge returned usage, and redact API keys from errors.

Verification: `ruff check .` passed; `pytest -q` passed with **195 tests**. No contract tests were changed, no tests used the network, and nothing was committed.
