# Batch 31, round 2: the review's fixes

You are the builder for round 2 of batch 31 of Anamnesis. Your round-1 code is in the working tree: build on it. SPEC.md §8's subsection "The follow-up by itself (`follow_up`, batch 31)" has changed, and so has the contract `tests/contract/test_b31_follow_up.py` (now 43 cases). Read both again before you start.

## What changed in the SPEC: do all of it
1. **Only medicines mentioned but not photographed.** The targets are the `not_photographed` entries of `requestable(report)`. A pack that couldn't be read is never the follow-up's to ask for: one template can't tell the patient which pack is meant, and any photo that gives a reading would replace it.
2. **Targets the clinician holds.** A target whose claim has an `open` or `withdrawn` request is never asked, because a withdrawn request is the clinician's decision not to ask. Each target is asked once per round. Just before asking, re-check that the target is still in `requestable(report)` and has no open request.
3. **`reply` gets a copy of the request** (`model_copy(deep=True)`), never the review's own object. Nothing `reply` does to it may reach the review, the report or the log.
4. **`max_rounds`** must be an `int`, not a `bool`, and at least 1. Anything else is a `ValueError`, raised before anything else, whatever the report holds.
5. **`add_photo` raises `PhotoAlreadyGiven`** for a photo it already has. Define it in `anamnesis/review.py` as a `ValueError` subclass with the same message, "photo was already given". `follow_up` catches that class, not the message string.
6. **The brief refuses a log that isn't its review's.** That means:
   - a `request_id` that appears twice in the log;
   - a step whose `target_id` or `kind` differs from its request's;
   - an `answered` step whose request isn't `answered`;
   - a `no_reply` or `duplicate` step whose request is `answered`.

   The line counts the log's steps, not the review's requests.
7. **A failed channel:** `reply` reports one by returning `None`, and anything it raises propagates. Don't catch it.

## Also from the review: no contract test pins these, so do them anyway
8. **`follow_up` is 54 lines,** with three near-identical log blocks. Set the outcome in each branch (`try`/`except`/`else`, appending the photo to the image list in the `else`), and write the log step once.
9. **The prepared-media check exists three times** (`brief.py`, `add_photo` and `follow_up`). Share one small helper.
10. **Your unit tests** in `tests/unit/test_b31_extra.py`:
    - drop the checks that repeat the contract;
    - add a test that a refusal other than a repeated photo propagates (for instance, a `reply` that returns a malformed photo);
    - make sure each test fails if the behaviour it names is removed. One of them still passed with the round's `break` removed.

## Hard rules
1. **Locked files:** never create, modify or delete anything under `tests/contract/`, any `conftest.py`, `pyproject.toml` or `uv.lock`. Add no dependency.
2. **Off limits:** don't edit `SPEC.md`, `docs/`, `evidence/`, `briefs/`, `NOTICE`, `finetune/` or any script. Don't open anything under `evidence/` or `finetune/data*`.
3. **Behaviour that stays:** every earlier contract, and every existing function in `review.py` apart from the new error class.
4. **No outside contact:** no network, no API keys, no `modal` commands, no git commits.
5. **Tools:** run them as `.venv/bin/ruff` and `.venv/bin/python -m pytest`. One test needs a local network socket that your sandbox forbids; if it is the only failure, say so and close your goal.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass from the repo root, and `git status --porcelain tests/contract` prints nothing.

Reply with a short report: what you changed for each numbered item, anything that looked wrong, and the final test count.
