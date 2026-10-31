# Batch 30 review: an `inn` string that names several ingredients is read as that set (SPEC §3)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 3 rounds, audited by a fresh Muse session; no read-only plan (one reconciler rule, already tried on a CEO reference build)

**What the batch changes:**
- **The reconciler** (`anamnesis/core/reconcile.py`, `_identity`): an `inn` string joined by "/", "+", "&", a comma that isn't between two digits, a whole-word "and" or a «و» with a plain space on each side names the set of its parts, each resolved as any `inn`. With a strength, a set of two or more must equal the strength's ingredients; without one, it is the side's identity. A stray separator ("amoxicillin/") leaves its one part, and an `inn` of more than eight parts is read whole.
- **A catalogue name counts only when it covers all of an `inn`:** a one-part `inn`, or one part of a combined one, resolves through the catalogue only when one catalogue name matches all of it (`Catalogue.covers`); otherwise it is its own name. Strength and intake ingredients resolve as before.
- **Salts** (`_side_salts`): each part's salt counts in the salt rules.
- **The second read** (`anamnesis/agent/loop.py`, §4 step 5b) reads its named ingredients and salts from the parts too.

**Why:** after batch 29 fixed U2's claim, all three live runs still gave `insufficient_information`: the label reader wrote the Augmentin pack's `inn` as "amoxicillin/clavulanic acid" beside the right 875/125 strength, and the reconciler counted that one unknown string as an extraction conflict. Part of "Fix U2 first".

**Who did what:**
- **The CEO** wrote the SPEC line, the contract and a reference build for each round, and re-reconciled all 132 saved live reports with it.
- **Muse built it in three rounds:**
  - **round 1** ($0.75) did what the first SPEC line said, with 13 unit tests. It matched "and" as a whole word rather than "spaced", so "X, and Y" splits too; the SPEC followed the build;
  - **round 2** ($0.65) took the findings below. It splits on «و» only with one plain space on each side, where the reference allowed any whitespace: a «و» set off by tabs or no-break spaces stays unsplit, and the pack reads as a conflict, never a `match`. The SPEC follows the build;
  - **round 3** ($0.58) took the supervisor's re-check of round 2. It behaves exactly as the reference build: a Triveram pack read short ("atorvastatin/amlodipine with perindopril" beside two of its three amounts) no longer matches a Caduet claim, nor "paracetamol plus caffeine" beside a paracetamol-only strength a Panadol claim (a false `match` already on `main`); 2,000 parts take 0.04 s, not 6.8 s.
- **The fresh Muse audit** of round 1 (`evidence/grills/b30-muse-audit/`) and **the Opus supervisor** (`supervisor.md`) both found that a salt inside a combined `inn` was lost: "amoxicillin sodium" against a pack's "amoxicillin trihydrate/potassium clavulanate" became a false `match`. Round 2 reads one salt per part, in the reconciler and in the second read. It also splits more safely: no comma between digits ("2,4-dichlorobenzyl alcohol"), no attached «و» («وارفارين»), and no `\s*` around separators, which took 14 s on 30,000 spaces.

**Measured on round 3:** re-reconciling the 132 saved live reports gives the same seven changes as the reference build: today's three U2 runs become `match`, and four older reports already differ on `main`, from reconciler fixes since 28–29 Oct (`rereconcile.py`).

**The gate:** pass, 2,757 tests, ruff clean, contract untouched since the latest `test(contract): batch 30` (`gate.json`).

**Cost:** Muse $2.24 in all: round 1 $0.75, round 2 $0.65, round 3 $0.58, audit $0.25. The rounds are in `evidence/spend/muse_ledger.jsonl`; the audit is in neither ledger, and the spend gate adds it.

**The live check** (`live-plan.md`, written before the build): U2 three times after the merge.

**The Opus supervisor's round 3 re-check:** APPROVE (`supervisor.md`). Nothing moves into `match` over 2,430 targeted combinations, and there is no crash.

**Found, not fixed here (safe direction, in the SPEC):** an `inn` that carries a salt or strength the alias table doesn't know ("bisoprolol fumarato", "Paracetamol 500 mg") now abstains where main matched. On a claim with no strength, it can leave the claim unpaired. None of the 132 saved reports has one; the fix is adding those forms to the alias table.

Verdict: PASS
