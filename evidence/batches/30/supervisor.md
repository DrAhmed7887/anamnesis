# Batch 30: the Opus supervisor

## Round 1 review (31 Oct): SUPERVISOR: CHANGES
1. **HIGH, a false `match`** (`reconcile.py:269`): `_side_salts` still read `inn` whole, so it found no salt in a combined one, while `_identity` accepted each part. With the contract's fakes, before → after: claim inn "amoxicillin sodium" against pack inn "amoxicillin trihydrate/potassium clavulanate": `insufficient_information` → `match` (the one-part "amoxicillin trihydrate" gives `formulation_mismatch`); claim inn "amoxicillin sodium/clavulanic acid" against a pack strength "amoxicillin trihydrate": `insufficient_information` → `match`; pack inn "amoxicillin trihydrate/amoxicillin sodium/clavulanic acid" (two salts): `insufficient_information` → `match`. Fix: one (ingredient, salt) pair per part; checked as a scratch patch: `formulation_mismatch`, `formulation_mismatch`, `insufficient_information`, U2 still `match`, 2,730 tests pass. The same blind spot exists at HEAD in `agent/loop.py`'s second-read salts.
2. **MEDIUM, safe direction:** `(?<!\w)و(?!\w)` treats Arabic diacritics as non-word characters, so a diacritised word containing «و» splits; with a strength it becomes a conflict, never a `match`.
3. **LOW, a slowdown:** the `\s*` around each separator backtracks quadratically on runs of spaces (10k spaces 1.7 s, 30k 14.4 s), on every claim × pack call.
4. **INFO, safe:** "bisoprolol, 5 mg", "2,4-dichlorobenzyl alcohol" and "sennosides A and B" now conflict where HEAD didn't.
5. **OK:** scope; one-part `inn`s give the same identity, salts, `_pair_score` and findings as HEAD across 4,536 combinations; no crashes; it also closes a HEAD false `match` (a Panadol claim against pack inn "paracetamol/caffeine" beside a paracetamol-only strength).

**The CEO's effect:** all taken into round 2 with the fresh Muse audit's matching findings: salts from each part (and in the second read); a spaced «و» only (which also keeps «وارفارين» whole); a comma that isn't between two digits; no `\s*`; a stray separator's single part resolved. A CEO reference build passes all contract tests, and re-reconciling the 132 saved live reports still changes only today's three U2 runs, to `match`.

## Round 2 re-check (31 Oct): SUPERVISOR: CHANGES
1. **HIGH, narrow, a new false `match`** (`reconcile.py:57`, `:68`, through the catalogue fallback in `_resolve_inn`):
   - **The case:** a Triveram pack, `inn` "atorvastatin/amlodipine with perindopril", with an atorvastatin 20 mg + amlodipine 5 mg strength and the label "Triveram 20 mg/10 mg/5 mg", against a "Caduet 20/5" claim with the same strength.
   - **Before → after:** main gave `insufficient_information`, the build gives `match`. "… y perindopril" and "…\tو\tperindopril" do the same.
   - **The cause:** the part "amlodipine with perindopril" resolved as amlodipine, through the catalogue's whole-word match.
   - **The fuzz:** 10 of 5,000 targeted inputs were this class.
   - **The proposed fix** (a scratch prototype): a part of a combined `inn` resolves through the catalogue only on a whole-part match.
2. **MEDIUM, a slowdown:** an `inn` of "a/" × 15,000 took 16.9 s against main's 0.09 s, and 2,000 parts with 5 claims took 6.8 s.
3. **LOW, fail-open joiners, as on main:** "paracetamol\tو\tcaffeine" beside a paracetamol-only strength, against a Panadol 500 claim, gives `match` on both main and the build. "y", "plus" and an attached «و» do the same.
4. **INFO:**
   - some names now conflict where main didn't, all in the safe direction ("D,L-methionine", "sennosides A and B", "paracetamol 120 mg/5 ml");
   - "amoxicillin/" followed by an amoxicillin-only second reading is accepted, as the SPEC intends;
   - a first reading with `inn` "/" keeps the first reading.
5. **Verified:**
   - round 1's probes now give `formulation_mismatch` or `insufficient_information`;
   - 30,000 spaces take 0.01 s;
   - three false matches main makes are closed;
   - 12,960 comparisons with no separator are identical to main, including the second read;
   - no crash on odd Unicode.

**The CEO's effect:** all taken into round 3.
- **Findings 1 and 3, one rule for every `inn` string, not only parts:** a catalogue name counts only when it covers all of the string.
- **The cost of that rule, measured first:** re-reconciling the 132 saved live reports gives the same seven changes, and no saved one-part `inn` resolves differently. With the rule patched in, all 2,742 tests pass, and the four failing probes give `insufficient_information` while U2 and "atorvastatin/Norvasc" still `match`.
- **Finding 2:** an `inn` of more than eight parts is read whole.
- **The «و» regex:** it stays as Muse built it. With the rule, an unsplit «و» between tabs fails safe.
- **The reference build** passes the 31 contract tests and the full suite (2,752), with the same seven changes on the saved reports.

## Round 3 re-check (31 Oct): SUPERVISOR: APPROVE
- **HIGH and MEDIUM:** none. All three round 2 findings are closed.
- **LOW, safe direction:** a one-part `inn` with words beyond one catalogue name no longer resolves. "amlodipine (as besilate)", the Spanish salt forms the alias table lacks ("bisoprolol fumarato", "amlodipino besilato", "metoprolol succinato", "atorvastatina cálcica"), "Atorvastatin-Calcium-Trihydrat", "Paracetamol 500 mg", "Beloc-Zok mite", "Concor COR" and «كونكور 5», each beside its own strength and a matching claim, went from `match` (main, round 2) to `insufficient_information`. None is in the 132 saved reports. The proposed follow-up: add those forms to the alias table.
- **LOW:** a claim with no strength and such an `inn` ("Panadol", inn "Paracetamol 500 mg", intake 500 mg) becomes an unknown name. It overlaps no pack, so both the claim and the Panadol pack give `missing_modality`, where main gave `match`. Main already does this for any claim `inn` that conflicts.
- **Verified:**
  - the three Triveram forms give `insufficient_information`;
  - «و» between tabs or no-break spaces, an attached «و», "y", "plus", "with", "und" and "،" beside a paracetamol-only strength all give `insufficient_information`, where main gave `match`;
  - "a/" × 15,000 takes 0.10 s, and 2,000 parts with 5 claims take 0.11 s;
  - brands with Arabic clitics, spelling variants, salts, aliases and accented names give the same findings as main;
  - over 2,430 extra-word combinations, nothing moves into `match`;
  - 12,960 comparisons with no separator differ from main only on the three extra-word `inn`s;
  - the second-read scenarios are unchanged;
  - no crash, on `inn`s up to 140k characters.

**The CEO's effect:** merged. Both LOWs are in the SPEC as a known limit, in the safe direction. The alias forms are a follow-up, not tonight: adding them changes the PubChem snapshot and its pinned claim of 35 of 52.
