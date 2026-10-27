# Milestone 2: grill after batch 9 (27 Oct 2026)

Source: an adversarial review pasted into the session by Ahmed (the tool that produced it wasn't stated; the full text stays in the session transcript, and this table is the record). Each code claim was **reproduced offline against `main` before triage**, at $0 cost.

| ID | Claim | Reproduced? | Verdict | Batch |
|---|---|---|---|---|
| F-01A | A tartrate intake against a succinate pack gives `match`: the salt gate ignores `intake_amount.salt` | **Yes → `match`, no review.** Real safety bug | **Accepted (critical)** | B10 |
| F-01B | r = 0.5 returns `intake_differs` before the formulation/salt gate, hiding a known IR-vs-ER or salt difference | Yes. It still requires review, but for the wrong reason | **Accepted:** a known formulation or salt conflict outranks `intake_differs` | B10 |
| F-03a | A brand in `strength.ingredients[].inn` counts as an extraction conflict and pairs with nothing | Yes → `insufficient_information`, and score 0 in pairing | **Accepted:** one resolver (INN, alias, or single-INN brand) for every ingredient field | B10 |
| F-03b | A hallucinated `inn` with no strength skips the conflict check against `name_text` | Yes. "Concor" + `inn=metoprolol` paired with Beloc-Zok | **Accepted** | B10 |
| F-02 | A second brand for one INN makes `resolve` return `None` on labels that print brand and INN | Yes, with a test-only second metoprolol brand | **Accepted:** a brand match covers its own INN mentions | B10 |
| F-08 | "Panadol … and Panadol Extra" resolves to Panadol Extra instead of `None` | Yes | **Accepted:** containment is checked by character span, not by substring | B10 |
| F-04 | Arabic clitics (الكونكور, وبنادول, الPanadol) defeat whole-word matching | Yes, all three → `None` | **Accepted** with the Arabic aliases: letter normalisation (alef, yeh, teh marbuta, tatweel, diacritics), splitting at script boundaries, optional ال/وال/بال. LASA reasoning agrees with the earlier decision against transliteration or embeddings | B11 |
| F-05 | Beloc-Zok 95 mg succinate equals 100 mg tartrate; "metoprolol 100 mg" gives a false `strength_mismatch` | Yes → `strength_mismatch` | **Accepted:** a curated `SALT_BASIS_EQUIVALENTS` table, applied only when the claim names no salt. Metoprolol succinate only, because perindopril isn't in the catalogue | B11 |
| F-06 | A crop-zoom retry must not re-run SAM on the crop, and must keep the source `region_id` and hash | Design point for the agent loop | **Accepted as a constraint:** the crop goes only to Spark, with a "cropped image" prompt | B12 |
| F-07 | Timed-out calls aren't charged; retry traces are dropped; retries could multiply; LLM prose could leak | Timeout billing: true. Prose leak: already blocked, because `Finding` accepts only canonical templates | **Accepted:** a timeout charges the pre-call estimate, retries return every trace, the loop has no outer retry, and `SpendGuard` gets per-session call and $ caps. Arabic words are added to the blocklist as a regression check only | B12 |
| F-09 | No single report artifact; no agentic ablation; no open-weight harness | True | **Accepted:** a `ReconciliationReport` bundle (B12). Open-weight benchmark, Baseten Spark Open first (B13). The 3 tables become the README's evidence plan | B12–B13 |

**Effect:** 11 findings, all accepted. 7 code claims reproduced exactly; F-03a reproduced with a milder outcome than claimed (`insufficient_information`, then unpaired); the rest are design points. The most important catch is **F-01A**: a silent `match` across metoprolol salts. Earlier grills and contracts missed it, because every salt test so far put the salt on `strength`.
