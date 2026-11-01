# Batch 31, round 3: the review's last points

You are the builder for round 3 of batch 31 of Anamnesis. Your round-2 code is in the working tree: build on it. SPEC.md §8's subsection "The follow-up by itself" and the contract `tests/contract/test_b31_follow_up.py` (now 46 cases) changed again. Read the subsection's "On the brief" bullet and its new "Known limit" bullet first. Six contract cases fail on your round-2 code, and these three changes fix them:

1. **The header text,** in `anamnesis/schema/templates.py`. `FOLLOW_UP_DONE` becomes exactly: "Anamnesis sent the follow-up itself, for medicines mentioned but not photographed: photos asked for {asked}, received {received}."
2. **A late answer is valid,** in `anamnesis/brief.py`. A `no_reply` or `duplicate` step may name a request in any state: open, withdrawn, or answered later through `add_photo`. Only an `answered` step still needs an answered request. Remove the refusal "an unanswered step names an answered request".
3. **Only the follow-up's own kind of request:** a step whose `kind` isn't `not_photographed` is refused with `ValueError`, because the follow-up never makes another kind of request.

**Also:**
- Move the whole log check out of `render_brief` into one helper, `_check_follow_up_log(review, follow_up)`, in `anamnesis/brief.py`. `render_brief` is 56 lines now.
- Correct `follow_up`'s docstring: it asks only for medicines mentioned but not photographed, not for "every missing photo".
- In your unit tests, drop any check the new contract cases make redundant.

## Hard rules
1. **Locked files:** never create, modify or delete anything under `tests/contract/`, any `conftest.py`, `pyproject.toml` or `uv.lock`. Add no dependency.
2. **Off limits:** don't edit `SPEC.md`, `docs/`, `evidence/`, `briefs/`, `NOTICE`, `finetune/` or any script. Don't open anything under `evidence/` or `finetune/data*`.
3. **Behaviour that stays:** every earlier contract, and everything in `review.py` apart from the docstring.
4. **No outside contact:** no network, no API keys, no `modal` commands, no git commits.
5. **Tools:** run them as `.venv/bin/ruff` and `.venv/bin/python -m pytest`. One test needs a local network socket that your sandbox forbids; if it is the only failure, say so and close your goal.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass from the repo root, and `git status --porcelain tests/contract` prints nothing.

Reply with a short report: what you changed, anything that looked wrong, and the final test count.
