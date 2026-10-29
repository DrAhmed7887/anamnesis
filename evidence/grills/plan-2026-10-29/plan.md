# Plan to the freeze: Spanish and German, 29 Oct 2026, 15:30 CET (grilled before Ahmed decides)

## Where things stand
- **`main` at 25a9274:** 2,075 tests pass. The feature freeze is Sat 31 Oct 23:59 CET; submission is Wed 4 Nov by 15:00.
- **The fine-tune:**
  - r1's results are committed (f07e273): Glimmer + LoRA got 290/303 fully right, against Spark 1.3's 193/303.
  - r2 (the same recipe plus 80 Spanish brands from AEMPS CIMA) is trained, and its adapter is on Modal. Its eval hasn't run.
  - Spark 1.3 on `test_spain` (60 notes) is done: $0.80, with its replies saved but not yet committed.
- **The credits, read at their sources today at 14:45:**
  - **Meta:** $35.03 of $150. It ends 4 Nov, and a card is on file, so past $150 the card pays. Our stop line is $75.
  - **Modal:** $8.72 in October, all from credits, $0.00 billed. $342.41 of grants are left, with a $0 spend limit.
  - **Fireworks:** about $99.70.
  - **Baseten:** the $100 grant is unconfirmed, so no calls.
  - **Google:** $2.54 of $50.95.
- **The product today:**
  - It reads English and Egyptian-Arabic speech. Its number words are English and Arabic only (`anamnesis/providers/stated.py`), so "quinientos miligramos" and "fünfhundert Milligramm" state no amount, while "500 mg" does.
  - `catalogue.normalise()` casefolds, keeps accents and umlauts, and turns "ß" into "ss".
  - The release words (`reconcile.py` `_RELEASE_WORDS`) include "retard" and "depot", but no Spanish forms.
  - `scripts/intake_live.py` `LANGUAGES` has only en and ar.
  - The catalogue's 9 entries carry no codes.
  - The public photos include metoprolol 50 mg ratiopharm (DE), bisoprolol 2.5 mg Sandoz (ES) and Sortis 40 mg (atorvastatin, CZ).

## Steps, in order
### 0. r2's eval and write-up (Thu, engine; Modal about $2.50)
- **The run:** `modal run --detach finetune/modal_glimmer.py --step eval --run r2 --jobs glimmer-base@data_v2/test_spain,glimmer-lora-r1@data_v2/test_spain,glimmer-lora-r2@data_v2/test_spain,glimmer-lora-r2@test_iid,glimmer-lora-r2@test_shift,glimmer-lora-r2@test_codeswitch,glimmer-lora-r2@test_real`.
- **The write-up:** `evidence/finetune/summarize.py --table r2` goes into `results.md`, with every miss, and is committed with Spark's `test_spain` replies.

### 1. Batch 24's contract (Thu night, engine; $0)
`scripts/batch.sh start 24 es-de` makes the branch, then one commit "test(contract): batch 24" holds the SPEC lines, `tests/contract/test_b24_*.py` and `briefs/24.md`. The parts:
1. **Ingredient grounding** (`parse_claims_json`):
   - A claim's `inn` must occur, after `normalise`, in a turn it cites, or it becomes null.
   - An amount's label (the intake's `inn`, and each strength ingredient's `inn`) that is empty or doesn't occur becomes the claim's `name_text`.
   - **Contract pins:** test_iid #79's "string" label; an `inn` of "bisoprolol" when only "Concor" was said; a label of "".
2. **An empty strength object** (`"ingredients": []`) is no strength: it doesn't set off the rule that a dropped amount takes the other with it. **Pin:** Spark's reply to test_shift #34 keeps Naprosyn 550 mg.
3. **The catalogue release fix:** Glucophage and Augmentin get release `unknown`, because RxNorm records extended-release products under both brands (`evidence/data/rxnorm_catalogue.md`:43–46). **Pin:** "Glucophage 500 mg" against an XR pack gives `insufficient_information`, not `formulation_mismatch`.
4. **Spanish and German number words** (`stated.py`), with tables keyed by `normalise()` output:
   - **Spanish:**
     - cero to quince, dieciséis to diecinueve, veinte, veintiuno to veintinueve, treinta to noventa;
     - cien and ciento, doscientos to novecientos (with the -as forms), mil;
     - "y" joins a run; "un", "una" and "uno" are 1; "medio" and "media" are a half, so "y medio" adds 0.5.
   - **German:** one-word compounds up to 9,999 are parsed by a small helper:
     - units (ein, eins, eine, einen, zwei to neun), teens (zehn, elf, zwölf, dreizehn to neunzehn, with sechzehn and siebzehn), tens (zwanzig, dreissig to neunzig);
     - "und" inside a word, "hundert", "tausend";
     - "halb", "halbe" and "halben" are a half; "einhalb" and "eineinhalb" are 1.5; "zweieinhalb" and the rest are n + 0.5.
   - **Not numbers,** as English "twice" isn't one: "zweimal", "dreimal", "dos veces", "tres veces".
   - **SPEC §2 lines** say all of this. The contract pins about 20 forms per language, and checks that "ein"/"eine" before a noun reads as 1, the same way English "one" already does.
5. **Release words:** "prolongada", "modificada", "gastrorresistente", "gastrorresistentes", "retardtablette", "retardtabletten", "retardkapsel", "retardkapseln" and "magensaftresistent" join `_RELEASE_WORDS`. They are modified release: Ph. Eur. counts prolonged and delayed release as modified.
6. **The codes:**
   - **The catalogue:** entries gain optional `atc`, `rxcui` (a list) and `snomed_ct`, taken from `evidence/data/drugs_v2.json` `catalogue`. The loader checks the formats: ATC `^[A-Z]\d\d[A-Z][A-Z]\d\d$`, digit strings otherwise.
   - **The brief:** each resolved medicine's row shows "ATC C07AB07 · RxNorm 19484 · SNOMED CT [SNOMED CT id removed]", escaped. An entry without codes shows nothing.
   - **Pins:** Concor and Panadol Extra.
7. **New catalogue entries, all with CIMA's codes:**
   - **Nolotil:** ES, metamizole, capsule, release immediate, splittable null.
   - **Emconcor:** ES, bisoprolol. It's Merck's Spanish name for Concor, per CIMA.
   - **Sortis:** DE/CZ, atorvastatin. It's Pfizer's name for Lipitor, from the Commons photo and CIMA's ATC for atorvastatin.

   All three are marked `synthetic: true`, as the others are. A metamizole RxCUI comes from RxNav, which calls it dipyrone.
8. **The M7 low items,** only if there's room. These are the first cut.

### 2. Batch 24's build (Fri after 16:00, Muse; Meta about $5)
`scripts/batch.sh run 24`, then the gate, the Opus supervisor and round 2 if needed, then the merge. Usage is reported, as for every batch.

### 3. Live Spanish and German cases (Fri night, after the merge; Meta about $0.50)
- **Pre-registered:** the rows go in `evidence/batches/24/manifest.md` before any call.
- **The voices:** macOS `say`, Flo (Spanish, Spain) and Anna (German), for runs only and never in the film.
- **The runner:** `scripts/intake_live.py --lang es|de`, with `LANGUAGES` gaining `"es": ["Spanish"]` and `"de": ["German"]`.

| Case | Voice note | Photo | Expected, by the product's rules |
|---|---|---|---|
| S1 | "Tomo Emconcor cinco miligramos una vez al día." | none | one claim, Emconcor, 5 mg, once a day; `missing_modality` |
| S2 | "Tomo bisoprolol dos coma cinco miligramos por la mañana." | bisoprolol 2.5 mg Sandoz (ES) | `match` |
| S3 | "Tomo Gelocatil de un gramo cuando tengo dolor." | none | 1 g, as needed; `missing_modality` |
| S4 | "Tomo medio comprimido de Panadol de quinientos." | Panadol 500 mg (FI) | half a tablet; strength 500 mg; `match` or the splittability finding the rules give |
| G1 | "Ich nehme Metoprolol fünfzig Milligramm zweimal täglich." | metoprolol 50 mg ratiopharm (DE) | `match` |
| G2 | "Ich nehme morgens eine halbe Tablette Beloc-Zok hundert Milligramm." | none | 0.5 tablets of a 100 mg tablet; `missing_modality` |
| G3 | "Ich nehme Sortis vierzig Milligramm am Abend." | Sortis 40 mg (CZ) | `match` |
| G4 | "Ibuprofen vierhundert habe ich abgesetzt." | none | discontinued, 400 mg |

### 4. Sat
- the Gemini 4 check of batch 24 (Google, about $1);
- the freeze at 23:59;
- the `demo-freeze` tag;
- a clean-checkout live run of the hero, U12 (about $0.04).

### 5. The story (the judge session; Ahmed relays)
- English and Egyptian Arabic are the tested core.
- Spanish and German were added in batch 24 and tested on 8 synthetic-voice cases.
- Spain's official registry (CIMA) feeds the drug data, and `test_spain` measures unseen Spanish brands.
- German brand data is future work: Germany has no open drug registry.

## The cut order if time runs short
1. the M7 low items;
2. the new catalogue entries;
3. the brief's codes, keeping them in the catalogue;
4. live cases S4 and G3.

Never cut: the two parser fixes, the number words with their contract, and r2's write-up.

## Costs, if everything runs
- **Meta:** about $41 of $150 (27%).
- **Modal:** about $12 of grants.
- **Google:** about $3.50.
- **Fireworks and Baseten:** $0.

## Hours
- **The engine:** about 10 across Thu to Sat.
- **Ahmed:** about 15 minutes of approvals, plus a look at dev.meta.ai/billing on Sat.
