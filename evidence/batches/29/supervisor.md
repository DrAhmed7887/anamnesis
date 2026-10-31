# Batch 29: the Opus supervisor

## Review (31 Oct): SUPERVISOR: APPROVE
1. **Scope:** only `claims.py` (+11/−1) and the new unit test file; nothing in tests/contract, SPEC, finetune/, scripts, glimmer, meta or openweight.
2. **The trained prompt:** `_SYSTEM_PROMPT` has the same sha256 in the contract commit and the build; Glimmer's served system message and `SYSTEM_CONTENT` hash identically in both; nothing else imports the new constants; `test_finetune_data` still rebuilds the committed training data byte for byte.
3. **Spark's request:** the system message is `_SYSTEM_PROMPT`, a space, and the SPEC's sentence (210 ASCII characters, once); the guard received exactly `spark_call_estimate` of the sent body ($0.069755, up from $0.0696225).
4. **MEDIUM, not blocking:** `finetune/spark_eval.py` now sends the sentence, as intended, but the scoring predates it: `finetune/real_slice.py` keys U2 as "both amounts null", and `finetune/score.py` counts an ingredient name the transcript lacks as harm, so a Spark re-run would count the fix against Spark; the run files don't record the prompt.
5. **Other paths:** label prompts unchanged; `intake_live.py` sends Spark the new prompt and Glimmer the trained one; every `MetaClaimExtractor` uses muse-spark-1.3.
6. **LOW:** Muse's tests weaken nothing, but two restate the contract.
7. 2,703 passed, ruff clean.

**The CEO's effect on 4:** the re-measure plan was amended before any call (`remeasure-plan.md`, 15:27): the pre-registered scoring stays primary, and a second, labelled view keys U2's strength and doesn't count a brand's own ingredient as harm, for every system alike (`score_views.py`). The re-measure's output folder (`runs/spark-b29`) names the prompt.
