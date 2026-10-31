muse: workspace root: <repo>/.muse/worktrees/20261031-d634 (cwd default)
muse: warning: rules file at <repo>/CLAUDE.md exists, but the workspace is untrusted, so it is skipped for this session; restart with --trust-workspace to load project rules
muse: Agent delegation: auto unavailable: workspace is untrusted.
**Verdict:** Build matches SPEC and contract; no fail-open crash, only narrow fuzzy and minor over-skips.

**Findings:**

1. **Medium — fuzzy drops SPEC's short-name blocks.** `SPEC.md:257` requires turn word ≥4 letters; diff `relations.py` `fuzzy_words={... if len(word)>=4}` also requires name word ≥4. A 1–3 letter alias/INN (e.g. `d`) never blocks past/split, dropping where SPEC keeps. Fix: keep `len(token)>=4`, drop name-word length filter.
2. **Low — walk skips non-units.** `SPEC.md:252` walks over “unit words”; `SPEC.md:239` lists `ملي/مللي/ميكرو` separately. Diff `_UNIT_SKIP=...|_OPEN_UNIT` plus pair fragments (`لتر`,`دوليه`) skips them, so `Panadol ملي five` walks to Panadol and drops; SPEC stops at `ملي` and keeps. Fix: walk only `_UNIT_SINGLE`/`_UNIT_TWO` units.
3. **Low — glued names have no SPEC basis.** `SPEC.md:255` matches whole tokens; diff `_names_to_token_lists` adds `norm.replace(" ","")`. `PanadolExtra` then drops for Panadol where SPEC keeps. Fix: remove glued variant.
4. **Low — `ten mg, a day` kept as non-daily.** `SPEC.md:257` says directly followed; diff `_is_daily_total` requires same clause, so comma breaks daily and split total is kept. Fix: allow one clause break or pin SPEC.
5. **Info — 4-letter reach is huge.** `SPEC.md:257` + diff fuzzy `token.startswith(word) or word.startswith(token)` over every catalogue brand/alias/INN means e.g. Spanish `para` matches `paracetamol` and blocks any splitter/past in its clause, only ever keeping. Per SPEC, but document it.

**What you checked and found fine:**
- Word lists match SPEC: negation/DON (`SPEC.md:242`), mg/mcg/g/ml/iu + open (`SPEC.md:243-250`), counts + `sobre` + ES/DE dose (`SPEC.md:251`), joiners/of (`SPEC.md:252`), past (`SPEC.md:256`), per-day (`SPEC.md:257`), clause ends (`SPEC.md:240`).
- SPEC-keeps cases keep: bare number, open `ملي`, negation ≥3 away, `before breakfast`, `once/twice a day` (not directly followed).
- `claims.py` diff sits between value check and drop-other rule (`anamnesis/providers/claims.py:350-371`), so dropped relation nulls the other; `discontinued` only skips past.
- No change to `stated_amounts`, labels, `regimen`, reconciler; `TypeError/ValueError` still become malformed, no new crash type.
