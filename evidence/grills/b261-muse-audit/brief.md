# Batch 26.1 audit: double-check another Muse session's build, read-only

You are auditing code that another Muse Code session just wrote for batch 26.1 of Anamnesis. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, use no API key, and run no `modal` command;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The audit is done ONLY when your reply has the three sections in §3, and every finding cites a file and line you opened, or a line of the diff below.

## 2. What the code must do
SPEC.md §4, "Reasoning effort for the open-weight reader (batch 26.1)": open it in the repository.
- `OpenWeightLabelReader` gains an optional `reasoning_effort`. None sends today's request; one of `low`, `medium`, `high` and `xhigh` adds only that field; anything else raises `ValueError` before any call.
- `--reader fireworks` asks for `low`, and Baseten for None.

The contract is `tests/contract/test_b261_reasoning.py`, and the build passes it. Look for what it doesn't catch: batch 22's comparison path (`scripts/reader_eval.py`) changing, the estimate, the retry and length-stop paths, or batch 26's code changing.

## 3. Reply
1. **Verdict:** one line.
2. **Findings:** numbered, each with severity, file:line, the evidence and a fix.
3. **What you checked and found fine:** a short list.

Keep it under 400 words.

## The build: `git diff HEAD` (uncommitted in the batch worktree; this copy of the repository is at the contract commit)
```diff
diff --git a/anamnesis/providers/openweight.py b/anamnesis/providers/openweight.py
index 580bb2b..76ed43d 100644
--- a/anamnesis/providers/openweight.py
+++ b/anamnesis/providers/openweight.py
@@ -58,14 +58,18 @@ class OpenWeightClient(MetaClient):
 
 class OpenWeightLabelReader:
     def __init__(self, client: OpenWeightClient, guard: SpendGuard, *, model: str,
-                 price_key: str, json_mode: bool) -> None:
+                 price_key: str, json_mode: bool,
+                 reasoning_effort: str | None = None) -> None:
         if "-contributor" in model.strip().casefold():
             raise ValueError("contributor models are not permitted")
+        if reasoning_effort is not None and reasoning_effort not in ("low", "medium", "high", "xhigh"):
+            raise ValueError("reasoning_effort must be None or one of low, medium, high, xhigh")
         self.client = client
         self.guard = guard
         self.model = model
         self.price_key = price_key
         self.json_mode = json_mode
+        self.reasoning_effort = reasoning_effort
 
     def read(self, image: bytes, region: ImageRegion, *, mime: str,
              cropped: bool = False) -> tuple[LabelReading, ProviderTrace]:
@@ -95,6 +99,8 @@ class OpenWeightLabelReader:
             body["response_format"] = {"type": "json_schema", "json_schema": {
                 "name": "label_reading", "strict": True, "schema": LABEL_SCHEMA,
             }}
+        if self.reasoning_effort is not None:
+            body["reasoning_effort"] = self.reasoning_effort
 
         estimate = spark_call_estimate({**body, "model": self.price_key})
 
diff --git a/scripts/intake_live.py b/scripts/intake_live.py
index 2694b4a..61f704a 100644
--- a/scripts/intake_live.py
+++ b/scripts/intake_live.py
@@ -7,7 +7,8 @@
 With no --case it runs the two synthetic notes (media: scripts/make_synthetic_media.sh). With --case it runs
 one staged case (evidence/batches/21/manifest.md): that voice note and those photos, in order, --repeat times.
 --reader baseten or --reader fireworks makes Meta's open-weight Muse Spark Open on Baseten or Fireworks the
-label reader (keys: BASETEN_API_KEY, FIREWORKS_API_KEY); everything else stays on Meta. It refuses any photo
+label reader (keys: BASETEN_API_KEY, FIREWORKS_API_KEY); everything else stays on Meta. On Fireworks it asks
+for low reasoning effort, as Spark 1.3's reader does. It refuses any photo
 outside the public folders that docs/DATA_HANDLING.md lets go to Baseten or Fireworks, before the first call.
 --extractor glimmer makes the tuned Glimmer on Modal the claim extractor (token: MODAL_PROXY_TOKEN, URL from
 --glimmer-url or GLIMMER_URL); it refuses any voice note but the synthetic ones under
@@ -129,7 +130,8 @@ def intake(run: Run, name: str, audio: bytes, images: list[tuple[bytes, str]],
     else:
         provider = run.open_client.provider
         reader = OpenWeightLabelReader(run.open_client, guard, model=PRESETS[provider]["model"],
-                                       price_key=f"muse-spark-open@{provider}", json_mode=False)
+                                       price_key=f"muse-spark-open@{provider}", json_mode=False,
+                                       reasoning_effort="low" if provider == "fireworks" else None)
     start = time.monotonic()
     report = run_intake(
         audio, images,
diff --git a/tests/unit/test_b261_extra.py b/tests/unit/test_b261_extra.py
new file mode 100644
index 0000000..0beb3b2
--- /dev/null
+++ b/tests/unit/test_b261_extra.py
@@ -0,0 +1,80 @@
+"""Batch 26.1 gaps the contract leaves: non-string efforts, the stored default,
+the effort under JSON mode and on a retry, and the live script's docstring."""
+
+import ast
+import json
+from decimal import Decimal
+from pathlib import Path
+
+import httpx
+import pytest
+
+from anamnesis.providers import SpendGuard
+from anamnesis.providers.openweight import PRESETS, OpenWeightClient, OpenWeightLabelReader
+from anamnesis.schema import ImageRegion
+
+ROOT = Path(__file__).resolve().parents[2]
+REGION = ImageRegion(region_id="r0", image_sha256="0" * 64, object_id=0,
+                     x1=1, y1=2, x2=10, y2=20, frame_w=100, frame_h=100)
+PHOTO = b"not a real photo, just bytes for the mocked endpoint"
+REPLY = {"label_text": "Widget 5 mg", "readability": "readable"}
+
+
+def _reply(content: str) -> httpx.Response:
+    return httpx.Response(200, json={"id": "cmpl-1", "choices": [{"message": {"content": content},
+                                                                   "finish_reason": "stop"}],
+                                     "usage": {"prompt_tokens": 1000, "completion_tokens": 500}})
+
+
+def _reader(tmp_path: Path, replies: list, json_mode: bool = False, **options):
+    sent: list[dict] = []
+
+    def handler(request: httpx.Request) -> httpx.Response:
+        sent.append(json.loads(request.content))
+        return replies[min(len(sent), len(replies)) - 1]
+
+    client = OpenWeightClient(api_key="fw_secret", base_url=PRESETS["fireworks"]["base_url"],
+                              provider="fireworks", transport=httpx.MockTransport(handler))
+    guard = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal(5))
+    reader = OpenWeightLabelReader(client, guard, model=PRESETS["fireworks"]["model"],
+                                   price_key="muse-spark-open@fireworks", json_mode=json_mode,
+                                   **options)
+    return reader, sent
+
+
+def test_the_default_effort_is_none_and_is_stored(tmp_path):
+    reader, _ = _reader(tmp_path, [_reply(json.dumps(REPLY))])
+    assert reader.reasoning_effort is None
+
+
+def test_a_documented_effort_is_stored(tmp_path):
+    reader, _ = _reader(tmp_path, [_reply(json.dumps(REPLY))], reasoning_effort="medium")
+    assert reader.reasoning_effort == "medium"
+
+
+@pytest.mark.parametrize("effort", [True, 0.5, b"low", ["low"], {"effort": "low"}, " low", "low ", "Low"])
+def test_near_misses_and_non_strings_are_refused_at_construction(tmp_path, effort):
+    with pytest.raises(ValueError):
+        _reader(tmp_path, [_reply(json.dumps(REPLY))], reasoning_effort=effort)
+
+
+def test_the_effort_is_added_under_json_mode_too_and_only_it(tmp_path):
+    plain, plain_sent = _reader(tmp_path / "a", [_reply(json.dumps(REPLY))], json_mode=True)
+    high, high_sent = _reader(tmp_path / "b", [_reply(json.dumps(REPLY))], json_mode=True,
+                              reasoning_effort="xhigh")
+    plain.read(PHOTO, REGION, mime="image/png")
+    high.read(PHOTO, REGION, mime="image/png")
+    assert high_sent[0] == {**plain_sent[0], "reasoning_effort": "xhigh"}
+
+
+def test_the_retry_request_carries_the_effort_as_well(tmp_path):
+    reader, sent = _reader(tmp_path, [_reply("not json"), _reply(json.dumps(REPLY))],
+                           reasoning_effort="low")
+    reader.read(PHOTO, REGION, mime="image/png")
+    assert [body.get("reasoning_effort") for body in sent] == ["low", "low"]
+
+
+def test_the_live_scripts_docstring_says_fireworks_asks_for_low_effort():
+    module = ast.parse((ROOT / "scripts/intake_live.py").read_text(encoding="utf-8"))
+    docstring = ast.get_docstring(module) or ""
+    assert "low reasoning effort" in docstring
```
