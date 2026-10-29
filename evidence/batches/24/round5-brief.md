# Batch 24, round 5: the supervisor's review of round 4

You are the builder for batch 24, round 5. Your round 1–4 code is still in the working tree, uncommitted: keep it and build on it. Keep each change surgical: no refactors, and nothing outside this brief.

## Goal
Make `tests/contract/test_b24_round5.py` pass, and keep every other test green, including all of `tests/contract/test_b24_*.py`. First read the SPEC.md lines marked "round 5".

## The fixes. Each one is pinned in `test_b24_round5.py`
**Each case stated a number nobody said, and an invented amount of that number reached a false `match`.**

1. **Two Spanish or German number words under 100 never add up unless `y` joins them** (`anamnesis/providers/stated.py`).
   - **The failure:** "a las diez treinta" (10:30) stated 40; "dos tres pastillas" 5; "zweieinhalb Fünf-Milligramm-Tabletten" 7.5; "dos cincuenta" 52.
   - **The rule:** when a Spanish or German plain number word under 100 comes right after a plain word under 100 in the run, and the token before it isn't `y`, close the run first.
   - **What must keep working:** a hundreds word still takes a smaller number after it ("ciento veinte" 120, "doscientos cincuenta" 250, "mil quinientos" 1500), and "fünf hundert" is still 500.
2. **A half never joins a clock hour.** When `la` or `las` comes before the hour, the `y` before `medio` or `media` joins nothing, even when a dose word follows the half. "a las dos y medio comprimido" must state 2 and 0.5, never 2.5.
3. **German `Acht` meaning "care" states nothing.** That is `acht` after `ausser`, or before `geben`, `nehmen` or `lassen` and their participles: "in Acht nehmen", "außer Acht lassen", "Acht geben". "in acht Tagen" is still 8.
4. **Grounding reads in NFC** (`anamnesis/providers/claims.py`). Normalise both the field and the cited turns to NFC before matching, so a decomposed "fünf" label is still an amount word.
5. **"una y media" is 1.5.** The article before `y medio` or `y media` joins the half, except as a time ("la una y media").

## Rules
- **Never create, modify or delete anything under `tests/contract/`, any `conftest.py`, `pyproject.toml` or `uv.lock`. A batch that touches them is rejected automatically.** A contract test that is skipped or xfailed fails the gate too.
- Don't edit `SPEC.md`, `scripts/`, `evidence/`, `docs/` or `finetune/`.
- Work only inside this repository. No network, no API keys, no git commits, no new dependencies.
- `uv` can't write its cache in your sandbox, so run the tools as `.venv/bin/ruff` and `.venv/bin/python -m pytest`.
- **One test needs a local network socket that your sandbox forbids.** If it is the only failure, say so and close your goal. The gate runs outside the sandbox.
