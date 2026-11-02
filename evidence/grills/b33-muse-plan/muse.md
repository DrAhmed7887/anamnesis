muse: workspace root: <repo>/.muse/worktrees/20261102-c4b0 (cwd default)
muse: warning: rules file at <repo>/CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
## 1. The design

- Put the change in the shared salt path `_side_salts` (`anamnesis/core/reconcile.py:282`), on the strength/intake line (`anamnesis/core/reconcile.py:292`), by adding `_text_salts(part.inn, catalogue)` (`anamnesis/core/reconcile.py:251`) beside `part.salt or salt_of(part.inn)` (`anamnesis/schema/medication.py:124`).
- The candidate location is right: rule 6 names one shared salt path (`SPEC.md:303`), and `_side_salts` is that path for both sides (`anamnesis/core/reconcile.py:304`); fixing it there fixes claim strength, claim intake, and pack strength together.
- The candidate function is right, not just whole-alias matching: the joined label needs the loose path because the exact-alias split misses it (`anamnesis/schema/medication.py:139`) and the salted catalogue name matches only as written (`SPEC.md:335`), while `_loose_salts` reads the salt word once the moiety is mentioned (`anamnesis/core/reconcile.py:268`).
- Keep the smaller scope the CEO names: reuse `_text_salts`/`_loose_salts` as-is (`anamnesis/core/reconcile.py:251`), no new salt table beyond `INN_ALIASES` (`anamnesis/schema/medication.py:46`), no catalogue `_matches` change (`anamnesis/core/catalogue.py:111`), no model call.
- Expected effect on the five labels: each names succinate through the alias or loose pass (`anamnesis/core/reconcile.py:251`), so each disagrees with tartrate under rule 6 (`SPEC.md:303`) as `formulation_mismatch`.
- Same-salt stays agreeing: equal named salts do not differ (`anamnesis/core/reconcile.py:318`), so tartrate-in-label against tartrate stays out of rule 6.
- Name-tartrate plus label-succinate abstains: two salts of one ingredient on one side is a rule 3 conflict (`SPEC.md:300`), checked before any cross-side comparison (`anamnesis/core/reconcile.py:312`).
- Rule 7 follows automatically: `_claim_has_salt` reads `_claim_salts` (`anamnesis/core/reconcile.py:224`), which reads `_side_salts` (`anamnesis/core/reconcile.py:304`), so a label-named salt disables the nominal equivalent (`anamnesis/core/reconcile.py:228`).

## 2. Risks

1. Salt word attaches to the wrong moiety in one label: `_loose_salts` pairs any curated salt word with any mentioned moiety (`anamnesis/core/reconcile.py:268`), gated only by `mentions_moiety` (`anamnesis/core/catalogue.py:105`). Pin with a one-part label naming two moieties plus one salt word, asserting no cross-moiety salt is attached.
2. Combination label: a single part naming a combination brand plus a salt word could misattribute, because `mentions_moiety` accepts only single-INN brands (`anamnesis/core/catalogue.py:105`). Pin with an Augmentin-style brand plus a salt word, asserting it does not become the other ingredient's salt.
3. Two aliases where one contains the other: the longer-alias suppression (`anamnesis/core/reconcile.py:259`) and same-moiety salt suppression (`anamnesis/core/reconcile.py:275`) must keep e.g. calcium trihydrate from also reading as calcium (`anamnesis/schema/medication.py:57`). Pin with the longer alias alone, asserting one salt, not two.
4. Hydrate or `(as …)` form: `_inn_and_salt` handles only the exact `(as …)` alias shape (`anamnesis/schema/medication.py:109`), so loose reading newly catches forms like `as besilate` once punctuation is stripped (`anamnesis/core/catalogue.py:12`). Pin with an `(as …)` label, asserting the newly read salt and its exact finding.
5. Arabic text: Arabic normalisation and clitics affect moiety mention (`anamnesis/core/catalogue.py:12`), while salt words stay Latin-curated (`anamnesis/schema/medication.py:46`). Pin with an Arabic label carrying a Latin salt word, asserting the moiety gate still applies.
6. Pack-side label: the same `_side_salts` change affects packs (`anamnesis/core/reconcile.py:308`), so a pack label naming the other salt can force rule 3 abstention (`anamnesis/core/reconcile.py:312`) and lower pairing score (`anamnesis/core/reconcile.py:464`). Pin with a tartrate pack whose strength label says succinate, asserting `insufficient_information`, not `formulation_mismatch`.
7. A `match` flips to a different disagreement than expected: identity and conflict rules run before rule 6 (`anamnesis/core/reconcile.py:414`), and strength labels resolve through the catalogue (`anamnesis/core/reconcile.py:81`). Pin each of the five labels separately, asserting `formulation_mismatch` only where identity still agrees.
8. Nothing may newly agree: added salts only add conflict pairs (`anamnesis/core/reconcile.py:297`) and only add inequality witnesses (`anamnesis/core/reconcile.py:318`), while a newly claimed salt only removes the nominal match route (`anamnesis/core/reconcile.py:232`). Pin with a no-salt nominal-equality pair plus the same pair with a label-named salt, asserting `match` then non-`match`, never the reverse.

## 3. The contract

- `label_tomo_spaced_names_succinate`: `tomo metoprolol succinate` intake against tartrate 100 mg is `formulation_mismatch` (`anamnesis/core/reconcile.py:318`).
- `label_tomo_joined_names_succinate`: `tomometoprolol succinate` intake against tartrate 100 mg is `formulation_mismatch` (`anamnesis/core/reconcile.py:268`).
- `label_comma_names_succinate`: `metoprolol, succinate` intake against tartrate 100 mg is `formulation_mismatch` (`anamnesis/core/reconcile.py:251`).
- `label_retard_names_succinate`: `metoprolol succinate retard` intake against tartrate 100 mg is `formulation_mismatch` (`anamnesis/core/reconcile.py:251`).
- `strength_label_with_amount_names_succinate`: `metoprolol succinate 100 mg` strength label against tartrate 100 mg is `formulation_mismatch` (`anamnesis/core/reconcile.py:292`).
- `label_same_salt_still_matches`: `tomo metoprolol tartrate` against tartrate 100 mg stays `match` (`anamnesis/core/reconcile.py:318`).
- `name_and_label_two_salts_abstains`: tartrate name plus succinate label is `insufficient_information` (`anamnesis/core/reconcile.py:312`).
- `pack_label_other_salt_abstains`: tartrate pack with succinate strength label is `insufficient_information` (`anamnesis/core/reconcile.py:308`).
- `label_salt_disables_nominal`: label-named salt loses the nominal-equivalent match (`anamnesis/core/reconcile.py:224`).
- `spanish_salt_still_unread`: `Metoprolol succinato` still matches equal-strength tartrate (`SPEC.md:339`).

## 4. What to leave out

- Scalar `inn`: leave it on exact `salt_of` per part (`anamnesis/core/reconcile.py:293`), because batch 30 already resolves and abstains there (`SPEC.md:291`).
- `_nominal_pack_amount`'s own salt read (`anamnesis/core/reconcile.py:237`): leave exact-only, since widening pack nominal lookup is a separate equivalence-table change.
- Spanish salt names (`SPEC.md:339`) and any non-curated salt word: adding them would expand `INN_ALIASES` (`anamnesis/schema/medication.py:46`), against the hard limit.
- Catalogue `_matches` and batch 32 rules (`anamnesis/core/catalogue.py:111`): the gap is reconciler salt reading, already flagged as a reconciler batch (`SPEC.md:338`).
- Claim-parser shape checks (`anamnesis/providers/claims.py:125`) and the exact-alias validator (`anamnesis/schema/medication.py:139`): the batch reads longer labels at reconcile time rather than redefining stored labels.

