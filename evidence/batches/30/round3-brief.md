# Batch 30, round 3: a catalogue name counts only when it covers all of an `inn`

Round 2 passed the gate, and every round 1 finding is closed. The Opus supervisor's re-check found one new false `match` and a slowdown. SPEC §3's batch 30 bullet now settles both, and new contract tests pin them at the end of `tests/contract/test_b30_combined_inn.py` ("round 3"). The contract commit is the latest `test(contract): batch 30`.

## The findings
1. **A false `match` (high).** A Triveram pack (atorvastatin, perindopril and amlodipine) was read with `inn` "atorvastatin/amlodipine with perindopril" beside an atorvastatin 20 mg + amlodipine 5 mg strength, and it matched a "Caduet 20/5" claim.
   - **The cause:** the part "amlodipine with perindopril" resolved through the catalogue's whole-word match on "amlodipine", so perindopril vanished.
   - **The same cause elsewhere:**
     - "… y perindopril" and a «و» between tabs did the same;
     - a one-part `inn` does it too: "paracetamol plus caffeine" beside a paracetamol-only strength matched a Panadol claim.
2. **A slowdown (medium).** Every part that isn't a known moiety goes through the catalogue, at about 0.6 ms each, both for identity and for salts. An `inn` of "a/" repeated 15,000 times took 16.9 s, and 2,000 different parts took 6.8 s.

## Do
1. **`Catalogue.covers(text) -> bool`** (`anamnesis/core/catalogue.py`): true when one catalogue name matches all of `normalise(text)`, that is, when one of `_matches(text)` starts at 0 and ends at the normalised text's length.
2. **An `inn` string resolves through the catalogue only when it is covered** (`anamnesis/core/reconcile.py`). In `_identity` and `_side_salts`, resolve a one-part `inn`, and each part of a combined one, in this order:
   - a known moiety resolves as now;
   - otherwise, through the catalogue only when `catalogue.covers(part)` is true;
   - otherwise, as its own canonical name.

   Leave `_resolve_inn` as it is for strength and intake ingredients and for every other caller.
3. **More than eight parts:** when the split gives more than eight parts, `_split_inn_parts` returns the stripped `inn` whole, as one part.

Update your own unit tests wherever they pinned the old behaviour. Everything else in the hard rules of `briefs/30.md` still holds; `anamnesis/core/catalogue.py` may change for item 1.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass from the repo root, and `git status --porcelain tests/contract` prints nothing. Reply with a short report and the final test count.
