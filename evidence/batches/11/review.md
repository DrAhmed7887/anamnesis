# Batch 11 review: Arabic-script brands (M2 F-04) and salt-basis equivalence (M2 F-05)

Reviewer: Claude Code (Opus 5.5). Builder: codex `gpt-6-luna`, which hit 4 rate-limit (429) retries and finished. Gate: pass, 328 tests. The contract started with 22 failing tests; all 3 Arabic fixtures are real live claims.

Verdict: PASS

## Checked
- **Aliases:** curated, and treated as **brand** names, so they carry release and splittability. Both live spellings of Beloc-Zok are present (`بيلوك زوك`, `بلوك زوك`). No partial names: `بيلوك` alone stays `None`. ✅
- **Normalisation:** removes tatweel and diacritics, unifies alef, yeh and teh marbuta, converts Arabic-Indic digits, and splits at script boundaries (`الPanadol` → `ال panadol`). It's applied to both text and catalogue names. ✅
- **Clitics:** the optional prefix (`وال|بال|فال|لل|ال|و|ف|ب|ل`) applies **only** to Arabic-script names, inside the whole-word boundary. Spans still drive ambiguity. ✅
- **LASA traps** (Cordarone, Cozaar, Tramadol, Nolvadex, partial names) all stay `None`. ✅
- **Salt basis:** a curated metoprolol-succinate table is used only when the claim names **no** salt. It now also checks for a salt spoken in `name_text`, which partly addresses QM #2. The formulation gate still applies, so unknown-vs-modified release stays `insufficient_information`. ✅

## Notes (not blocking)
- `_claim_strength_type` narrows the type with `assert`. Fine with the default interpreter; make it a guard if the project ever runs with `-O`.
