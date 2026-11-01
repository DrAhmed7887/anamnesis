# NCBI, at build time only: PubMed citations and a PubChem check of the INN aliases (31 Oct 2026)

**Origin:** the "NCBI and UpToDate integration review" session, on Ahmed's call (31 Oct), handed both items to the engine. NCBI is used only while building, never by the product at runtime: a runtime lookup would send a patient's drug names to NIH, and `docs/DATA_HANDLING.md` sends media only to Meta. UpToDate stays out of the product (its licence, and the no-advice rule).

## 1. PubMed: for the README and `docs/CLAIMS.md` (owner: the judge session)
Each record was re-read by the engine through NCBI E-utilities on 31 Oct (`pubmed_esummary.json`: authors, journal, volume, pages, DOI). The numbers come from each abstract, read the same day. The abstracts themselves aren't stored here: they are the publishers' text.

| Claim | Source |
|---|---|
| In an outpatient practice, comparing what patients take (their medicine bottles) with the doctor's record, **239 patients (76%) had at least one discrepancy**. Of the 545 discrepancies, 51% were medicines taken but not recorded, 29% recorded but not taken, and 20% a different dose. | Bedell SE et al. *Arch Intern Med* 2000;160(14):2129–34. PMID 10904455. doi:10.1001/archinte.160.14.2129 |
| At hospital admission, medication history errors occur in up to 67% of patients (a systematic review: 22 studies, 3,755 patients). | Tam VC et al. *CMAJ* 2005;173(5):510–5. PMID 16129874. doi:10.1503/cmaj.045311 |
| At hospital admission, 53.6% of patients (81 of 151) had at least one unintended discrepancy, and 38.6% of the discrepancies could have caused moderate to severe harm. | Cornish PL et al. *Arch Intern Med* 2005;165(4):424–9. PMID 15738372. doi:10.1001/archinte.165.4.424 |
| In a cluster-randomised trial in six primary-care clinics (224 patients), **9 (7.6%) of the usual-care patients and 8 (7.5%) with the app had 0 discrepancies** between their medication list and a pharmacist's best possible medication history. Read 1 Nov 2026 (`pubmed_esummary_2026-11-01.json`). | Gionfriddo MR et al. *JMIR Form Res* 2022;6(3):e33488. PMID 35023836. doi:10.2196/33488 |
| In a multicentre retrospective chart review of 60-minute pharmacist telemedicine visits in geriatric primary care (275 visits scheduled), **at least one unintentional medication discrepancy was found in 151 patients (66%)**. Read 1 Nov 2026 (`pubmed_esummary_2026-11-01.json`). | Handshaw JV et al. *J Pharm Pract* 2024;37(4):889–94 (epub 2023). PMID 37586717. doi:10.1177/08971900231196178 |
| README line 14, "helped them prepare in 33 of 44 cases": **confirmed**. The study enrolled 114 patients, and 98 completed both the AI chat and the visit; it isn't "n=100". | Brodeur PG et al. *Lancet* 2026;408(10565):1732–44. PMID 42849491. doi:10.1016/S0140-6736(26)01535-7 |

- **Lead with Bedell 2000.** It is outpatient care, before the visit, and compares what patients take with the record: Anamnesis's premise. Tam and Cornish are hospital admissions, so say "at admission" if they are used.
- **These are the studies' numbers.** Anamnesis measured none of them: they describe the problem, not the product.

## 2. PubChem: the INN aliases (owner: the engine)
- **The probe:** `pubchem_probe.py` (read-only, written by the review session), run on `anamnesis/schema/medication.py` at 87e572c. For each alias it resolves name → CID → parent CID (or the components, for mixtures) and compares it with the CID of the moiety the alias maps to. Output: `pubchem_aliases.json`.
- **Result: 35 of 52 aliases agree with PubChem, none disagree, and 17 aren't listed there.** The 17 are Latin genitive salt names, German compounds and accented forms; they need another source (Ph. Eur. names, or the CIMA data in `evidence/data/drugs_v2.json`).
- **The salt basis:** metoprolol succinate 47.5 mg carries 38.91 mg of base and tartrate 50 mg carries 39.04 mg, 0.34% apart at all four strengths (`salt_basis.txt`; molecular weights from PubChem).
- **Say it as:** "35 of 52 aliases agree with PubChem, none disagree, 17 aren't listed there". Never "verified against PubChem" on its own.
- **Next (engine, cut first if time runs short):** a test that reads a committed snapshot of this result, with no network in tests.
