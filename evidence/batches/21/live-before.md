# Batch 21: first live runs on today's code, 28 Oct (before the batch is built)

**Setup.**
- Code: branch `batch/21-real-media` before its build. In `anamnesis/` it is identical to `main` 3b40d5a.
- Runner: `scripts/intake_live.py` (8b993ff). The expected results were pre-registered in `manifest.md` (8b993ff) before the first call.
- Volume: 12 intakes plus 1 diagnostic claim call. 59 adapter calls, **$0.33919** on the ledger. The ledger total is now $0.82189.
- Reports: `evidence/live/2026-10-28/`, one line per run in `runs.jsonl`. The briefs are git-ignored.

**Latency.** Every claim-extraction request finished well inside the client's 30 s timeout: 8.2–14.6 s. One intake took 14–36 s from start to finish.

## The two 27 Oct synthetic notes (QM M4 #6): a regression
| Note | Medicine | 27 Oct | Today | Why |
|---|---|---|---|---|
| English | Concor, "five milligrams once a day" | `match` | `insufficient_information` | Spark wrote `"amount": "five"` |
| English | metoprolol 50 mg twice a day vs Beloc-Zok 100 mg | `intake_differs_from_unit_strength` | same ✓ | |
| English | Panadol, stopped | `missing_modality` (stopped) | same ✓ | |
| Arabic | كونكور خمسة ملي جرام | `match` | `insufficient_information` | the amount was spoken in words |
| Arabic | بيلوك زوك خمسين ملي جرام vs Beloc-Zok 100 mg | `intake_differs_from_unit_strength` | `insufficient_information` | the amount was spoken in words |
| Arabic | البنادول, stopped | `missing_modality` (stopped) | same ✓ | |

Both briefs still show the `same_class` beta-blocker observation.

**Root cause.**
- A diagnostic call captured Spark's raw reply for the English note: `"amount": "five"` and `"intakes_per_day": "once a day"`.
- Batch 20's new prompt sentence, "Write each amount with the number and unit the patient said", makes Spark copy number words. Those never parse (SPEC §2), so the amount is dropped.
- So since batch 20, every dose spoken in words has failed safe to `insufficient_information`.
- The offline tests couldn't see it: their fixture replies already hold digits. No live run followed batch 20.

**Fix:** batch 21 item 7. Amounts are now asked for as digits, and the stated-amount check still confirms each one was said.

## Public pack photos (U1–U10, pre-registered): 1 of 10 correct
| Case | Expected | Today | Verdict | Cause | Fixed by |
|---|---|---|---|---|---|
| U1 Concor, Russia (Cyrillic) | `match` | `insufficient_information` | miss, fails safe | The pack was read correctly: bisoprolol 5 mg from a Cyrillic label. The claim lost its "five" | item 7 |
| U2 Augmentin, Belgium (French) | `match` | the claim and the pack were left unpaired, as two `missing_modality` | miss, fails safe | The reader returned "amoxicilline" and "acide clavulanique", which don't overlap with the claim's INNs | items 7, 8 |
| U3 Panadol, Australia | `match` | `insufficient_information` | miss, fails safe | `label_text` was only "Panadol TABLETS", so batch 20's label rule dropped the 500 mg the reader reported | item 7 |
| U4 Panadol 500 mg, Finland, "two tablets at a time" | `intake_differs_from_unit_strength` | same | **correct** | | |
| U5 Norvasc 5 mg and 10 mg, Israel | claim ↔ 5 mg `match`; 10 mg `missing_modality` | claim ↔ **10 mg** `insufficient_information`; the 5 mg box reported as "Photographed, not mentioned" | **miss, wrong pairing** | The intake-only claim tied at score 2 with both boxes, and the tie went by id | item 9 |
| U6 Glucophage, China (Chinese only) | `match` | the pack `unresolved_name`; the claim `missing_modality` | miss, fails safe | No INN came back from a Chinese-only label | item 7 (English INN) |
| U7 Sortis 40 mg vs "Lipitor twenty milligrams" | `strength_mismatch` | `insufficient_information` | miss against the key | Spark extracted an intake, not a strength. Half of a 40 mg tablet of unknown splittability is `insufficient_information` (rule 8), which is what the SPEC says. **The pre-registered key assumed a strength; that was the CEO's error.** The key stays as written | none needed |
| U8 Betaloc ZOK 100, Czech Republic | `match` | the pack `partial`, so `unreadable_source`; the claim `missing_modality` | miss, not harmful | Low-resolution photo, and the unit is cut off at the edge. The reader abstained even after the 2× zoom | none (correct abstention) |
| U9 Panadol Extra carton, US | `ingredient_mismatch` | the claim `missing_modality`; no pack found | miss, fails safe | SAM found no pack in a flat label-artwork image. A phone photo of a box is a different input | none planned |
| U10 Panadol Extra Strength 500, US | `match` | the claim `missing_modality`; no pack found; the claim also lost its amount | miss, fails safe | as U9, plus item 7 | item 7 |

**Harm check.**
- No false `match`. No wrong strength or ingredient was shown as fact.
- The one result in a release-gate class is **U5's wrong pairing**: the brief showed the patient's Norvasc next to the wrong box. Batch 21 item 9 fixes it, and the contract checks both pack orders.

**What carries over to Ahmed's real cases.**
- V1 says «بنادول خمسمية ملي» and «جيلوكاتيل جرام واحد» in words. On today's code both amounts would be dropped. So the real cases run once tonight as "before" data, and the 10× hero runs only after batch 21.
- After batch 21 merges, all of these cases run again unchanged. The result is reported next to this table, misses included.

**Lesson.** A batch that changes a prompt needs a live run of the two synthetic notes before it merges (about $0.06). Batch 20 had none.
