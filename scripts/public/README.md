# How the public copy of this repository is made

The private repository stays as it is. `make_public.sh` builds the public copy from a fresh clone of `main`. It keeps every commit, because the history itself shows how Muse Code built the product: contract → Muse build → gate → review → merge.

1. **`git filter-repo` rewrites every commit:**
   - Home and scratch paths become `<repo>`, `<scratch>` or `~`.
   - Personal account names and other personal details are replaced.
   - The build's accounts aren't named: the history names the tool behind each batch (Codex, Claude Code, Muse Code). Notes about those accounts are left out, which rewrites the 27 Oct decision entry, `CLAUDE.md`'s line on the early builds and pre-B16 grill item J8.
   - SNOMED CT ids are removed: their licence doesn't clearly allow publishing them (`evidence/decisions.md`, 30 Oct).
   - The author email becomes a GitHub noreply address.
   - The raw Muse session exports leave the history, and come back cleaned in step 2.

   The rules file and the author mapping name what they remove, so they are kept outside git, in `evidence/raw/public-kit/`.
2. **Muse's sessions come back, cleaned by `clean_muse_session.py`:** the grill sessions at their own paths, and every build session under `evidence/muse-sessions/`, gzipped and indexed by `index_sessions.py`. The cleaner removes exactly two things:
   - the encrypted reasoning blobs;
   - the session owner's personal context, their own skill list.

   Every message, tool call, file read, edit, command, result and billing record stays.
3. **`remap_shas.py` remaps the commit ids cited in the Markdown files and the batch log** to the new history. `git filter-repo` itself remaps them in commit messages.
4. **The gate before anything is public:**
   - a scan of every commit's diff, every commit message and every session for each removed item finds nothing;
   - ruff passes and the full test suite passes in the public copy.
