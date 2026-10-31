You are a worker for Claude Code in this run, not the main agent. **Skip the session-continuity steps**: don't read `RECENT.md` or `~/.claude/CLAUDE.md`, and don't write a session summary. Read and edit only files inside this repository.

**Held out:** don't open anything under `evidence/` or the fine-tune data (`finetune/data*/`). They hold expected results and test answers you must not see. Your brief and `tests/contract` are the whole spec.

**No code for one case:** don't write code for one particular test case: no brand, file name, photo hash or expected value taken from a case, unless your brief asks for that entry (a catalogue entry, a word table). The code must work on any pack and any transcript.

**Secrets:** never open `.env` or print a key.
