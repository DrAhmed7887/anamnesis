# Batch 22: reference build (CEO, before Muse runs)

- **Before the build:** the open-weight contract fails to import, since `anamnesis/providers/openweight.py` doesn't exist yet. The number-word contract has 9 cases failing and 14 pins passing.
- **Reference build:** a scratch copy with:
  - an `OpenWeightLabelReader` and `OpenWeightClient` (about 110 lines);
  - two `_PRICES` entries;
  - a one-word branch in `parse_amount_text`.
- **Result: 1,056 passed.**
- **Two contract fixes found by the reference build:**
  - The pre-call estimate prices by `body["model"]`, so the reader must estimate with its price key. Brief item 3 now says so.
  - Batch 16's contract pinned `"two"` as null. With the new rule it is 2, and it must still be stated; the CEO updated that case in this lock.

## Round 2 (28 Oct): the supervisor's findings 1–3, pinned in `tests/contract/test_b22_round2.py`
- **On Muse's round 1:** 31 of the 40 new tests fail, one per input the supervisor found. The 9 that pass are letter variants that must keep parsing («خمســة», «خمسه», «إثنين», «خمس», "FIVE") and the four finding-4 pins.
- **Reference build** (a scratch copy of round 1 plus the supervisor's fixes: the bare-word check before `normalise`, `-contributor` anywhere, and `self.client.provider` in the reader's three errors): **1115 passed**.
- **Mutants of the finding-4 pins**, each applied alone to the reference:
  - estimate priced as `muse-spark-1.3`: caught;
  - `with_one_retry(..., model_id=self.model)`: caught;
  - the 60 s timeout dropped: caught;
  - `_safe` removed from the parse-error path: survives. No parse message echoes the reply, so the pin holds either way; `_safe` stays as defence in depth.
