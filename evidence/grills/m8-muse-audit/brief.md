Before any other work, pin this objective as your session goal with your goal tool. Close it only when its check passes: **the audit is done ONLY when your reply has all six sections below, every finding cites a file and line you opened in this session, and no finding repeats one already recorded in an `evidence/grills/*/effect.md`.**

You are a worker in this run, not the main agent. **Skip any session-continuity steps:** don't read `RECENT.md` or anything under `~/.claude`, and don't write a session summary. Read only files inside this repository.

# Anamnesis: what did we miss? An audit by Muse Code before the feature freeze

**What Anamnesis is:**
- **The product:** a pre-visit medication intake agent, built for the Meta Global AI Developer Hackathon. The patient sends a voice note and photos of their medicine packs. The clinician gets a one-page brief: what the patient said beside what the pack prints, with every finding linked to its audio turn and image region.
- **Meta's models in the product:** Muse Voice Transcribe, SAM 3.1 and Muse Spark 1.3, which picks the medicines out of the transcript and reads each label.
- **Open weights:** Muse Spark Open has been run in a comparison, and once as the intake's label reader (`scripts/intake_live.py --reader baseten`).
- **Who built it:** Muse Code, you, wrote the product code in `anamnesis/` from batch 16 on. You built it from a spec (`SPEC.md`) and contract tests (`tests/contract/`) written by Claude Code. A separate Claude Opus reviewer checked each batch, and Gemini 4 checked the milestones.
- **Dates:** the feature freeze is Sat 31 Oct, 23:59 CET. After it, only fixes for release-blocking problems go in. The submission is Wed 4 Nov.

**Your job: find what we missed.** Don't report what is already known. Read every `evidence/grills/*/effect.md` first, starting with `evidence/grills/m7-pre-freeze/effect.md`. Skip anything they already record, unless you can show that a decision there is wrong.

## 1. Plan first
Before you open any code, write your plan as a numbered list: what you will check, in what order, and how you will know each check is done. Then follow it. When you change the plan, say so in one line ("Plan change: …") with the reason.

## 2. What "missed" means here
Check these, in this order:
1. **The demo path that hasn't run live yet.** Follow `scripts/intake_live.py` end to end for what is still untested:
   - a real human voice (every voice so far is macOS text-to-speech);
   - several photos of real packs in one intake;
   - an unreadable photo and its re-photo (`anamnesis/review.py`, `add_photo`).

   What breaks first: timeouts, the call budget, Arabic, pairing across photos?
2. **The spec against the code.** Look for a rule in `SPEC.md` that no contract test pins, or code that does more or less than `SPEC.md` says.
3. **Safety.** Look for any of these:
   - text that reaches the brief or the patient outside the fixed templates (`anamnesis/schema/templates.py`);
   - a model call that isn't charged to the ledger (`anamnesis/providers/spend.py`);
   - a `*-contributor` model id that isn't refused;
   - a photo that could reach a provider `docs/DATA_HANDLING.md` doesn't allow.
4. **What a judge would expect and not find.** The judging looks at technical execution, use of Meta's models and tools, real-world impact, originality and the demo. Read the README draft and the claims table on the branch `judge/claims-video`, with `git show judge/claims-video:README.md` and `git show judge/claims-video:docs/CLAIMS.md`. What is missing that this repository could still show by Saturday?

## 3. Rules
- **Read-only.** Don't create, edit, move or delete any file. No git commits, branches or pushes. No network calls, API keys or installs.
- **Never open `evidence/raw/`,** which holds media and raw logs, or anything outside this repository.
- **What you may run:**
  - `git log`, `git show` and `git grep`;
  - the tests offline, only if `.venv/bin/python` exists where you are working: `.venv/bin/python -m pytest -q` (about 15 s for all) or one file, and `.venv/bin/ruff check .`. Don't install anything to get them; if they're missing, read the tests instead.
- **A finding needs evidence:** the file and line you opened, and for a bug, the exact input that shows it.

## 4. Your reply, in six sections
1. **Goal:** the objective as you pinned it.
2. **Plan:** the list exactly as you first wrote it, then each change with its reason.
3. **Steps:** one line per step, with what you opened or ran and what you learned.
4. **Findings:** a table of at most 12 rows, most severe first: `# | severity (blocker/major/minor) | area (1–4) | evidence (file:line, or the exact input) | what is missing or wrong | the smallest fix`. Include only findings that no `effect.md` already records.
5. **Checked and fine:** one line for each area where you found nothing new, saying what you checked.
6. **How you reached the goal:** did your plan hold? What did you drop, and why? What couldn't you check from inside this repository?

End with one line, exactly: `AUDIT: N findings (B blockers, M majors)`.
