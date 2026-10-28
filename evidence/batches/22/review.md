# Batch 22 review: an open-weight label reader for a zero-shot comparison with Spark 1.3, and one-word amounts (SPEC §2, §4)

Built-by: Muse Code (muse-spark-1.3, contributor mode off), 2 rounds, goal pinned with its goal tool in each

**Who did what:**
- Claude Code (Opus 5.5), as CEO, wrote the SPEC lines, the brief and the contract on 28 Oct, after Ahmed added the zero-shot comparison with Muse Spark Open:
  - `test_b22_openweight.py` and `test_b22_number_words.py`;
  - one case changed in `test_b16_model_replies.py` (`"two"` now parses as 2);
  - `test_b22_round2.py` after the round 1 review.
- Before each round, the CEO proved the contract with a throwaway reference build: 1,056 passed, then 1,115. Round 2's pins were checked against four mutants (`reference.md`).
- Muse wrote all the code: `anamnesis/providers/openweight.py`, the two prices in `base.py`, the number-word fallback in `numbers.py`, and its unit tests.
- An independent Opus supervisor reviewed both rounds: CHANGES, then APPROVE (`supervisor.md`).

**What the review rounds found:**
- **Round 1:** a word amount with a sign or comparator parsed as exact. "I take Concor, less than five milligrams" (`"<five"`) became 5 mg and reached **`match`**, a false agreement. «خُمس» (a fifth) parsed as 5. Also:
  - a contributor id was refused only as an exact suffix;
  - the reader's own errors named "spark", so a comparison would have counted them as Spark 1.3's;
  - four mutants survived the suite.
- **Round 2:** all fixed and pinned, with 40 new contract cases. The supervisor then found one weak pin of the CEO's: the parse-error key test could not fail, and the reason the CEO recorded for that was wrong. The CEO changed the pin's input after round 2, and it now catches the mutant. No code change was needed.
- **The CEO's errors:** both round 1 bugs came from the brief's own wording. Item 5 said to normalise any one-token text with `catalogue.normalise` before matching it, which is what stripped the "<" and the damma. Item 3 said "a `model` ending in `-contributor`". Muse built both exactly as written.

**Privacy:** the round 1 and 2 Muse exports carry no personal names, and no reads of `evidence/raw/`.

**Spend:** Muse $0.80760 and $0.52297, **$1.33057 for the batch** (estimated). No live calls.

**Follow-ups, after the freeze:**
- The loop strips a salt only when the full name is in `INN_ALIASES`. "Rosuvastatin calcium", "terbinafine hydrochloride", "sitagliptin phosphate", "pseudoephedrine sulfate" and "candesartan cilexetil" stay as written, so a pack read with its salt would not pair with the claim's INN. The comparison's scorer compares INNs without salt words, so it is not affected.
- `read()` in `openweight.py` copies `MetaLabelReader.read`, about 70 lines. The contract's body-equality test catches drift.
- The client's message text still says "Meta …" for Fireworks and Baseten errors. The `provider` field is right.

**Next:** commit the comparison script and the pre-registered answer keys to main before any call. Then run Spark 1.3 and Muse Spark Open on the 39 public photos, once Ahmed's Fireworks key is in the Keychain.

Verdict: PASS
