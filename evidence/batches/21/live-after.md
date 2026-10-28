# Batch 21: the same pre-registered cases on the merged code, 28 Oct (after the batch)

**Setup.**
- Code: `main` after the batch 21 merge (`ea5a705`).
- Cases: the same cases, voice notes, photos and expected results as `live-before.md` and `manifest.md`, unchanged. Each ran once, named `<case>-b21` in `evidence/live/2026-10-28/`.
- Cost: 12 intakes for **$0.36897**, plus 2 diagnostic calls for $0.02221. The ledger total is now $1.21236.

**Latency.** Claim requests took 8.3–26.4 s. All were inside the 30 s timeout, but U10's 26.4 s is close. One intake took 17–49 s end to end.

## Synthetic notes (QM M4 #6): regression fixed, 6 of 6
| Note | Before | After |
|---|---|---|
| English: Concor "five milligrams once a day" | `insufficient_information` | **`match`** |
| English: metoprolol 50 mg twice a day vs Beloc-Zok 100 mg | `intake_differs_from_unit_strength` | same ✓ |
| English: Panadol, stopped | stopped ✓ | same ✓ |
| Arabic: كونكور خمسة ملي جرام | `insufficient_information` | **`match`** |
| Arabic: بيلوك زوك خمسين ملي جرام vs Beloc-Zok 100 mg | `insufficient_information` | **`intake_differs_from_unit_strength`** |
| Arabic: البنادول, stopped | stopped ✓ | same ✓ |

## Public pack photos (U1–U10): 3 of 10 correct, up from 1
| Case | Expected | Before | After | Verdict | Cause now |
|---|---|---|---|---|---|
| U1 Concor, Russia (Cyrillic) | `match` | `insufficient_information` | **`match`** | correct | |
| U2 Augmentin, Belgium (French) | `match` | unpaired | paired, `insufficient_information` | miss, fails safe | The pack now pairs: the French INNs resolve. But the claim "Augmentin, 875 and 125 milligrams" came back with no strength |
| U3 Panadol, Australia | `match` | `insufficient_information` | **`match`** | correct | `label_text` is now complete, so 500 mg is kept |
| U4 Panadol 500 mg, Finland, two tablets | `intake_differs_from_unit_strength` | same | same | correct | |
| U5 Norvasc 5 mg and 10 mg, Israel | claim ↔ 5 mg `match` | claim ↔ 10 mg | claim ↔ 10 mg, `insufficient_information` | **miss, wrong pairing** | In this run the claim *and* the 5 mg pack both came back without amounts, so the two boxes tied. A diagnostic call on the same inputs got clean amounts on both sides (5 mg intake, amlodipine 5 mg): this is model variance. Spark still sometimes writes an amount as a word, which never parses |
| U6 Glucophage, China | `match` | `unresolved_name` | same | miss, fails safe | The reader transcribed the manufacturer block, not the brand and strength |
| U7 Sortis 40 mg vs "Lipitor twenty milligrams" | `strength_mismatch` | `insufficient_information` | the pack `partial`, so `unreadable_source` | miss, not harmful | The reader judged the pack only partly readable this time. The CEO's key error, noted before, stands |
| U8 Betaloc ZOK 100 | `match` | `unreadable_source` | same | miss, not harmful | Low resolution, unit cut off |
| U9 Panadol Extra carton | `ingredient_mismatch` | no pack found | same | miss, fails safe | SAM finds no pack in flat label artwork |
| U10 Panadol Extra Strength 500 | `match` | no pack found | same | miss, fails safe | as U9 |

**Harm check.** No false `match`, and no wrong strength or ingredient shown as fact. U5's wrong pairing remains. It is now a tie between two boxes, after both amounts were dropped.

**What comes next.**
- **Batch 22** carries one more fail-safe fix: an amount written as a number word ("five", «خمسة») parses through the same number-word reader as `stated_amounts`, and must still be stated. This removes the cause of U5 and any similar drop in Ahmed's hero note, where «خمسمية» and «جرام واحد» are spoken in words.
- **U2's combination claim** needs the raw reply to diagnose.
- **U6:** what part of the box SAM picks.
- **U9 and U10:** no fix planned.
