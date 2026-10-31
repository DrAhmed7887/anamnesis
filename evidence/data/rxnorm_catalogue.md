# Catalogue grounded in RxNorm

`scripts/rxnorm_ground.py` maps `anamnesis/core/catalogue.yaml` to RxNorm, the US National Library of Medicine's drug ontology. Only each brand name and its INNs are looked up; the Arabic aliases are not sent. The same data, one record per entry, is in `rxnorm_catalogue.json`.

- **Date:** 2026-10-28 (UTC)
- **API:** NLM RxNav REST API, `https://rxnav.nlm.nih.gov/REST` (no key): `rxcui.json` (exact, then normalized), `rxcui/{rxcui}/properties.json`, `rxcui/{rxcui}/related.json`, `version.json`
- **RxNorm release:** 05-Oct-2026 (API 3.1.356)

## Counts

- Catalogue entries: 9
- INNs: 11 listed across the entries, 9 distinct
- Distinct INNs that map to an RxNorm ingredient (IN): 9 of 9
- Brands in RxNorm as a brand name (BN): 6 of 9. The other 3 are not in RxNorm, which is expected for non-US brands.

## INN to US-name mappings

None needed: RxNorm resolved every INN under its own name. Fallback table: `paracetamol` to `acetaminophen`.

Where RxNorm's ingredient name differs from the INN:

- `paracetamol`: RxNorm's ingredient is `acetaminophen` (161), and RxNorm resolves the INN as a synonym of it
- `clavulanic acid`: RxNorm's ingredient is `clavulanate` (48203); the INN is its precise ingredient `clavulanic acid` (21216)

## INNs that did not map

None.

## Brands

| Brand | RxCUI (BN) | Ingredients RxNorm records for it | Against the catalogue |
|---|---|---|---|
| Concor | none | not in RxNorm | |
| Beloc-Zok | none | not in RxNorm | |
| Norvasc | 58927 | amlodipine (17767) | match |
| Glucophage | 151827 | metformin (6809) | match |
| Panadol | 202432 | acetaminophen (161) | match |
| Panadol Extra | 1872070 | acetaminophen (161), caffeine (1886) | match |
| Augmentin | 151392 | amoxicillin (723), clavulanate (48203) | match |
| Lipitor | 153165 | atorvastatin (83367) | match |
| Gelocatil | none | not in RxNorm | |

## Release forms to check by hand

- Glucophage: the catalogue says immediate, and RxNorm also records `metformin Extended Release Oral Tablet [Glucophage]`
- Augmentin: the catalogue says immediate, and RxNorm also records `amoxicillin / clavulanate Extended Release Oral Tablet [Augmentin]`

---

This product uses publicly available data from the U.S. National Library of Medicine (NLM), National Institutes of Health, Department of Health and Human Services; NLM is not responsible for the product and does not endorse or recommend this or any other product.
