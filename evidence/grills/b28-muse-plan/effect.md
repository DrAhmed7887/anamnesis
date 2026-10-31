# Effect of Muse's plan grill on batch 28 (31 Oct, CEO)

Verdict: "Approve with fixes". The session's model is `muse-spark-1.3` throughout; the `contributor` count is the product's own refusal string.

| # | Muse's point | Effect |
|---|---|---|
| R1, Q1 | Same INN, another strength: the second reading wins | **Accepted.** Two models that disagree on a strength leave the pack unread: SPEC step 5b's conflict now covers strengths. Contract: `test_a_second_reading_with_another_strength_keeps_the_first`. |
| R2 | A first reading that names nothing can't block a second | **Intended, now said in the SPEC:** the second reading stands on its own, under the same label checks as any reading. |
| R3, Q3 | The dollar cap isn't exercised | **Pinned:** the second reader shares the first reader's `SessionGuard`, so `--session-usd` bounds both (SPEC and the live-script test). The U1–U8 runs use `--session-usd 0.40`. |
| R4 | An explicit budget can starve the second read | **Documented:** a caller passing an explicit budget adds `top_k` per photo; the live script does. |
| R5, Q5 | A re-photo that is still partial supersedes and stays re-requestable | **Intended:** unchanged batch 20 behaviour. |
| R6 | Crop provenance | Already pinned by byte equality. |
| R7, Q2 | No second read when the zoom is skipped at the size cap? | **The SPEC already says "or in its place";** now pinned: `test_a_pack_too_big_to_zoom_gets_its_second_read_in_the_zooms_place`. |
| R8 | `cropped=True` and an unreadable first reading are untested | **Pinned:** the fake records `cropped`, and `test_an_unreadable_first_reading_gets_a_second_read_too`. |
| Q4 | Does the brief's timeline need a new rendering? | No: it prints each step's action value, as for `zoom_read`. |

The CEO's reference build passes all 25 contract tests.
