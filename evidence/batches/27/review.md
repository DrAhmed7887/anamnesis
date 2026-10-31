# Batch 27 review: relation checks on claim amounts (SPEC §2)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 3 rounds, planned first by a read-only Muse session and audited by a fresh one

**What the batch changes:** after the value check in `parse_claims_json`, six word rules decide what each number in a cited turn was said about, and an amount whose every mention is excluded is dropped, taking the other amount with it:
1. **negation** ("ten, not five"), with words of knowing exempt ("not sure, five");
2. **another unit** ("five micrograms" doesn't ground 5 mg), for every claim, in or out of the catalogue;
3. **a count** ("two Panadol tablets" isn't 2 mg);
4. **another medicine's amount** (the walk-back to the nearest name, and "of"-forms; an "of" naming the claim wins);
5. **a past amount** for a claim that isn't discontinued ("used to take ten, now five");
6. **a split daily total** ("ten milligrams a day, five in the morning and five at night"; also "ten a day").

New: `anamnesis/providers/relations.py` and the hook in `anamnesis/providers/claims.py`. Labels, `regimen`, `stated_amounts` and the reconciler are unchanged.

**Why:** GPT-6 Astra's win grill said the provenance checks "prove words occurred, not that the finding follows". The relation audit (`evidence/audits/relation-provenance/`) showed that seven of ten invented traps would pass a wrong reply, three as false `match`es. Ahmed reversed the "no code change before the freeze" decision (31 Oct, 10:45).

**Who did what:**
- **The CEO prototyped the rules first,** outside the product, and measured them on the committed fine-tune replies and the saved live reports before writing the SPEC and the contract.
- **Muse planned first** (`evidence/grills/b27-muse-plan/`): "Ship with tightened wording". Five of its points tightened the SPEC, among them: amount labels are never own names.
- **Muse built it in three rounds:**
  - **round 1** passed the gate and flagged three conflicts. Two lenient exceptions were accepted into the SPEC (a past marker stops at another medicine's name; a daily-total splitter is blocked in a clause naming another medicine). The third, rule 2 only for catalogue medicines, was reversed: a batch 24 row had "mg" by default where a gram was said; the CEO corrected it and pinned rule 2 outside the catalogue;
  - **round 2** applied rule 2 to every claim;
  - **round 3** took the Opus supervisor's five findings (`supervisor.md`).
- **A fresh Muse audit** of round 2 (`evidence/grills/b27-muse-audit/`): "Build matches SPEC and contract; no fail-open crash". The SPEC followed the build on its four small points.
- **The Opus supervisor** reviewed round 2 (CHANGES: five findings, all taken) and round 3 (below).

**Measured on the final build** (the CEO's scripts; the pre-registered post-merge checks are in `check-plan.md`):
- the relation audit's ten traps: all fail safe, and every right reply keeps the careful listener's findings;
- the committed fine-tune replies (Spark 1.3, base Glimmer, r1 and r2 on every test split, 1,452 in all): 0 lose a fully-right score, 0 harmful claims added;
- the 97 saved live reports (120 claims), re-parsed: 0 change.

**The gate:** pass, 2,610 tests, ruff clean, contract untouched since the latest `test(contract): batch 27` (`gate.json`).

**Known limits, in the SPEC:** word rules, not understanding. A medicine that is neither in the catalogue nor claimed in the reply isn't seen as another medicine, and words outside the lists aren't seen. A bare number with no unit or count word still grounds any unit.

**Cost:** Muse $7.29 in all: plan $0.20, round 1 $4.86, round 2 $0.42, round 3 $1.47, audit $0.35. The rounds are in `evidence/spend/muse_ledger.jsonl`; the grills are in neither ledger.

**The Opus supervisor's round 3 re-check:** APPROVE (`supervisor.md`): its earlier failing probes all pass, 32,000 fuzzed replies give 0 crashes and 0 amounts kept that the value check would drop.

**Found, not fixed here (batch 27.1, after batch 28; both fail safe):** a duration ("for five years") can split a daily total, and German "weiß nicht" before a number still negates it.

Verdict: PASS
