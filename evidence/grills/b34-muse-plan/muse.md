muse: workspace root: <repo>/.muse/worktrees/20261102-0f67 (cwd default)
muse: warning: rules file at <repo>/CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
This is a plan, not a special mode; I haven’t started implementation. Reply `go` to execute this plan, or tell me what to change.

## 1. The design

**Verdict: the CEO's candidate (separate Spanish salt-word table), in a smaller form: consume it only in `_loose_salts`, not as new `INN_ALIASES` keys.** (`anamnesis/core/reconcile.py:268`, `anamnesis/schema/medication.py:46`)

- **Where:** add `SPANISH_SALT_WORDS` beside `INN_ALIASES` (`anamnesis/schema/medication.py:46`), mapping each Spanish word to its English salt (succinato → succinate, …, potasio → potassium, with both accented and unaccented `cálcica/calcica`, `sódica/sodica`), and read it only inside `_loose_salts` (`anamnesis/core/reconcile.py:268`), which already gates on whole-word match plus `mentions_moiety` (`anamnesis/core/reconcile.py:271`).
- **Why not the alternative:** `INN_ALIASES` feeds `canonical_inn`/`salt_of` (`anamnesis/schema/medication.py:119`), the schema validator (`anamnesis/schema/medication.py:139`), claim grounding (`anamnesis/providers/claims.py:255` and `:287`), and identity resolution (`anamnesis/core/reconcile.py:81`), so new alias keys could change identity, grounding, and pairing — including turning an abstention into agreement, which the hard limits forbid. The separate table only widens `_side_salts` (`anamnesis/core/reconcile.py:282`), which feeds rule 3 conflict (`anamnesis/core/reconcile.py:314`), rule 6 `_salts_differ` (`anamnesis/core/reconcile.py:320`), and rule 7 nominal suppression (`anamnesis/core/reconcile.py:228`) — all of which only move pairs away from `match` (`SPEC.md:300`, `SPEC.md:303`, `SPEC.md:310`).
- **Smaller than the candidate:** skip the `_text_salts` exact-alias branch (`anamnesis/core/reconcile.py:253`); Spanish salts on real boxes stand apart from the moiety ("Metoprolol, tartrato", "Fumarato de bisoprolol"), which is exactly the `_loose_salts` shape (`anamnesis/core/reconcile.py:268`), and word order already doesn't matter there because moiety and salt are matched independently (`anamnesis/core/reconcile.py:271`). Normalise Spanish hits to the English salt before the per-moiety set is built (`anamnesis/core/reconcile.py:299`), and extend the longer-suppresses-shorter rule (`anamnesis/core/reconcile.py:275`) across both languages.

## 2. Risks

1. **Accents read twice:** Spanish prints `cálcica`/`sódica` but registries write capitals without accents (`SPEC.md:59` notes accents are kept by `normalise`); `_loose_salts` matches on `normalise`d text (`anamnesis/core/reconcile.py:271`), and alias keys match after NFC (`anamnesis/schema/medication.py:110`). Pin with a test pairing `cálcica` and `calcica` forms against the same pack, both `formulation_mismatch`.
2. **Two-word salt beside its one-word form:** `cálcica trihidrato` vs `cálcica` must behave like `calcium trihydrate` vs `calcium`, which are kept apart (`SPEC.md:308`), with the longer suppressing the shorter on one side (`anamnesis/core/reconcile.py:275`). Pin with `atorvastatina cálcica trihidrato` vs calcium pack → `formulation_mismatch`, and a single side naming both → `insufficient_information` via rule 3 (`anamnesis/core/reconcile.py:314`).
3. **Spanish + English names of one salt on one side:** `succinato` and `succinate` together must count as one salt, not two, so normalisation to English must happen before the set build (`anamnesis/core/reconcile.py:299`), else rule 3 abstains wrongly (`anamnesis/core/reconcile.py:314`). Pin with a label naming both against a tartrate pack → `formulation_mismatch`, not `insufficient_information`.
4. **Spanish salt words that are ordinary words:** an unmoored word match would over-fire; `_loose_salts` requires the text to name the moiety or brand (`anamnesis/core/reconcile.py:273`). Pin with the salt word present but no moiety/brand (e.g. `potasio` in diet text) → finding unchanged (`SPEC.md:303` shared path only).
5. **Hero boxes now carry a salt:** Emconcor/Lopresor labels gain fumarate/tartrate via `_pack_salts` (`anamnesis/core/reconcile.py:310`), but `_salts_differ` needs both sides to name a salt (`anamnesis/core/reconcile.py:324`), and rule 7 nominals still apply when the claim names none (`anamnesis/core/reconcile.py:228`, `SPEC.md:310`). Pin both hero findings unchanged: bare `bisoprolol` 10 mg → `intake_differs_from_unit_strength`, bare `metoprolol` 100 mg → `match`; pairing scores are strength/identity based, not salt based (`SPEC.md:324`).
6. **New rule 3 abstentions must be the only new abstentions:** a side naming two different salts (e.g. Spanish succinato + English tartrate) becomes `insufficient_information` (`anamnesis/core/reconcile.py:314`, `SPEC.md:300`). Pin with such a claim vs either pack → `insufficient_information`.
7. **Nothing may start to agree:** the table must not feed `canonical_inn`/`salt_of` (`anamnesis/schema/medication.py:119`), the validator (`anamnesis/schema/medication.py:139`), grounding (`anamnesis/providers/claims.py:287`), or identity/catalogue resolution (`anamnesis/core/reconcile.py:43`, `SPEC.md:332`). Pin with an `unresolved_name`, an `ingredient_mismatch`, and an `insufficient_information` pair each unchanged after the batch.
8. **Punctuation and word order:** `succinato de metoprolol`, `Tomometoprolol succinato`, `Metoprolol, tartrato` must all hit via padded whole-word match (`anamnesis/core/reconcile.py:253`) plus moiety gating (`anamnesis/core/reconcile.py:271`), as batch 33 did for English labels (`SPEC.md:304`). Pin each form → `formulation_mismatch` vs the wrong-salt pack.
9. **Salt-in-label scope:** batch 33 reads each strength/intake label through `_text_salts` (`anamnesis/core/reconcile.py:293`, `SPEC.md:304`), while the scalar `inn` uses `salt_of` only (`anamnesis/core/reconcile.py:297`) — Spanish in a scalar `inn` stays unread. Pin with Spanish salt in strength label → `formulation_mismatch`, but in scalar `inn` alone → unchanged.

## 3. The contract

Each is an offline `reconcile_pair` test (Claim vs PackObservation, bundled catalogue):

- `spanish_intake_label_succinato_vs_tartrate`: intake label `metoprolol succinato` vs Metoprolol tartrate 100 mg → `formulation_mismatch` (`anamnesis/core/reconcile.py:320`).
- `spanish_reordered_succinato_de_metoprolol`: `succinato de metoprolol` vs tartrate 100 mg → `formulation_mismatch` (`anamnesis/core/reconcile.py:268`).
- `spanish_joined_tomometoprolol_succinato`: `Tomometoprolol succinato` vs tartrate 100 mg → `formulation_mismatch` (`SPEC.md:341` salt read as written; `anamnesis/core/reconcile.py:268`).
- `spanish_pack_tartrato_vs_succinate_claim`: claim `Metoprolol succinate` vs Lopresor label `Metoprolol, tartrato` → `formulation_mismatch` (`anamnesis/core/reconcile.py:310`).
- `spanish_besilato_vs_maleato` / `spanish_maleato_vs_besilato`: `besilato de amlodipino` vs maleate pack, and `amlodipino maleato` vs besilate pack → `formulation_mismatch` (`anamnesis/core/reconcile.py:320`).
- `spanish_fumarato_label_vs_pack`: `Fumarato de bisoprolol` label vs non-fumarate bisoprolol pack → `formulation_mismatch` (`anamnesis/core/reconcile.py:293`).
- `spanish_same_salt_still_matches`: `metoprolol succinato` vs succinate pack, equal strength → `match` (`SPEC.md:306` unchanged: own salt still matches).
- `hero_bisoprolol_bare_unchanged`: bare `bisoprolol` 10 mg vs Emconcor 5 mg → `intake_differs_from_unit_strength` (`anamnesis/core/reconcile.py:228`).
- `hero_metoprolol_bare_unchanged`: bare `metoprolol` 100 mg vs Lopresor box → `match` (`anamnesis/core/reconcile.py:324`).
- `spanish_two_salts_one_side_abstains`: one side naming succinato + tartrate → `insufficient_information` (`anamnesis/core/reconcile.py:314`).

## 4. What to leave out

- **Adding Spanish keys to `INN_ALIASES`:** changes identity, validation, grounding, and catalogue matching (`anamnesis/schema/medication.py:119`, `anamnesis/schema/medication.py:139`, `anamnesis/providers/claims.py:287`, `SPEC.md:332`), risking new agreements; the side table is sufficient (`anamnesis/core/reconcile.py:282`).
- **Touching `Catalogue._matches`/name resolution or `mentions_moiety` gating:** name matching stays as is per the hard limits; the moiety gate already exists (`anamnesis/core/reconcile.py:273`, `SPEC.md:332`).
- **New salt-basis equivalents or merging calcium/calcium-trihydrate, fumarate/hemifumarate:** rule 7 equivalents are a curated mg table (`anamnesis/schema/medication.py:101`, `SPEC.md:310`), and the pairs are deliberately kept apart (`SPEC.md:308`); merging would move pairs toward `match`.
- **Spanish salt handling in the scalar `inn` (`salt_of`), the claim parser, or the label prompt:** pack salts come only from the curated split of `inn` (`SPEC.md:47`), the scalar path is read as before (`SPEC.md:306`), and prompts stay frozen; batch scope is the reconciler's loose-salt read plus contract tests.
- **More Spanish words than §2's list or accent-folding `normalise`:** curated-only and deterministic; both accent forms are listed explicitly instead of changing shared normalisation (`anamnesis/core/reconcile.py:253`).

Reply `go` to execute this plan, or tell me what to change.
