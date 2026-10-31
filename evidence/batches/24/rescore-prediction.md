# Batch 24: the re-score after the merge, predicted before the build

**Written 29 Oct at 17:50 CET, before batch 24's Muse run.**
- **What happens after the merge:** every committed fine-tune reply is re-scored with the merged parser, at $0.
- **Where these numbers come from:** the CEO's reference build (`reference.md` on the batch branch), scored the same way. So any difference after the merge means Muse's build behaves differently from the reference, and each difference is reported.

## Fully right (`evidence/finetune/summarize.py`, scorer unchanged)
| System | r1's four splits (303 notes) | test_spain (60 notes) |
|---|---|---|
| Spark 1.3 | 193 → **203** | 38 → **40** |
| Glimmer base | 50 → 51 | 11 → 11 |
| Glimmer + LoRA r1 | 290 → 290 | 55 → 55 |
| Glimmer + LoRA r2 | 295 → 295 | 56 → 56 |

- **Where Spark gains:** intakes, 506 → 529 of 547 on r1's splits and 93 → 96 of 108 on test_spain. These are amounts the drop rule used to lose after an empty strength object or label.

## Harmful claims after the checks
**The scorer must change first.**
- **How it counts today:** `finetune/score.py` counts "after the checks" on the raw reply's strings, with flags for which amounts the product kept. Before batch 24 that matched the product's own output.
- **Why that breaks:** batch 24 replaces empty or ungrounded labels and nulls unsaid INNs. The raw count then rises (base Glimmer 54 → 79, test_spain 9 → 15) while the product shows fewer.
- **The change, after the merge:** `score.py` counts "after the checks" on the product's parsed output. An INN said under an alias (said "acetaminophen", stored "paracetamol") counts as said.
- **Its check:** under today's parser, the change must leave every committed number as it is.

**Counted on the product's output** (`harm_parsed.py`; outputs in `harm_parsed_main.out` and `harm_parsed_reference.out`, aliases set aside):

| System | r1's four splits: today → batch 24 | test_spain: today → batch 24 |
|---|---|---|
| Glimmer base | 54 → **0** | 9 → **0** |
| Spark 1.3 | 1 → **0** (the "string" label, test_iid #79) | 0 → 0 |
| Glimmer + LoRA r1 and r2 | 0 → 0 | 0 → 0 |

- **What base Glimmer's 54 were:** placeholders and misplaced values kept as ingredient strings ("unknown", "mg", "null", "100", "amount_digit_text").
- **The alias, set aside above:** `harm_parsed.py` also prints "paracetamol" where the patient said "acetaminophen" (test_iid #19 and #73). That is the same ingredient under its international name, not harm.
- **What this doesn't say:** the product's extractor is Spark 1.3. Base Glimmer is in this table only because its replies are the hardest test of the checks.
