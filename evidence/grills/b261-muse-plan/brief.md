# Batch 26.1 design: the Fireworks label reader asks for low reasoning effort

You are planning, not building. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, and use no API key;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The plan is done ONLY when your reply has the four sections in §4, and every point cites a file and line you opened in this session.

## 2. What happened (30 Oct, live)
- **The live column timed out.** `scripts/intake_live.py --reader fireworks` reads pack crops with Muse Spark Open on Fireworks, through `OpenWeightLabelReader` (`anamnesis/providers/openweight.py`). In a live column of 8 intakes, 16 of 18 reads timed out at the client's 60 s limit.
- **A longer timeout doesn't help.** One read with a 180 s limit was dropped by Fireworks with a transport error at about 62 s, and its retry succeeded in 52 s.
- **The cause is the reasoning effort.** `MetaLabelReader` (Spark 1.3, `anamnesis/providers/meta.py`:296) sends `"reasoning_effort": "low"`, but `OpenWeightLabelReader` sends no reasoning effort. `docs/muse/muse-spark-open.md`:34 says Spark Open's default is `xhigh` and that it reasons long by default.
- **The test:** with `"reasoning_effort": "low"` added, and everything else unchanged, three reads on Fireworks took 19.2, 24.4 and 16.5 s at the 60 s limit. All three were readable and correct.

## 3. The CEO's draft (challenge it)
1. **The option:** `OpenWeightLabelReader` gains `reasoning_effort: str | None = None`.
   - None, the default, sends the request exactly as today, so batch 22's comparison (`scripts/reader_eval.py`) stays as it ran.
   - A value adds `"reasoning_effort": <value>` to the body and changes nothing else.
   - The values Meta documents are `low`, `medium`, `high` and `xhigh`; anything else raises `ValueError`.
2. **`scripts/intake_live.py`:** `--reader fireworks` builds its reader with `reasoning_effort="low"`, the effort Spark 1.3's reader asks for. `--reader baseten` stays at None, because Baseten is barred and its support for the field isn't known.
3. **The timeout stays at 60 s,** and `PRESETS` doesn't change.

## 4. Reply
1. **Verdict on the draft:** one line.
2. **Risks:** numbered, each with file:line and what to do. For instance: does the estimate (`spark_call_estimate`) change, does any test pin the body, and what does the label reader's retry do with a reply cut short.
3. **Tests the contract should pin:** a list. The CEO writes them; you don't.
4. **Open questions for the CEO.**

Keep it under 500 words.
