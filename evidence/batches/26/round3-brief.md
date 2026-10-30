# Batch 26, round 3: one test that can fail, and one message

You are the builder for round 3 of batch 26 of Anamnesis. Rounds 1 and 2 are in the working tree, uncommitted. Change only what this brief lists. Everything the earlier briefs said still holds, including the hard rules.

The supervisor checked round 2. The product code is correct, and round 2's server passed its live check on Modal. Two things remain.

## 1. The symlink test must be able to fail (`tests/unit/test_b26_extra.py`, about lines 201–208)
**The gap:** the symlink and its target both sit in `tmp_path`, outside `evidence/raw/media/public/voice/`, so any guard refuses them. A guard that stopped following links (for instance `Path(os.path.abspath(args.voice))` in place of `.resolve()`) still passes this test.

**The fix:**
- point the script's `MEDIA` at a folder under `tmp_path` (`monkeypatch.setattr(il, "MEDIA", tmp_path / "media")`);
- create `media/public/voice/`;
- put the symlink *inside* that folder, pointing to a file outside it;
- assert that `--extractor glimmer` with that link as `--voice` is refused with "may go to Modal" before any key or client.

Add one more case: a real file inside that voice folder passes the voice guard. Use a valid URL there, and stop the run at the first key read with a stub `keychain` that raises, so you can tell it passed.

## 2. The URL refusal prints the host, not the URL (`scripts/intake_live.py`, about line 243)
**The gap:** a URL such as `https://u:secret@x.modal.run` is printed whole, password included.

**The fix:** the refusal message names only the URL's host (or says the URL is missing). The message must still contain `modal.run`.

## Rules
- **Locked files:** never create, modify or delete anything under `tests/contract/`, any `conftest.py`, `pyproject.toml` or `uv.lock`.
- **Off limits:** don't edit `SPEC.md`, `docs/`, `evidence/`, `briefs/`, `NOTICE`, `scripts/batch.sh` or `scripts/goal_check.py`, and change nothing in `finetune/`. Don't open anything under `evidence/` or `finetune/data*`.
- **No outside contact:** no network, no API keys, no `modal` commands, no git commits.
- **Tools:** run them as `.venv/bin/ruff` and `.venv/bin/python -m pytest`. One test needs a local network socket that your sandbox forbids; if it is the only failure, say so and close your goal.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass from the repo root, and `git status --porcelain tests/contract` prints nothing.

Reply with a short report: what you changed for each item, and the final test count.
