# Batch 27.1 review: durations, "weiß nicht", and a dropped amount's tablet count (SPEC §2)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 2 rounds, planned first by a read-only Muse session and audited by a fresh one

**What the batch changes** (all in the relation checks, `anamnesis/providers/relations.py` and the hook in `claims.py`):
1. **A duration is never an amount:** with no unit word after a number, a plural duration word right after it ("five years", «خمس سنين», "two weeks") makes it a duration, so it neither grounds an amount nor splits a daily total. "ten a day" stays a daily amount; singular time words («ساعة ما», «يوم ويوم لا», "10/day") are not durations.
2. **German "weiß nicht":** a negation right after "weiß" doesn't negate the number. After any other word of knowing it still does ("sicher nicht fünf" is "certainly not five").
3. **A dropped amount takes an unbacked tablet count with it:** when the relation checks drop a claim's amount, its `units_per_intake` goes too, unless a count about this claim backs it (rule 3, not negated, not another medicine's, not past).

**Why:** the Opus supervisor's two fail-safe findings on batch 27 (a duration split "ten a day for five years"; "ich weiß nicht fünf" dropped the 5), and one live finding: on trap J the tuned Glimmer wrote a 10 mg intake and five tablets; batch 27 dropped the 10, and the five gave a false `strength_mismatch`.

**Who did what:**
- **The CEO** wrote the SPEC lines, the contract and a reference build, and measured it before Muse saw it.
- **Muse planned first** (`evidence/grills/b271-muse-plan/`): "Accept with the fixes below", all already in the design.
- **Muse built it in two rounds.** Round 1 followed the SPEC; the fresh Muse audit (`evidence/grills/b271-muse-audit/`) found the tablet-count backing ignored negation and another medicine, and the Opus supervisor (`supervisor.md`) found the "weiß nicht" exception, as the SPEC first worded it for every word of knowing, re-opened traps A and H's false `match`, and that singular time words swallowed doses. Round 2 narrowed all three.

**Measured on the final build:** it matches the CEO's reference on all 1,452 scored fine-tune replies; against batch 27, none loses a fully-right score and two base-Glimmer notes change (one wrong tablet count gone, one right count of 2 with no count word gone, fail-closed); 0 of 164 saved live claims change; the ten traps stay safe.

**The gate:** pass, 2,694 tests, ruff clean, contract untouched since the latest `test(contract): batch 27.1` (`gate.json`).

**Cost:** Muse $2.93 in all: plan $0.18, round 1 $1.02, round 2 $0.73, audit $0.30, plus the supervisor's review (Claude, no Meta credit). The rounds are in `evidence/spend/muse_ledger.jsonl`; the grills are in neither ledger.

**The Opus supervisor's round 2 re-check:** APPROVE (`supervisor.md`): traps A and H and every "certainly not" variant end as `insufficient_information`, the durations and the tablet-count backing behave as the SPEC says, and nothing of batch 27 changed (8,000 multi-claim fuzz cases).

**Found, not fixed here (fails safe):** Arabic puts a singular noun after numbers from 11, so «عشرين سنة» (twenty years) can still split a daily amount and drop it.

Verdict: PASS
