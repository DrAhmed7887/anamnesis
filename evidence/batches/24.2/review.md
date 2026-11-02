# Batch 24.2 review: no catalogue codes beside a side that contradicts its own name (SPEC §7)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 1 round, goal pinned with its goal tool and closed complete

**What the batch changes:** a finding box shows its catalogue codes only when its side agrees with its own name.
- **The check:** the reconciler's own identity check, `_claim_identity` for a claim and `_pack_identity` (with the pack's country) for a pack-only finding. When it reports a conflict, the box shows no codes line.
- **Why:** this is decision 4 of 30 Oct (`evidence/decisions.md`). The batch 24.1 supervisor found "Concor" said with "atorvastatin" showing bisoprolol's codes beside the patient's atorvastatin. A code the patient's own words dispute is worse than no code.
- **Freeze:** it is a provenance fix, which the freeze allows.

**Who did what:**
- **Claude Code (Opus 5.5), as CEO,** wrote the SPEC line, the brief and the contract (2f2694c).
  - **The reference build** (`reference.md`) gave 2,416 passed, with one mutant per behaviour, all four caught.
  - **The contract:** on main, 3 of the 5 contract tests fail (the contradictions) and 2 pass (the guards against over-fixing).
- **Muse wrote all the code:**
  - two public wrappers in `core/reconcile.py`, `claim_identity_conflict` and `pack_identity_conflict`, which return the existing conflict flag;
  - the early returns in `brief_html._codes_entry`;
  - its unit tests in `tests/unit/test_b24_2_extra.py`, including the Panadol Extra case.
- **The held-out guard:** Muse's export shows no read under `evidence/` or the fine-tune data (`goal.md`).
- **A separate Opus supervisor** (a Claude subagent of the engine session) reviewed the build (`supervisor.md`): **APPROVE**.
  - **Codes hidden correctly:** no codes line beside a contradiction as the SPEC defines it, and none wrongly hidden.
  - **Salts and aliases keep their codes:** fumarate, "(as …)", German and Latin forms, acetaminophen, بنادول, كونكور.
  - **Nothing else changed:** 377 `reconcile_all` results and 83 existing briefs are byte-identical apart from the codes lines.
  - **The reconciler's behaviour is unchanged:** only two one-line wrappers were added, and nothing in it calls them.

**The gate:** pass, 2,417 tests, ruff clean, contract untouched (`gate.json`).

**Checks beyond the gate:**
- **Outside the gate's lock:** `NOTICE`, `finetune/`, `SPEC.md` and `briefs/` are unchanged since the contract commit.
- **The fine-tune data tests:** all 27 pass.

**Found, not fixed here (recorded for after the hackathon):**
- **The intake amount's ingredient isn't checked (the supervisor's #1, medium).** "Concor" with an atorvastatin 20 mg intake, but `inn` left empty, still shows bisoprolol's codes.
  - The SPEC's check covers the stated INN and the strength only, and the brief forbade a second comparison.
  - It also needs the model to leave `inn` empty while the patient names the ingredient, which its prompt tells it not to do.
  - The fix, for a later batch: when `inn` is empty, pass `intake_amount.inn` to the identity check as the stated INN.
- **Two safe-side cases (info), where a code is hidden that a reader might expect:**
  - naming one ingredient of a combination ("Panadol Extra" with paracetamol alone);
  - an Arabic ingredient name, because `INN_ALIASES` has no Arabic names. Main already failed to pair such a claim with its pack.
- **The pack's country:** the codes' entry is still resolved without it (the batch 24.1 supervisor's #3). It has no visible effect today.

**Cost:** Muse $0.77 (`evidence/spend/muse_ledger.jsonl`).

Verdict: PASS
