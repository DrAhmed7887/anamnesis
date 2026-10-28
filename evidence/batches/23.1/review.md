# Batch 23.1 review: the follow-ups to batch 23's last review and its Gemini 4 check (SPEC §2, §5)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 1 round, goal pinned with its goal tool

**What the batch changes:**
- **The tablet-word carve-out** in the refusal's before-form now applies only with `in` or `في`, the connectors every dissolving line uses. After `/` or `per`, a tablet word excuses nothing, so "Calpol 250 mg tab/5 ml" read per tablet drops. "Vitamin C 1000 mg effervescent tablet, dissolve in 200 ml" keeps its strength. This was the supervisor's batch 23 round 9 #1, and the Gemini 4 check's #2.
- **The always-counts form** allows any number of bracket groups before the connector, as SPEC already said (Gemini #4).
- **The per-1-ml print** takes the plural spellings (Gemini #4).
- **The nominative colloquial dual** `معلقتان` is pinned in the contract (Gemini #3). The code already handled it.
- **`SpendGuard.charge_estimate`** refuses a `*-contributor` model id before anything reaches the ledger (Gemini #6, defense in depth). `ProviderTrace` already refused one, so `charge` was covered.

**Who did what:**
- **Claude Code (Opus 5.5), as CEO,** wrote the SPEC lines, the brief and `test_b23_1_followups.py` on 28 Oct. It proved them with a throwaway reference build: 1,407 contract tests pass and 6 of 6 mutants are caught (`reference.md`).
- **Muse** wrote the code in `providers/spark.py` and `providers/spend.py`, and `tests/unit/test_b23_1_extra.py`.
- **The CEO's differential check:** Muse's code and the reference give the same answer on all 940 checks: 235 labels × 4 `per` values.
- **The independent Opus supervisor** reviewed it: APPROVE, with nothing to change (`supervisor.md`).

**What is still open, on purpose:**
- "Paracetamol 250 mg = one tablet in each 5 ml" keeps a per-tablet reading. It uses `in`, and no pack prints it. The supervisor accepted it in batch 23 round 9.

**Privacy:** the Muse export carries no personal names and shows no reads of `evidence/raw/`. `muse-session.md` lists every tool call by its path or command only.

**Spend:** Muse **$0.56952** (estimated). No live calls.

**Next:** merge. Then the pre-freeze Gemini 4 check across batches 21–23.1 on Sat.

Verdict: PASS
