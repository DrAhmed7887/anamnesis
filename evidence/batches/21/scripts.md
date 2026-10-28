# Batch 21: what to record (fictional scripts and shot list)

Rules: `docs/DATA_HANDLING.md`.
- The patient is invented: no real history, no place names.
- Only Ahmed's voice: no other voices, no TV in the background.
- Packs only: no pharmacy labels, faces, documents or screens.
- If something slips in, retake the file. Never edit it afterwards.
- Raw files stay in `evidence/raw/media/real/` (git-ignored). Only these scripts and the expected results are committed.

## Voice notes
Record in Voice Memos, in a quiet room, with the phone about 20 cm away. Read each script as written. If a box shows another strength, change only that number, and say every amount in full: "one gram", not "a gram". Since batch 20, an amount the patient doesn't actually say is dropped.

**V1, the hero** (Egyptian Arabic, at most 20 s). It names both brands, each with a strength, and says both are taken now. The "across medicines" note comes only from what the patient says: a pack never implies use.
> السلام عليكم يا دكتور. أنا باخد بنادول خمسمية ملي، حباية واحدة لما راسي توجعني، مرتين في اليوم تقريبًا. وكمان باخد جيلوكاتيل جرام واحد لما ضهري يوجعني، مرة واحدة في اليوم.

*"Hello doctor. I take Panadol five hundred milligrams, one tablet when I have a headache, about twice a day. And I also take Gelocatil one gram when my back hurts, once a day."*

**V1b, optional** (Ahmed's call): the same note, but with one spoken strength that differs from the box, so the brief's Disagreements section has a side-by-side. It is one more thing that has to come out right in 10 of 10.
> السلام عليكم يا دكتور. أنا باخد بنادول خمسمية ملي، حباية واحدة لما راسي توجعني، مرتين في اليوم تقريبًا. وكمان باخد جيلوكاتيل ستمية وخمسين ملي لما ضهري يوجعني، مرة واحدة في اليوم.

*"… And I also take Gelocatil six hundred and fifty milligrams …"* (the box says 1 g)

**V2, rambling** (English, about 30 s; keep the hesitations):
> "Hi… um, so, my medicines. I take Panadol, the five hundred milligram one, uh, one tablet, sometimes two when it's bad. And Gelocatil, wait, is it Gelocatil? Yes, one gram, in the morning. Oh, and I used to take ibuprofen, but I stopped that last month. That's it, I think."

**V3, long** (Egyptian Arabic, about 40 s). This tests whether a long note finishes inside the claim call's 30 s timeout; the live calls of 27 Oct took 11.6 s and 13.1 s.
> باخد كونكور خمسة ملي مرة واحدة الصبح. وبيلوك زوك مية ملي، نص حباية الصبح. ونورفاسك خمسة ملي بالليل. وجلوكوفاج خمسمية ملي مرتين في اليوم مع الأكل. وليبيتور عشرين ملي بالليل. وبنادول خمسمية ملي لما أحتاجه، حوالي مرتين في الأسبوع. ووقفت الأوجمنتين الأسبوع اللي فات لما خلصت الكورس.

*"I take Concor five milligrams once in the morning. Beloc-Zok one hundred milligrams, half a tablet in the morning. Norvasc five milligrams at night. Glucophage five hundred milligrams twice a day with food. Lipitor twenty milligrams at night. Panadol five hundred milligrams when I need it, about twice a week. I stopped Augmentin last week when I finished the course."*

Checked offline on this branch: `stated_amounts` finds every spoken number above, including «خمسمية» 500, «ستمية وخمسين» 650 and «نص» 0.5.

## Photos
Use a plain table in daylight. Turn off Location for the camera if you can.

| ID | Shot | How |
|---|---|---|
| P1 | **hero** | Panadol and Gelocatil side by side, fronts up. Phone upright (portrait), straight above, about 35 cm away. Both brand names and strengths readable |
| P2 | **unreadable** | The same layout as P1, but take the Gelocatil box so its label can't be read: glare from a window or lamp, or out of focus. **Take it that way; never edit it.** Panadol stays readable |
| P3 | **re-photo** | Gelocatil alone, label facing the camera, in good light. It answers the photo request for P2 |
| P4 | **shelf** | 3–4 boxes: those two plus one or two other over-the-counter boxes. Phone sideways (landscape), with a glare stripe across one box's front |
| P5 | **blister** | One blister strip, printed foil side up, flat, about 25 cm away. It is meant to be hard to read |
| P6 | **empty** | The same table with nothing on it |
| P7 | optional | Bisoprolol and metoprolol boxes, only if you have them without a pharmacy sticker |

## Also send
For each box you photographed:
- the brand and strength printed on it;
- whether it is Egyptian or Spanish;
- which box is the blister's.

The country goes into the manifest. Scene 1 may say "two countries, two brand names" only with Ahmed's yes.
