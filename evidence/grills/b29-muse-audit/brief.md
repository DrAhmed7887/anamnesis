# Batch 29 audit: double-check another Muse session's build, read-only

You are auditing code that another Muse Code session just wrote for batch 29 of Anamnesis. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, use no API key, and run no `modal` command;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The audit is done ONLY when your reply has the three sections in §3, and every finding cites a file and line you opened, or a line of the diff below.

## 2. What the code must do
SPEC.md §2, "Prompts", the bullet "Spark's claim prompt adds one sentence (batch 29)": open it. `MetaClaimExtractor` sends `_SYSTEM_PROMPT` plus a space plus the combination sentence, word for word; `_SYSTEM_PROMPT` itself, the tuned Glimmer's served prompt (`anamnesis/providers/glimmer.py`) and the fine-tune's prompt (`finetune/common.py`) don't change. The contract is `tests/contract/test_b29_combination_prompt.py`, and the build passes it. Look for anything that sends the sentence to Glimmer or the fine-tune, any change to the pre-call estimate's correctness, and anything else that changed.

## 3. Reply
1. **Verdict:** one line.
2. **Findings:** numbered, each with severity, file:line, the evidence and a fix.
3. **What you checked and found fine:** a short list.

Keep it under 300 words.

## The build: `git diff HEAD` (uncommitted in the batch worktree; this copy of the repository is at the contract commit)
```diff
diff --git a/anamnesis/providers/claims.py b/anamnesis/providers/claims.py
index 023df20..cdbfa2e 100644
--- a/anamnesis/providers/claims.py
+++ b/anamnesis/providers/claims.py
@@ -46,6 +46,16 @@ _SYSTEM_PROMPT = (
     "Give no medical advice. Only report what the patient said."
 )
 
+_COMBINATION_SENTENCE = (
+    "A combination product said with one amount per ingredient, such as "
+    "'Augmentin 875 and 125 milligrams', is its strength: one ingredient per amount, "
+    "in the order said, each named for the ingredient it belongs to."
+)
+"""The batch 29 sentence, SPEC §2 word for word; only Spark 1.3's claim prompt gets it."""
+
+_SPARK_CLAIM_PROMPT = f"{_SYSTEM_PROMPT} {_COMBINATION_SENTENCE}"
+"""What MetaClaimExtractor sends: the trained prompt plus the combination sentence."""
+
 _AMOUNT_SCHEMA: dict[str, Any] = {
     "type": "object",
     "additionalProperties": False,
@@ -452,7 +462,7 @@ class MetaClaimExtractor:
             "reasoning_effort": "low",
             "max_tokens": 16000,
             "messages": [
-                {"role": "system", "content": _SYSTEM_PROMPT},
+                {"role": "system", "content": _SPARK_CLAIM_PROMPT},
                 {"role": "user", "content": transcript},
             ],
             "response_format": {"type": "json_schema", "json_schema": {
diff --git a/tests/unit/test_b29_extra.py b/tests/unit/test_b29_extra.py
new file mode 100644
index 0000000..b4bd390
--- /dev/null
+++ b/tests/unit/test_b29_extra.py
@@ -0,0 +1,56 @@
+"""Batch 29 gaps the contract leaves: the sentence constant, the join, and who gets what prompt."""
+
+import json
+from decimal import Decimal
+
+import httpx
+
+from anamnesis.providers import SpendGuard
+from anamnesis.providers.claims import (
+    _COMBINATION_SENTENCE,
+    _SPARK_CLAIM_PROMPT,
+    _SYSTEM_PROMPT,
+    MetaClaimExtractor,
+)
+from anamnesis.providers.glimmer import _SYSTEM_PROMPT as GLIMMER_PROMPT
+from anamnesis.providers.meta import MetaClient
+from anamnesis.schema import AudioTurn
+from finetune.common import SYSTEM_CONTENT
+
+TURNS = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=2500,
+                  transcript="I take one tablet every morning.")]
+
+
+def test_the_combination_sentence_is_the_specs_word_for_word():
+    assert _COMBINATION_SENTENCE == (
+        "A combination product said with one amount per ingredient, such as "
+        "'Augmentin 875 and 125 milligrams', is its strength: one ingredient per amount, "
+        "in the order said, each named for the ingredient it belongs to.")
+
+
+def test_sparks_claim_prompt_is_the_trained_prompt_plus_one_space_plus_the_sentence():
+    assert _SPARK_CLAIM_PROMPT == f"{_SYSTEM_PROMPT} {_COMBINATION_SENTENCE}"
+    assert _SPARK_CLAIM_PROMPT[len(_SYSTEM_PROMPT)] == " "
+    assert "combination product" not in _SYSTEM_PROMPT
+
+
+def test_spark_sends_sparks_claim_prompt_as_its_system_message(tmp_path):
+    sent = []
+
+    def handler(request):
+        sent.append(json.loads(request.content))
+        return httpx.Response(200, json={"id": "chat_1", "choices": [{"message": {"role": "assistant",
+                              "content": '{"claims": []}'}, "finish_reason": "stop"}],
+                              "usage": {"prompt_tokens": 900, "completion_tokens": 10}})
+
+    client = MetaClient(api_key="LLM_t_s", transport=httpx.MockTransport(handler))
+    claims, _ = MetaClaimExtractor(client, SpendGuard(tmp_path / "ledger.jsonl",
+                                                     cap_usd=Decimal(5))).extract(TURNS)
+    assert claims == []
+    assert sent[0]["messages"][0] == {"role": "system", "content": _SPARK_CLAIM_PROMPT}
+
+
+def test_glimmer_and_the_finetune_keep_the_trained_prompt_without_the_sentence():
+    assert GLIMMER_PROMPT == SYSTEM_CONTENT == f"{_SYSTEM_PROMPT}\nReasoning strength: low"
+    assert _COMBINATION_SENTENCE not in GLIMMER_PROMPT
+    assert _COMBINATION_SENTENCE not in SYSTEM_CONTENT
```
