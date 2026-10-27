# Batch 10 review: identity and salt fixes (M2 F-01, F-02, F-03, F-08)

Reviewer: Claude Code (Opus 5.5). Builder: codex `gpt-6-luna` (no rate limits this time). Gate: pass, 284 tests. The contract started red with 10 failing tests, each a bug reproduced on `main`.

Verdict: PASS

## Checked
- **F-01A (critical):** salts are now collected from `strength` ingredients, `intake_amount.salt` and `salt_of(claim.inn)` on the claim, and from `strength` and `salt_of(pack.inn)` on the pack. Tartrate vs succinate now gives `formulation_mismatch`; before, it was a silent `match`. ✅
- **F-01B:** the salt and known-release conflict check runs **before** any amount comparison, so half a Beloc-Zok can no longer hide an IR/ER or salt conflict. The "modified vs unknown → `insufficient_information`" gate stays last, before `match`. ✅
- **F-03:** one `_resolve_inn` (curated alias → known moiety → single-INN brand → unchanged) is used by strengths, the scalar `inn`, intakes, the strength comparison and pairing scores. A scalar `inn` that contradicts the spoken or printed name is a conflict. The batch 9 special case is gone. ✅
- **F-02:** a brand match covers its own INN mentions. Text that only names an ingredient still resolves when every candidate shares one INN set, and brand-implied facts still require a brand match. ✅
- **F-08:** matches carry character spans (`finditer`), and suppression requires the span to be strictly inside another. "Panadol … and Panadol Extra" now gives `None`. ✅

## Note (not blocking)
- When only an ingredient is named, `resolve` now sorts by brand before country, so the country preference only breaks ties. Identity is unaffected (same INN set), and brand-implied facts need a brand match anyway.
