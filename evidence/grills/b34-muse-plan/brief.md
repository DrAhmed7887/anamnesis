# Batch 34 design: Spanish salt names

You are planning, not building. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, and use no API key;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The plan is done ONLY when your reply has the four sections in §5, and every point cites a file and line you opened in this session.

## 2. The gap
- **Where salts are read:** `SPEC.md` §3, "Decision order for one claim and one pack", rule 6 and its batch 33 bullets. In code: `_side_salts`, `_text_salts` and `_loose_salts` in `anamnesis/core/reconcile.py`. Every salt comes from `INN_ALIASES` (`anamnesis/schema/medication.py`:46–99), whose salt names are English or Latin ("succinate", "tartrate", "fumarate", …).
- **The gap:** a Spanish salt name is never read. On `main` today each of these is reconciled as `match`:
  - "metoprolol succinato", "succinato de metoprolol" or "Tomometoprolol succinato", as an intake label, a strength label or the claim's name, against a "Metoprolol tartrate 100 mg" pack;
  - a claim named "Metoprolol succinate" against Spain's Lopresor box, whose label reads "Lopresor® 100 mg comprimidos recubiertos con película Metoprolol, tartrato 40 Comprimidos";
  - "besilato de amlodipino" against an amlodipine maleate pack, and "amlodipino maleato" against a besilate pack.

  Each hides a formulation difference from the clinician. The product's Spanish test runs use Spain's registry box images, which print the salt in Spanish ("Metoprolol, tartrato", and "Fumarato de bisoprolol" on the Emconcor Cor 5 mg box).
- **The Spanish names, from Spain's medicines registry** (AEMPS CIMA, its list of active substances, read on 2 Nov): METOPROLOL SUCCINATO and METOPROLOL TARTRATO; BISOPROLOL FUMARATO and BISOPROLOL HEMIFUMARATO; AMLODIPINO BESILATO and AMLODIPINO MALEATO; METFORMINA HIDROCLORURO; ATORVASTATINA CALCICA and ATORVASTATINA CALCICA TRIHIDRATO; AMOXICILINA SODICA and AMOXICILINA TRIHIDRATO; CLAVULANATO POTASIO. Each is a salt `INN_ALIASES` already curates in English. The registry writes capitals without accents; Spanish text writes "cálcica" and "sódica".

## 3. Hard limits: the plan keeps all of them
- Deterministic and curated: no model call, and only the Spanish names in §2.
- Nothing that disagrees or abstains today may start to agree. A change may only move a pair away from `match`.
- The Spanish hero's findings stay as they are: with no salt said, "bisoprolol" 10 mg against the Emconcor 5 mg box is `intake_differs_from_unit_strength`, and "metoprolol" 100 mg against the Lopresor box is `match`.
- Name matching (`Catalogue._matches` and every name it resolves) stays as it is.
- One small batch, with contract tests that run offline.

## 4. The CEO's candidate: challenge it, or beat it
A curated table of Spanish salt words beside `INN_ALIASES`, each mapped to the English salt it names: succinato → succinate, tartrato → tartrate, fumarato → fumarate, hemifumarato → hemifumarate, besilato → besilate, maleato → maleate, hidrocloruro → hydrochloride, cálcica or calcica → calcium, cálcica trihidrato or calcica trihidrato → calcium trihydrate, sódica or sodica → sodium, trihidrato → trihydrate, potasio → potassium. `_loose_salts` reads a curated (moiety, salt) pair when the salt's English name or one of its Spanish words stands as whole words in the text and the text names the moiety or its brand, as it already does for English salt words. Word order doesn't matter, so "Fumarato de bisoprolol" and "Metoprolol, tartrato" both count.

The alternative: add the Spanish names to `INN_ALIASES` as aliases ("metoprolol succinato": ("metoprolol", "succinate"), and so on). Say which is safer, given that `INN_ALIASES` also feeds `canonical_inn` and `salt_of` (`medication.py`:109–126), the schema's validator (:139–148), the claim parser's grounding (`anamnesis/providers/claims.py`:255, :287) and catalogue name matching (`catalogue.py`:111–135).

## 5. Reply
1. **The design:** where the change goes (file:line), and whether the candidate or the alternative is right, or something smaller.
2. **Risks:** numbered, each with a file:line and how a test pins it. For instance: accents, a two-word salt ("cálcica trihidrato") beside its one-word form, a Spanish and an English name of one salt on one side, Spanish words that are also ordinary words, the hero's boxes now carrying a salt (pairing scores, rule 7's salt-basis equivalents), and anything that would make a pair agree that disagreed before.
3. **The contract:** the tests you would write first, each named with a one-line assertion and the expected `DiscrepancyType`.
4. **What to leave out:** anything tempting that is out of scope, and why.
