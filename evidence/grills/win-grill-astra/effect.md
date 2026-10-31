# The win grill by GPT-6 Astra (Azure): what it changed

**What ran:** `brief.md` went to `gpt-6-astra` (2026-09-03) on Ahmed's Azure OpenAI resource, Azure for Students, at Ahmed's request on 30 Oct at 23:50 CET.
- **Usage:** 105 s; 1,716 input tokens and 4,083 output tokens, of which 2,355 were reasoning.
- **Cost:** about $0.22, at the third-party listed Azure price of $10 / $50 per 1M (`astra_usage.json`). The Azure portal's cost view is the final word.
- **What went:** project facts only. No patient data, no media and no secrets.

**Its main points, and what they mean here:**
1. **The model win doesn't show in the full product yet** (4, 3, 1 and 5 of 8; the hero all-three in 6 of 10). Fair. The README and film report full-intake results beside the fine-tune numbers, never one without the other.
2. **The provenance checks test that words occur, not how they relate** (negation, another medicine's amount, combination parts). Partly covered by existing rules: discontinued status, the cited-turn grounding, and combination amounts failing safe (U2). A short audit of these patterns before the freeze is worth an hour.
3. **Synthetic voices don't show real speech.** True. A few invented scripts read by real speakers would test the input the product claims to serve. That needs Ahmed's call, and his voice may go only to Meta's API (`docs/DATA_HANDLING.md`).
4. **"A fixed pipeline with a pause button"** (the agentic bonus). The README should show the real state transitions and who decides each one, without claiming autonomy the loop doesn't have.
5. **The open-weight model is optional, and its best evidence is off the product's path.** The fourth live column now runs both model steps on open weights (5 of 8). The film can show its trace.

**Its single most important change:** a hero case built on the clinician's pause, where an unresolved source becomes an evidence-backed finding after a re-photo, tested repeatedly, in place of the three-finding hero. That's Ahmed's call for the film.

**Its overclaim list** matches our rules. Its added wordings:
- "zero outputs scored harmful under our stated rubric in these runs";
- report the hero's registered 0 of 10 beside the 6 of 10;
- "five tested notes returned byte-identical replies", not "serving matches evaluation";
- name the reviewers as an Opus supervisor and a fresh Muse session, not independent validation.
