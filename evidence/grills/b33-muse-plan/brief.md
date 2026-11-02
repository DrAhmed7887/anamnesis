# Batch 33 design: a salt said inside a longer label

You are planning, not building. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, and use no API key;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The plan is done ONLY when your reply has the four sections in §5, and every point cites a file and line you opened in this session.

## 2. The gap
- **Where salts come from:** `SPEC.md` §6 ("Decision order", rule 6) says each side's salts come from one shared path. In code that path is `_side_salts` (`anamnesis/core/reconcile.py`:282–301). It reads:
  - each strength ingredient and the claim's `intake_amount`, through `part.salt or salt_of(part.inn)` (:292);
  - the scalar `inn`, through `salt_of` (:293–295);
  - `name_text` or `label_text`, through `_text_salts` (:251–265): whole-word curated salt aliases, plus `_loose_salts` (:268–279), curated salt words standing apart from a moiety or brand the text names.
- **The gap:** `salt_of` (`anamnesis/schema/medication.py`:124) knows only an exact alias, so a salt said inside a longer ingredient label is never read. Each of these, as an intake label or a strength ingredient's label, is reconciled as `match` against a "Metoprolol tartrate 100 mg" pack on `main` today:
  - "tomo metoprolol succinate";
  - "tomometoprolol succinate";
  - "metoprolol, succinate";
  - "metoprolol succinate retard";
  - "metoprolol succinate 100 mg" (as a strength label).

  The exact label "metoprolol succinate" already gives `formulation_mismatch`. A false match on salt hides a formulation difference from the clinician, so this is a release-gate item.
- **How such labels arise:** the claim parser keeps the model's ingredient label as written (`anamnesis/providers/claims.py`:125–148 checks only its keys: `inn`, `amount`, `unit`), and `IngredientAmount`'s validator splits only an exact alias (`medication.py`:139–148).

## 3. Hard limits: the plan keeps all of them
- Matching stays deterministic and curated: no model call, and no salt table beyond `INN_ALIASES` (`medication.py`:46–99).
- Nothing that disagrees today may start to agree. A change may only turn a `match` into a disagreement or an abstention, never the reverse.
- Name matching (`anamnesis/core/catalogue.py`, `Catalogue._matches`) and its batch 32 rules stay as they are.
- It is one small batch, with contract tests that run offline.

## 4. The CEO's candidate: challenge it, or beat it
In `_side_salts`, read each part's `inn` label the way `name_text` is read: add `_text_salts(part.inn, catalogue)` beside `part.salt or salt_of(part.inn)`. Expected effects:
- the five labels above name succinate, so they become `formulation_mismatch` against tartrate;
- a label that names the pack's own salt ("tomo metoprolol tartrate") still matches;
- a side whose name says tartrate and whose label says succinate names two salts, so rule 3 gives `insufficient_information`;
- in rule 7, a claim whose label names a salt is compared without the pack's salt-basis equivalents (`_claim_has_salt`, :224–238), exactly as one that names it in its exact label or in its name;
- left alone: the scalar `inn` (already abstains through rule 3), `_nominal_pack_amount`'s own salt reading (:237), and the Spanish salt names the table doesn't hold.

## 5. Reply
1. **The design:** where the change goes (file:line), and whether the candidate is right or something smaller or safer is.
2. **Risks:** numbered, each with a file:line and how a test pins it. For instance: a salt word that attaches to the wrong moiety, a combination label (amoxicillin with clavulanate), two aliases where one contains the other, a hydrate or a "(as …)" form, Arabic text, a pack-side label, a `match` that could flip to a different disagreement than expected, and anything that would make a pair agree that disagreed before.
3. **The contract:** the tests you would write first, each named with a one-line assertion and the expected `DiscrepancyType`.
4. **What to leave out:** anything tempting that is out of scope, and why.
