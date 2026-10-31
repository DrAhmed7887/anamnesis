# Batch 24.2: the supervisor's review

## Round 1: SUPERVISOR: APPROVE
**The verdict:** no codes line beside a contradiction as the SPEC defines it, none wrongly hidden, and nothing else changed. None of the three notes is a builder defect.
1. **Medium, a follow-up for the SPEC:** `_claim_identity` ignores `intake_amount`. "Concor" with an atorvastatin 20 mg intake and `inn` empty shows bisoprolol's codes. Fix in a later batch: pass `intake_amount.inn` as the stated INN when `inn` is empty.
2. **Info:** naming one ingredient of a combination hides the codes ("Panadol Extra" with paracetamol only). This matches the reconciler, and it errs on the safe side.
3. **Info:** Arabic ingredient names hide the codes, because there are no Arabic INN aliases. Main already failed to pair such a claim.

**Confirmed:**
- **Salts and aliases** keep their codes, and contradictions hide them.
- **Ambiguous names** show none.
- **A claim paired with a pack:** the claim side decides.
- **The reference line:** once per page whenever a codes line remains.
- **No other change:** 377 `reconcile_all` results and 83 briefs are byte-identical, and 80 probes differ only in codes lines.
- **Reuse:** two one-line wrappers over the reconciler's check.
- **Tests:** contract 5/5, failing 3/5 on main. Full suite 2,417, ruff clean.
