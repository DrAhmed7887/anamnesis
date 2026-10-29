# Drug vocabulary from RxNorm

`scripts/rxnorm_drugs.py` takes 60 INNs and records, from RxNorm only, each one's ingredient, up to 3 brands, up to 6 oral strengths and the oral dose forms. Machine-readable twin: `rxnorm_drugs.json`, which pairs each strength with its dose forms and the RxNorm clinical drugs behind it.

- **Date:** 2026-10-28 to 2026-10-29 (UTC)
- **API:** NLM RxNav REST API, `https://rxnav.nlm.nih.gov/REST` (no key): `rxcui.json`, `rxcui/{rxcui}/properties.json`, `rxcui/{rxcui}/related.json` (`tty=BN+SCD`, `tty=SBD`, `rela=inverse_isa`), `rxcui/{rxcui}/allProperties.json`, `version.json`
- **RxNorm release:** 05-Oct-2026 (API 3.1.356)

## Rules

- Oral: a dose form RxNorm files under its dose form group `Oral Product` (39 forms).
- Marketed: RxNorm's attributes say `HUMAN_DRUG` and `PRESCRIBABLE` = Y. Veterinary and discontinued products are left out, and the parsed strength must match `AVAILABLE_STRENGTH`.
- Strengths: single-ingredient clinical drugs (SCD) only, in RxNorm's units (MG, MG/ML). Past 6, the ones found in the most RxNorm products are kept.
- Brands: a BN with a marketed branded drug of a kept SCD. The most such drugs first, then the older RxCUI.

## Counts

- INNs: 60, of which 60 map to an RxNorm ingredient
- INNs with a brand: 55 (102 brands in all)
- INNs with an oral strength: 59 (270 strengths kept; 17 INNs have more than 6 in RxNorm)
- Distinct oral dose forms seen: 17
- RxNorm clinical drugs read: 1633. Kept 463. Left out: 899 combinations, 118 non-oral, 149 oral but not a marketed human drug, 4 mass-per-mass (MG/MG), 0 whose strength disagreed with RxNorm's, 0 unparsed.

## US-name mappings

None needed: every INN resolved as written. Fallback table: `acetylsalicylic acid` to `aspirin`, `alendronic acid` to `alendronate`, `paracetamol` to `acetaminophen`.

RxNorm names the ingredient differently for:

- `acetylsalicylic acid`: `aspirin` (1191)
- `paracetamol`: `acetaminophen` (161)
- `alendronic acid`: `alendronate` (46041)

## INNs with no brand

`bisoprolol`, `indapamide`, `gliclazide`, `glimepiride`, `terbinafine`.

## INNs with no oral strength

`gliclazide`.

## Not in RxNorm

None.

## Check by hand

Strength disagreed with RxNorm, or name did not parse: none.

---

This product uses publicly available data from the U.S. National Library of Medicine (NLM), National Institutes of Health, Department of Health and Human Services; NLM is not responsible for the product and does not endorse or recommend this or any other product.
