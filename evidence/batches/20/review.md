# Batch 20 review: amounts must be stated, and the clinician signs off after an optional photo request (SPEC §2, §7, §8)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 2 rounds, goal pinned with its goal tool in each

**Who did what:**
- Claude Code (Opus 5.5), as CEO, wrote the SPEC sections, the brief, the contract and the round-2 brief. The two ideas came from Meta's legal-agent workshop of 27 Oct (`github.com/meta-models/legal-agent-workshop`):
  - a quote is refused unless it is on the page;
  - a run pauses for a person, resumes for one item, and is final only after sign-off.
- Before Muse started each round, the CEO ran the contract against a throwaway reference build: the whole suite passed (747, then 889). On the merged 19.1 code, the existing suite with the amended b16 passed (707), and the new contract was red only on the two missing modules.
- Muse wrote all the code.
- The docs-only commit `2f0a45d` on this branch belongs to another session; it is also on main as `73f3071` and is not part of this review.

**Contract:** three commits.
- `22a49a0`: the contract itself. It amends `test_b16_model_replies.py` so its two number tests cite a turn that says the number, as the batch 18 contract commit amended b12, b14 and b15.5.
- `658f097`: wraps an import of the CEO's that tripped ruff I001. In round 1, Muse had widened the contract folder's lint ignore in `pyproject.toml` to get past it; the CEO reverted that, since the fault was the contract's.
- `7800b69`: round 2.

**Gate:** pass, 893 tests (707 before). The contract lock held in both rounds.

**Goal (`goal.md`):**
- Round 1: `create_goal` with the batch's check, closed complete; 85 of 86 main-agent model calls were under it.
- Round 2: pinned, and the goal reminder's last check found every condition met, but the goal was **never closed** with its tool. The gate is the check that counts, and it passed.

**Muse cost:** **$3.84286** for the batch, priced from Muse's own billing records (`usage.json`):
- round 1: $2.85737, from 12,652,211 input tokens (12,154,174 cached) and 96,869 output;
- round 2: $0.98549, from 3,820,200 input (3,606,849 cached) and 41,830 output.

Verdict: PASS (supervisor APPROVE, round 2)

## What changed
- **Amounts must be stated.** A claim amount must be stated in a turn the claim cites, and a label amount must be printed in `label_text`; otherwise it is dropped like an amount that doesn't parse, so an invented number can't decide a finding. "Stated" covers:
  - digits;
  - English and Egyptian/MSA Arabic number words, with runs ("two hundred and fifty", "ميتين وخمسين"), halves and `point` decimals.

  The live notes of 27 Oct keep their 5 mg and 50 mg ("five milligrams", "خمسة ملي جرام", "خمسين"). Both prompts now say never convert units.
- **A run of number words ends at punctuation**, so "five, two" never states 7 (supervisor #5). The digit pass is unchanged: a 200,000-case fuzz found no difference.
- **A malformed label reply stays malformed.** A non-string `label_text` was crashing the whole intake after the call was charged (supervisor #1); it is again a retryable malformed reply.
- **Clinician review.** A brief is a draft until a clinician approves it. Before that, the clinician can ask the patient for one new photo of an unreadable pack or of a medicine they mentioned but didn't photograph:
  - only that photo goes to a model, with its own call budget, and the steps, calls and spend carry on from the report;
  - the old pack is replaced only when the new photo gave a reading;
  - a review and a brief are bound to the report's `intake_id`, so neither a review of another report (supervisor #2) nor other media are accepted.
- **On the brief:** the review status in the header, "A new photo has been requested from the patient." on the finding it targets, "Replaced by a newer photo." on a replaced pack, and a photos-requested count in coverage.

## Follow-ups (none blocking)
- **Next contract:** add the Unicode line breaks (` `, ` `, `\x85`, `\v`, `\f`) and the ellipsis `…` to the run breaks in SPEC §2 (supervisor round 2 #7; fails open only on characters a transcript is unlikely to contain).
- **Later:** one shared "prepare, read, zoom, observe" helper for `run_intake` and `add_photo` (supervisor #6), once `run_intake` can change safely.
- **Known limits written into SPEC §2:**
  - only an amount's value is checked, not its unit;
  - regimen numbers aren't checked;
  - Spanish number words and digit-group speech fail closed to `insufficient_information`.
- **Demo:** a script that sends the photo request and answers it with a re-photo, for the video. `scripts/` is the CEO's, so the CEO writes it.
