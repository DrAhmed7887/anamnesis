# Batch 26.1 supervisor (independent Opus subagent)

## Round 1

SUPERVISOR: APPROVE

`/tmp/b261_sup/probe.py` and `/tmp/b261_sup/mutate.sh` reproduce findings 1, 2 and 4.

1. **LOW: validation compares by equality, not by type** (`anamnesis/providers/openweight.py:65`). Every realistic wrong value is refused. I tried "", case and whitespace variants, "max", "minimal", "none", Unicode look-alikes, 0, 1, True, bytes, list and dict. It does accept `UserString("low")` and `mock.ANY`. Both then fail JSON encoding with a TypeError, so no request goes out and no ledger line is written. Only a str subclass whose `__eq__` lies gets "max" onto the wire. This doesn't justify CHANGES: no caller can produce these values, and the attribute can be reassigned after construction anyway. Optional fix: `type(reasoning_effort) is not str or reasoning_effort not in (...)`.
2. **None: the request** (`openweight.py:102-105`). Compared with HEAD's module, None gives identical bodies, outcomes and ledger rows. That holds for both providers, json_mode on and off, cropped and not, and for a normal read, a retry and a length stop. "low" adds only its field, and the estimate ignores that field (`meta.py:74-91`). `scripts/reader_eval.py:86-87` passes no effort, so batch 22's comparison request is unchanged. Fix: none.
3. **None: scope.** The code changes are `openweight.py:62-72,102-103`, `scripts/intake_live.py:10-11,132-134` and the new test file. `PRESETS`, the 60 s timeout, `MetaLabelReader`, `glimmer.py`, `modal_serve.py` and the Glimmer guards are untouched. The fourth file in gate.json's diff count is the Muse spend line that the batch script adds (`scripts/batch.sh:65`), not Muse's code. Fix: commit it as usual.
4. **None: Muse's tests catch real bugs** (`tests/unit/test_b261_extra.py:55,61,70`). On a /tmp copy, I made two breaking edits: dropping the effort under json_mode, and stripping whitespace before the check. The contract tests still pass on both; Muse's tests fail on both. The batch only adds a test file, and nothing is skipped or weakened. Fix: none.
5. **INFO: the run log can't tell efforts apart** (`scripts/intake_live.py:148`). runs.jsonl records `reader: fireworks` whatever the effort was. Fix: note the effort in the decision log for the next live run.

Tests: the 301 related tests pass offline. The gate passed (2519 tests, ruff clean, no locked file touched). I wrote only under /tmp. Something else wrote to `evidence/grills/b261-muse-audit/` during my review.

**CEO's decisions:**
- **Finding 1 is accepted as is.** No caller can produce such a value.
- **Finding 5 is handled by the plan.** The pre-registered fourth column (`evidence/batches/26/intake-plan.md`) names its effort, and its tag `b261-open` marks it.
- **The writes it saw** were the CEO's: the audit's output and its triage.
