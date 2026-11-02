# Batch 24.2: the CEO's reference build, 30 Oct

- **Contract:** `test_b24_2_codes_conflict.py`, 5 tests.
  - On main, both at 03f500a and on this branch at 9f7e80e, 3 fail and 2 pass.
  - The 3 that fail are the contradictions: a claim's stated INN, a claim's strength, and a pack's reading that disagrees with its label.
  - The 2 that pass guard against over-fixing: an agreeing claim and an agreeing pack keep their codes.
- **Reference build:** a scratch clone of main outside the repo. `brief_html._codes_entry` shows no codes when the reconciler's identity check (`_claim_identity`, or `_pack_identity` with the pack's country) reports a conflict, through two public wrappers in `core/reconcile.py`. **2,416 passed**, ruff clean. No earlier test changed.
- **Left out:** resolving the codes' entry with the pack's country, the batch 24.1 supervisor's #3. It has no visible effect today, because entries with the same ingredient carry the same codes, and pinning it would need a scratch catalogue threaded through the whole intake. It is recorded for after the hackathon.

**One mutant per behaviour** (failures in `tests/contract`):

| Mutant | Failures |
|---|---|
| Codes shown despite a conflict | 3 |
| The claim side's conflict ignored | 2 |
| The pack side's conflict ignored | 1 |
| No codes at all | 5 |
