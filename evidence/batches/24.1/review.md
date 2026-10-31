# Batch 24.1 review: catalogue codes in the catalogue and the brief, and three new entries (SPEC §3, §7)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 1 round, goal pinned with its goal tool

**What the batch adds:**
- **Codes in the catalogue:** `CatalogueEntry` gains `atc` and `rxcui`, filled for the nine existing entries from AEMPS CIMA (ATC) and NLM RxNav (RxCUI), read 29 Oct.
- **Three new entries:** Emconcor (ES), Sortis (DE) and Nolotil (ES), each synthetic, with release, splittability and countries set.
- **Codes in the brief:** a finding box whose claim (or, with no claim, whose pack) resolves to a coded entry shows one escaped line, with no links: "Catalogue codes: ATC … · RxNorm …".
- **The reference line:** shown once per page when any codes line appears. It names the WHO Collaborating Centre and points to `NOTICE`.
- **`NOTICE`:** the terms of WHO, NLM and AEMPS.
- **No SNOMED CT in the product.** Ahmed decides on Tue whether the ids stay in the public copy of `evidence/data/drugs_v2.json`.

**Who did what:**
- **Claude Code (Opus 5.5), as CEO,** wrote the SPEC lines, the brief, the contract, `NOTICE` and the fine-tune pin (50eb972).
  - **The reference build** was proved twice: first on batch 24's reference, then on main after batch 24 merged (`reference.md`). On main it gave 2,408 passed, with one mutant per behaviour, all eight caught.
  - **Three problems it found in the CEO's own work,** all fixed before the build:
    - the fine-tune read every catalogue entry, so new entries would have changed r1's data (now pinned);
    - a test fixture needed a second reading;
    - the contract file's import order would have failed the gate.
- **Muse wrote all the code:** `core/catalogue.py`, `core/catalogue.yaml`, `brief.py`, `brief_html.py` and `schema/templates.py`, and its unit tests in `tests/unit/test_b24_1_extra.py`.
- **The held-out guard:** the brief gives every code in its table, so Muse needed nothing under `evidence/`. Muse's export shows no read under `evidence/` or the fine-tune data (`goal.md`).
- **A separate Opus supervisor** (a Claude subagent of the engine session) reviewed the build (`supervisor.md`): **APPROVE**, with no finding at a CHANGES level.
  - **Codes:** all 12 entries match the table, and no existing entry changed in any field.
  - **Escaping:** hostile names and hostile code values came out escaped, with no links.
  - **The reference line:** exactly once whenever a codes line shows, and never otherwise.
  - **No regressions:**
    - 65 suite briefs and 31 of the supervisor's own render byte for byte as before, once the new lines are stripped;
    - the suite's 230 reconciliations give identical findings;
    - 2,230 existing names in 6 countries resolve as before.
  - **Fine-tune data:** r1's and r2's data regenerate byte for byte.

**The gate:** pass, 2,411 tests, ruff clean, contract untouched (`gate.json`). Inside its sandbox, Muse's goal ended "blocked" on the one socket test the sandbox forbids, as the brief allows.

**Checks beyond the gate:**
- **Outside the gate's lock:** `NOTICE`, `finetune/`, `SPEC.md` and `briefs/` are unchanged since the contract commit.
- **The fine-tune data tests:** all 27 pass on the build (`test_finetune_data.py`, `test_finetune_v2.py`), so r1's and r2's data still regenerate byte for byte.

**Cost:** Muse $2.07 (`evidence/spend/muse_ledger.jsonl`).

**Found, not fixed here (from the supervisor):**
- **A changed finding, by design:** claim "metamizole 575 mg" was `unresolved_name` and is now `missing_modality` with Nolotil's codes. That is the SPEC's ingredient rule.
- **For Ahmed, after the freeze:** a claim whose name is one brand ("Concor") and whose said INN is another ingredient ("atorvastatin") shows the brand's codes next to that INN. This follows the SPEC as written. Whether to hide codes when name and ingredient conflict is his call.
- **The pack side resolves without the pack's country,** while reconciliation uses it. It has no visible effect today, because entries with the same ingredient carry the same codes.
- **A nit:** the codes entry is worked out twice, in `brief.py` and `brief_html.py`. The results agree.

Verdict: PASS
