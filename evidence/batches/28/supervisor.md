# Batch 28: the Opus supervisor

## Round 1 review (31 Oct): SUPERVISOR: CHANGES
The builder's code does what SPEC §4 step 5b said; the problem was in the step itself.

1. **HIGH, SPEC-level, a false match:** release, salt and `per` never counted as a disagreement (`loop.py:129-133, 166-169`). A partial step-5 reading of bisoprolol 5 mg modified release, then a readable bisoprolol 5 mg immediate release: the second won and the finding was `match`, where without the second reader it was `unreadable_source` and requestable. Metoprolol succinate read as tartrate (47.5 mg) also won, and so did per tablet read as per ml (`insufficient_information`).
2. **MEDIUM, SPEC-level:** a readable second reading with no `inn` and no `strength` skipped the ingredient check even when its label named another product (`loop.py:120-126, 162-165`): "Panadol 500 mg / Paracetamol" replaced a step-5 bisoprolol reading, and its `unreadable` request was gone. Live this can happen, because `parse_label_json` drops a strength whose amount isn't printed.
3. **INFO:** a second reader that raises a non-`ProviderError` exception crashes `run_intake`, as the first reader's zoom already does; `OpenWeightLabelReader` turns its failures into `ProviderError`. Not new; no action.

**Checked and fine:** scope; with no second reader, 1,500 random intakes plus `add_photo` gave byte-identical outputs (3,623 sha256 matches); every failure path keeps the step-5 reading and its re-photo request; crop provenance on a rotated JPEG; the budget worst case (26 calls) fits; one shared `SessionGuard`; 3,000 fuzzed intakes with a second reader, no crash, at most 3 reads per region; the live script's guards refuse a symlink into `real/` and a `..` path before any key; Muse's tests catch 12 deliberate code breaks.

**The CEO's effect:** findings 1 and 2 taken into round 2 with the fresh Muse audit's matching findings: the second reading must keep everything the step-5 reading had (ingredients, strength with its `per`) and agree on release and salt where both give them. SPEC §4 step 5b and the contract changed (the latest `test(contract): batch 28`); a CEO reference build passes all 31 contract tests.

## Round 2 re-check (31 Oct): SUPERVISOR: CHANGES
1. **HIGH: a false `match` when a known release becomes `unknown`** (`loop.py:193`). A step-5 reading "Concor 5 retard" (bisoprolol 5 mg, modified) replaced by a readable "Concor 5 mg / Bisoprolol fumarate" with release `unknown`: the second stood, the catalogue filled in Concor as immediate, and the finding was `match`. A reader told to "read only what is printed" that misses "retard" says `unknown` more likely than `immediate`, so this is the likelier route to round 1's false match. Salt does the same (metoprolol succinate read again with no salt). The SPEC's release and salt rules applied only "where both give" one; Muse followed them.
2. **LOW:** one salt per ingredient: `_salts` keeps the strength's salt and ignores a different one in `inn` (8 of 20,000 random, self-contradictory pairs). Fix: sets.
3. **LOW:** nothing tests the salt in `inn`: deleting that branch keeps all 40 batch 28 tests passing.

**Checked and fine:** round 1's HIGH and MEDIUM cases now conflict and stay requestable; an `unknown` step-5 release can still be completed; without a second reader, 1,500 random intakes are byte-identical (3,623 sha256 matches); with one, 3,000 random intakes, no crash; round 2 changed only `loop.py` and Muse's tests.

**The CEO's effect:** all three taken into round 3: a release or salt the step-5 reading gave must be repeated (a missing one is a conflict), salts are compared as sets from both sources, and the salt in `inn` is pinned by a contract case. A CEO reference build passes all 35 contract tests.

## Round 3 re-check (31 Oct): SUPERVISOR: APPROVE
- **"Concor 5 retard"** (modified, then a second reading with release `unknown`): conflict; the pack stays partial as `unreadable_source`, requestable, and there is no `match`. Modified→immediate, per tablet→ml, succinate→tartrate, succinate→no salt (through the strength and through `inn`), and bisoprolol→a "Panadol" text with no ingredients all conflict and stay requestable.
- **Completion works:** unknown→modified stands (`formulation_mismatch`); no salt→succinate stands; a step-5 reading that names nothing, then Concor 5, stands (`match`).
- **Spec check:** the round 3 text of 5b, coded separately from Muse's code, agreed on all 20,000 random reading pairs (round 2: 8 disagreements).
- **Without a second reader:** 1,500 random intakes through d25d6f8 and round 3, identical output (3,623 results). **With one:** 3,000 intakes, no crash; budget, crop and `add_photo` probes unchanged. Round 3 changed only `loop.py`.
1. **LOW:** no test checked that salts are compared as sets from both sources (the code is right). **The CEO's effect:** pinned by `test_salts_are_compared_from_both_sources` in the latest contract commit; the build passes it.
2. **INFO:** exact salt matching makes "fumarate" against "hemifumarate" a conflict, though they are usually the same 2:1 bisoprolol salt named two ways. It errs toward safety and only costs reads; an `INN_ALIASES` equivalence could fix it after the hackathon.
