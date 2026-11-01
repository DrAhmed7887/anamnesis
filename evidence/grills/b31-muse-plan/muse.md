muse: workspace root: <repo>/.muse/worktrees/20261101-6036 (cwd default)
muse: warning: rules file at <repo>/CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
1. **The feature:** Ship the CEO's `follow_up` loop plus one bounded model choice: code opens each request, sends only the fixed template text, and processes replies via `add_photo`, while a model picks only *which requestable target goes next* (or STOP) from the fixed set `requestable(report)` returns (`anamnesis/review.py:34`, `anamnesis/schema/templates.py:128`). Code validates the pick, enforces the round limit and budget, and the result stays a draft until `approve` (`anamnesis/review.py:168`, `SPEC.md:363`). It scores autonomy (the model sequences a multi-step patient follow-up instead of the fixed intake order in `SPEC.md:349`), effectiveness (every round re-runs the same read/reconcile path, `anamnesis/review.py:125`), and usefulness (clinician gets a complete draft rather than one-photo-at-a-time triage, `anamnesis/review.py:30`).

2. **The design:** all new code in `anamnesis/review.py` after `approve` (`anamnesis/review.py:168`); no new model id, reusing the existing reader/extractor model id (`SPEC.md:433`).
- `choose_next(candidates: list[tuple[RequestKind,str]], log: list[dict], rounds_left: int) -> str | None`: model returns one `target_id` from `candidates` or STOP; code rejects anything else and falls back to `candidates[0]` (`anamnesis/review.py:34`).
- `follow_up(report, review, images, audio, *, get_reply, segmenter, reader, catalogue, max_rounds=3, **kw) -> tuple[Report, Review, list[dict]]`: per round calls `choose_next`, then `request_photo` + `request_message`, then `get_reply(request)` (photo bytes or `None`), then `add_photo` on a reply; stops when `requestable` is empty, `max_rounds` hit, or budget exhausted (`anamnesis/review.py:51`, `anamnesis/review.py:85`, `anamnesis/review.py:97`).
- Log entries `{round, request_id, target_id, outcome}` where outcome ∈ `answered|no_reply|duplicate|budget|invalid_pick`, appended by code, never model text (`anamnesis/review.py:160`).
- Brief afterwards shows the new photo(s), re-reconciled findings, appended timeline steps, and updated status/coverage lines from templates only (`SPEC.md:446`, `anamnesis/schema/templates.py:120`, `anamnesis/schema/templates.py:122`).

3. **Risks:**
1. Endless loop: cap `max_rounds` plus stop on empty `requestable`; test asserts return after cap with draft status (`anamnesis/review.py:34`).
2. Reply mutating old evidence: `add_photo` only appends observations and supersedes just the unreadable target; test asserts old claims/regions byte-identical (`anamnesis/review.py:132`).
3. Spend across rounds: each `add_photo` gets its own `IntakeSession(max_provider_calls)` under the shared dollar guard; test asserts calls ≤ rounds × per-photo budget (`anamnesis/review.py:116`, `SPEC.md:363`).
4. Re-requesting the fulfilled: `request_photo` raises on already-open target and `add_photo` raises on duplicate bytes; test asserts second identical reply raises, not re-bills (`anamnesis/review.py:59`, `anamnesis/review.py:114`).
5. Skipping approval: `approve` raises while any request is OPEN and on intake mismatch; test asserts `follow_up` output never `APPROVED` (`anamnesis/review.py:168`).
6. Model inventing text/target: `choose_next` output constrained to candidate ids and all patient text from templates; test asserts unknown id falls back and message equals a template (`anamnesis/review.py:85`, `anamnesis/schema/templates.py:128`).

4. **The contract:** offline fixture adapters, no network (`SPEC.md:442`).
- `test_follow_up_stops_when_nothing_requestable`: empty `requestable` returns inputs unchanged plus empty log (`anamnesis/review.py:34`).
- `test_follow_up_processes_one_reply`: one open target + one photo yields new observation and ANSWERED request (`anamnesis/review.py:97`).
- `test_follow_up_ignores_invalid_pick`: off-list model pick falls back to first candidate (`anamnesis/review.py:51`).
- `test_follow_up_respects_round_limit`: `max_rounds=1` leaves remaining targets unrequested (`anamnesis/review.py:34`).
- `test_follow_up_rejects_duplicate_photo`: resubmitted bytes raise `photo was already given` (`anamnesis/review.py:114`).
- `test_follow_up_never_approves`: result status is DRAFT or AWAITING, never APPROVED (`anamnesis/review.py:168`).
- `test_follow_up_messages_are_templates`: every sent string equals `REQUEST_*` (`anamnesis/schema/templates.py:128`).

5. **Open questions for the CEO.**
- `max_rounds` default: is 3 (one retry per target class) acceptable, or 1 to match tonight's single-photo behavior (`anamnesis/review.py:97`)?
- On `no_reply`, should the loop withdraw that request or leave it OPEN for the clinician (`anamnesis/review.py:69`)?
- Should `choose_next` see finding types/counts only, or also claim names, given the fixed prompt budget (`SPEC.md:438`)?
- Which existing model id serves `choose_next` (claim extractor vs label reader) so spend attribution stays clean (`SPEC.md:432`)?

