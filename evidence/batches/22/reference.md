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
