# Decision log

## 2026-10-27: Antigravity suggestions (`docs/SUGGESTIONS_FOR_CLAUDE.md`)
Ahmed approved Antigravity writing suggestions for the orchestrator, and left the decisions to Claude Code.

| Suggestion | Decision | Reason |
|---|---|---|
| Client-side spend cap and ledger | **Accepted**, batch 4 (`SpendGuard`) | Matches SPEC §5 and Muse's m0 advice to log spend per call. Built with the **documented** prices from `docs/muse/`: the file's table listed Spark at $0.15/$0.60 per 1M tokens, while the docs say $1.25/$4.25. SAM and Voice prices were also wrong |
| Barcode / GS1 DataMatrix triangulation | **Deferred** to day 5+, if there's time | Clinically strong, but a GTIN or PZN code only resolves through a product database we don't have offline. It adds a non-Meta component to a Meta hackathon and a native dependency. The PZN example in the file is unverified |
| Four literature citations | **Hold:** verify each one before use | Cornish et al. 2005 (Arch Intern Med) matches known figures. The other three are unverified, and the NEJM AI attribution looks wrong. Nothing goes into the submission unless it has been checked against the source |
| ICU levofloxacin renal-dosing case | **Rejected** | It's inpatient renal dose adjustment, which is dosing-advice territory and outside pre-visit intake |
| Astra M1 action items | Already triaged | `evidence/grills/m1-core/effect.md` |

## 2026-10-27: ER splittability
Muse (M1 #3) said ER tablets can't be split. That is too broad: some scored ER tablets (Beloc-Zok, metoprolol succinate) may be halved. Splittability is therefore a per-product `splittable` flag in the catalogue, not a rule based on release form.

## 2026-10-27: Antigravity files left in the repo
- `CLAUDE.md`: **rewritten** by Claude Code to match the decisions above (the draft had the barcode schema, the unverified citations and the ICU case as instructions, plus a wrong portal address). Committed.
- `docs/SUGGESTIONS_FOR_CLAUDE.md`: decisions logged above. Kept **out of git**, because it contains the wrong price table and personal context. It stays as a local note.
- `docs/DATASET_RESEARCH_AUDIT.md`: a reference for the eval stage (packaging-photo datasets, speech corpora, RxNorm/openFDA/CIMA APIs). **Unverified.** The DOIs and licences get checked before any dataset is used. Kept out of git until then.
