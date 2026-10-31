# Batch 28, round 2: a second reading must keep everything the first had

Round 1 passed the gate, and the code does what SPEC §4 step 5b said. A fresh Muse audit and the Opus supervisor found that the step itself was too loose. Two models that disagree about the formulation could produce a false `match`. For example, a step-5 reading that was partial, bisoprolol 5 mg modified release, was replaced by a readable bisoprolol 5 mg immediate-release reading. And a readable second reading that named nothing could erase what the first had read.

The SPEC now settles it (§4 step 5b, the bullet that begins "the second reading must keep everything"), and new contract tests pin it in `tests/contract/test_b28_second_reader.py`. The contract commit is the latest `test(contract): batch 28`.

## Do, in `anamnesis/agent/loop.py`'s second-read check
1. **Knows less:** when the step-5 reading names ingredients (canonical INNs of its strength, or else of `inn`), the second must name the same set: none is a conflict too. When the step-5 reading gives a strength, the second must give the same one.
2. **`per`:** the strength comparison includes what the strength is per (tablet, capsule, ml or dose).
3. **Release:** where both readings give a release other than `unknown`, they must match. A step-5 `unknown` can still be completed by the second reading.
4. **Salt:** where both readings give an ingredient's salt (an amount's `salt`, or the salt in `inn`; `anamnesis/schema/medication.py` splits them), the salts must match for that ingredient.

Any of these failing logs the existing `conflict: kept the first reading` step and keeps the step-5 reading. Update your own tests where they pinned the old behaviour (for example "release ignored"). Everything else in the hard rules of `briefs/28.md` still holds.

## Done when
`.venv/bin/ruff check .` and `.venv/bin/python -m pytest -q` both pass from the repo root, and `git status --porcelain tests/contract` prints nothing. Reply with a short report and the final test count.
