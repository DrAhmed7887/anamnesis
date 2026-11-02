# Batch 32: the Opus supervisor

## Round 1 review (1 Nov): SUPERVISOR: CHANGES
Scope matches `briefs/32.md`: Muse changed only `Catalogue._matches` (`catalogue.py:124-129`) and added `tests/unit/test_b32_extra.py`. The locked files are untouched, and nothing else outside `anamnesis/` and `tests/unit/` is Muse's (the ledger row and `evidence/batches/32/` come from the harness). Ruff is clean and all 2,863 tests pass here, the socket test included. Every input below was run offline against the real catalogue, comparing the contract commit's matching (3878912) with Muse's.

1. **Major, a SPEC decision: a folded salt name drops its salt** (`catalogue.py:124-128`, read by `reconcile.py:295`). `_resolve_inn_part` now reads an `inn` through the fold, but `salt_of` still reads its salt only as written. The salt is lost, so a side that used to abstain can now `match`. Inputs run, with claim and pack at equal strength:
   - `inn` "tomometoprolol succinate" against Metoprolol tartrate 100 mg: `insufficient_information` → `match`. Spelled "metoprolol succinate", it gives `formulation_mismatch`.
   - Name and `inn` "amlodipine vesilate" against amlodipine maleate 5 mg: `insufficient_information` → `match`.
   - `inn` "visoprolol hemifumarate" against bisoprolol fumarate, and "atorbastatin calcium" against calcium trihydrate: the same.

   When `name_text` also carries the salt, the loose-salt rule catches "Tomometoprolol succinate" (`formulation_mismatch`). It can't catch "vesilate", which isn't a salt word. Exposure is low, because the alias table holds no Spanish salt. But this reopens batch 30's rule that a spelling the catalogue doesn't know abstains. Fix: match an alias that carries a salt (a name in `INN_ALIASES` with a salt) as written, with no `b`/`v` fold and no form of *tomar*, and say so in SPEC. Tried in memory: the four inputs abstain again, the hero's eight runs still change as intended, and all 45 contract tests and every other test pass. Three of Muse's nine unit tests assert the fold on salt aliases and must leave them out.
2. **Minor, existing and now one step wider: a strength or intake label loses its salt word** (`reconcile.py:81-90, 292`). Labels resolve without `covers`. So "tomo metoprolol succinate" as a strength label against a tartrate pack is already a `match` on `main`. Batch 32 adds the joined "tomometoprolol succinate" (`missing_modality` → `match`). The fix in #1 doesn't reach this path. Fix: in a reconciler batch, read curated salt words in labels the way `_loose_salts` reads names, or state this as a known limit.
3. **Minor, test gaps.** Three over-matching builds pass all 54 batch-32 tests:
   - each `b`/`v` also matches `p` and `w`: "pisoprolol" → Concor, "Peloc-Zok" → Beloc-Zok, "Norpasc" → Norvasc;
   - `p` folds as well;
   - three more verb forms are accepted ("tomó", "tome", "tomaba").

   Fix: pin "pisoprolol", "wisoprolol" and "tomóbisoprolol" as `None`.
4. **Minor, style:** the five forms are an inline pattern. A named constant beside `ARABIC_CLITICS` that cites SPEC §3 would match the rest of the module.

**What holds** (old → new, all as the SPEC says):
- **Real words and drug names:** nothing newly matches a catalogue name, out of 729 RxNorm and CIMA names (`evidence/data/`) and 313,489 entries of `/usr/share/dict` (words, web2a, propernames). The harness was checked on known positives first. Across the catalogue, no form of *tomar* plus a name (with `v` written `b`) is shared by two products.
- **Saved live reports:** of 193, only the eight U13d runs change. Each now gives `intake_differs_from_unit_strength` (c1, o0) and `match` (c2, o1). The only texts that resolve differently are "Tomobisoprolol", "Tomovisoprolol", "tomovisoprolol" and "visoprolol".
- **Resolve now:** "visoprolol", "TOMOVISOPROLOL", "TomoVisoprolol", "Tomo-visoprolol", "visoprololum", "Norbasc", "NORBASC", "atorbastatina", "Veloc Zok", "Veloczok", "Veloc/Zok", "VELOC-ZOK", "toma-Veloc-Zok", "tomaveloczok", "Tomopanadol Extra", "tomopanadolextra", "tomoconcor", "tomoemconcor" (Emconcor, not Concor), "tomasortis", "tomassortis", "tomanorvasc", "tomannorvasc", "tomanolotil", "tomamosnolotil", "tomaamlodipino", "tomovisoprolol 5mg", "بvisoprolol", "والvisoprolol", "visoprololو".
- **Stay `None`:** "visoprololo", "envisoprolol", "norbascs", "atorvastatinas", "Veloc", "Velo-Zok", "tomobeloc", "tomóbisoprolol", "Tomásbisoprolol", "tomábisoprolol", "Tomo visoprolól", "tomobisoprolol10", "10tomobisoprolol", "visoprolol10mg", "tomo1bisoprolol", "2tomovisoprolol", "veloc زوك", "tomamlodipino", "tomenbisoprolol", "tomarbisoprolol", "tomébisoprolol", "tomotomovisoprolol", "atomovisoprolol", "tomovisoprololes", "tomosbisoprolol", "tomobisoprololtomametoprolol".
- **Two products now read as ambiguous** (`None`):
  - "Tomovisoprolol y metoprolol" and "visoprolol/metoprolol" (were metoprolol);
  - "Emconcor Veloc-Zok" (was Emconcor) and "بيلوك زوك visoprolol" (was Beloc-Zok);
  - "Veloc-Zok visoprolol", "visoprolol norbasc", "tomoemconcor y tomaveloc-zok", "tomolipitor tomasortis" and "tomobisoprolol/tomometoprolol".

  None of these inputs went from ambiguous to resolved.
- **Arabic:** the 17 Arabic patterns are byte-identical to 3878912's. "tomoكونكور", "كونكورtomo" and "tomoبيلوك زوك" resolve as before.
- **The helpers follow `_matches` with no code of their own:**
  - `covers` holds for the joined forms but not for "Tomo Veloc Zok";
  - `brand_entry` and `matches_brand` hold for "Veloc-Zok" and "Norbasc", but not for the INN-only "visoprolol";
  - `mentions_moiety` follows the fold.
- **Pipeline:** in `claims.py`, `_grounded_by_turns` and the other-medicine name lists stay literal. Only the callers of `resolve` change, and a newly resolved claim moves only its own product's names from "another" to "own".
- **Speed:** inputs of 12,000 to 20,000 characters take 42-63 ms, against 37-42 ms before. The pattern has no nested repeats.

## Round 2 review (2 Nov): SUPERVISOR: APPROVE
Round 2 does what was asked, and nothing in Muse's build has to change before merge. Muse changed only `catalogue.py` and `tests/unit/test_b32_extra.py`, and the locked files are untouched. Ruff is clean and all 2,877 tests pass here, the socket test included. Every check below was rerun offline against contract commit 6722c7f.
- **Round 1's #1 is closed.** These pairs are all `insufficient_information` again, as they were before the batch:
  - "tomometoprolol succinate" against a tartrate pack, as `inn` alone and as name and `inn`;
  - "amlodipine vesilate" against maleate;
  - "visoprolol hemifumarate" against fumarate;
  - "atorbastatin calcium" against calcium trihydrate.

  "metoprolol succinate" still gives `formulation_mismatch`.
- **Nothing else moved.** Of the 92 compiled patterns:
  - the 30 for names that carry a salt are byte-identical to 3878912's;
  - the 17 Arabic ones are byte-identical to 3878912's;
  - the other 45 are byte-identical to round 1's.

  Of round 1's 87 probe inputs, only three moved, and each went back to its pre-batch result: "amlodipine vesilate" no longer covers, and "amlodipinvesilat" and "visoprololfumarat" are unresolved.
- **Saved reports and real words.** Of the 193 saved live reports, still only the eight U13d runs change, as intended. Nothing newly matches out of 729 drug names and 313,489 dictionary entries.
- **#3 is closed.** The three over-matching builds now fail 3 or 4 tests each. Five new breaks are also caught:
  - the salt flag ignored: 6 failures;
  - salt names taking the forms of *tomar*: 3;
  - salt names folded: 5;
  - the moiety flagged as a salt name: 26;
  - no fold at all: 20.
- **#4 is closed.** `TOMAR_FORMS` sits beside `ARABIC_CLITICS` with its SPEC line.

1. **Minor, SPEC wording:** the new known-limit bullet calls the label limit "older than batch 32". That holds for the spaced "tomo metoprolol succinate". The joined "tomometoprolol succinate" as a strength label is new with this batch: against a tartrate pack, it went from `missing_modality` to `match`. Say that the batch widens the limit.
- **Still open, older than batch 32:** `name_text` doesn't read a salt word the alias table lacks, and the table has no Spanish salts. So a claim of "Metoprolol succinato" or "Amlodipino besilato" with no `inn` is a `match` against a tartrate or maleate pack of equal strength. That is true both on `main` and here.
