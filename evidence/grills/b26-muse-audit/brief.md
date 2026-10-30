# Batch 26 audit: double-check another Muse session's build, read-only

You are auditing code that another Muse Code session just wrote for batch 26 of Anamnesis. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, use no API key, and run no `modal` command;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The audit is done ONLY when your reply has the four sections in §4, and every finding cites a file and line you opened in this session, or a line of the diff below.

## 2. What the code must do
- **The specification** is SPEC.md §4, "Open-weight claim extractor and the Fireworks reader (batch 26)". Open it in the repository.
- **The contract tests** are `tests/contract/test_b26_open_weight_path.py`, and the build passes them. Look for what they don't catch.
- **The server** must reuse the eval's engine and decoding unchanged: `evaluate` and `_two_passes` in `finetune/modal_glimmer.py`. Five served replies already matched the eval's replies byte for byte, on a reference server written separately.

## 3. What to look for
- any difference between the served engine or decoding and `evaluate`/`_two_passes`;
- a path that fails unsafe, an attempt charged twice or never, or a token leak (errors, `runs.jsonl`, reports, printed lines);
- a way around the guards: voice-note paths with `..` or symlinks, URLs, photo folders;
- anything in the server that could start a second GPU or keep one running;
- anything a judge reading the code would find wrong or misleading.

## 4. Reply
1. **Verdict:** one line.
2. **Findings:** numbered, each with severity, file:line, the evidence and a fix.
3. **What you checked and found fine:** a short list.
4. **Open questions.**

Keep it under 700 words.

## The build: `git diff HEAD` (the code is uncommitted in the batch worktree; this copy of the repository is at the contract commit)
```diff
diff --git a/anamnesis/providers/base.py b/anamnesis/providers/base.py
index f2bce30..49637fd 100644
--- a/anamnesis/providers/base.py
+++ b/anamnesis/providers/base.py
@@ -114,19 +114,23 @@ _PRICES = {
                                 "output_tokens": Decimal("4.25") / 1_000_000},
     "sam-3.1": {"images": Decimal("2.50") / 1_000},
     "muse-voice-transcribe-1.0": {"audio_seconds": Decimal("0.18") / 3_600},
+    "muse-glimmer-30b+lora-r1@modal": {"gpu_seconds": Decimal("0.00127284")},
 }
 
 
 def cost_usd(
     model_id: str, *, input_tokens: int = 0, output_tokens: int = 0,
     audio_ms: int | None = None, images: int | None = None,
+    gpu_ms: int | None = None,
 ) -> Decimal:
     rates = _PRICES[model_id]
-    if any(value < 0 for value in (input_tokens, output_tokens, audio_ms or 0, images or 0)):
+    if any(value < 0 for value in (input_tokens, output_tokens, audio_ms or 0, images or 0,
+                                   gpu_ms or 0)):
         raise ValueError("usage cannot be negative")
     return (
         rates.get("input_tokens", Decimal(0)) * input_tokens
         + rates.get("output_tokens", Decimal(0)) * output_tokens
         + rates.get("images", Decimal(0)) * (images or 0)
         + rates.get("audio_seconds", Decimal(0)) * (((audio_ms or 0) + 999) // 1000)
+        + rates.get("gpu_seconds", Decimal(0)) * (((gpu_ms or 0) + 999) // 1000)
     )
diff --git a/anamnesis/providers/glimmer.py b/anamnesis/providers/glimmer.py
new file mode 100644
index 0000000..9703f60
--- /dev/null
+++ b/anamnesis/providers/glimmer.py
@@ -0,0 +1,106 @@
+"""Tuned Glimmer claim extractor on Modal (SPEC §4, batch 26)."""
+
+from typing import Any
+
+from anamnesis.providers.base import ProviderError, ProviderTrace, cost_usd, with_one_retry
+from anamnesis.providers.claims import _SYSTEM_PROMPT as _SPARK_SYSTEM_PROMPT
+from anamnesis.providers.claims import CLAIMS_SCHEMA, parse_claims_json
+from anamnesis.providers.spend import SpendGuard
+from anamnesis.schema import AudioTurn, PatientClaim
+
+GLIMMER_MODEL_ID = "muse-glimmer-30b+lora-r1@modal"
+GLIMMER_TIMEOUT_S = 120.0
+_SYSTEM_PROMPT = f"{_SPARK_SYSTEM_PROMPT}\nReasoning strength: low"
+
+
+class GlimmerClaimExtractor:
+    def __init__(self, client: Any, guard: SpendGuard) -> None:
+        self.client = client
+        self.guard = guard
+
+    def extract(
+        self, turns: list[AudioTurn],
+    ) -> tuple[list[PatientClaim], ProviderTrace | None]:
+        if not turns:
+            return [], None
+
+        transcript = "\n".join(
+            f"[{turn.turn_id} {turn.start_ms}–{turn.end_ms} ms, speaker {turn.speaker or 'unknown'}] "
+            f"{turn.transcript}"
+            for turn in turns
+        )
+        body = {
+            "messages": [
+                {"role": "system", "content": _SYSTEM_PROMPT},
+                {"role": "user", "content": transcript},
+            ],
+            "schema": CLAIMS_SCHEMA,
+            "max_tokens": 16000,
+        }
+
+        estimate = cost_usd(GLIMMER_MODEL_ID, gpu_ms=int(GLIMMER_TIMEOUT_S * 1000))
+
+        def attempt() -> tuple[list[PatientClaim], ProviderTrace]:
+            self.guard.check(estimate)
+            payload, latency_ms = self.client.post("/extract", json=body)
+            try:
+                if not isinstance(payload, dict):
+                    raise ValueError("reply is not an object")
+                call_id = payload["id"]
+                reply = payload["reply"]
+                opened_answer = payload["opened_answer"]
+                first_finish = payload["first_finish"]
+                answer_finish = payload["answer_finish"]
+                prompt_tokens = payload["prompt_tokens"]
+                completion_tokens = payload["completion_tokens"]
+                if not isinstance(call_id, str) or not call_id:
+                    raise ValueError("bad id")
+                if not (reply is None or isinstance(reply, str)):
+                    raise ValueError("bad reply")
+                if type(opened_answer) is not bool:
+                    raise ValueError("bad opened_answer")
+                if not (first_finish is None or isinstance(first_finish, str)):
+                    raise ValueError("bad first_finish")
+                if not (answer_finish is None or isinstance(answer_finish, str)):
+                    raise ValueError("bad answer_finish")
+                if type(prompt_tokens) is not int or prompt_tokens < 0:
+                    raise ValueError("bad prompt_tokens")
+                if type(completion_tokens) is not int or completion_tokens < 0:
+                    raise ValueError("bad completion_tokens")
+            except (KeyError, TypeError, ValueError) as exc:
+                raise ProviderError(
+                    "modal", "malformed Modal response", retryable=True,
+                    billable_uncertain=True, estimated_reason="malformed Modal response",
+                ) from exc
+            trace = ProviderTrace(
+                call_id=call_id,
+                model_id=GLIMMER_MODEL_ID,
+                latency_ms=latency_ms,
+                input_tokens=prompt_tokens,
+                output_tokens=completion_tokens,
+                cost_usd=cost_usd(GLIMMER_MODEL_ID, gpu_ms=latency_ms),
+            )
+            self.guard.charge_prechecked(trace)
+            if first_finish == "length" or answer_finish == "length":
+                raise ProviderError(
+                    "modal", "Glimmer reply stopped at the length limit", retryable=False,
+                    attempt_trace=trace,
+                )
+            if reply is None:
+                raise ProviderError(
+                    "modal", "Glimmer reply has no answer", retryable=True,
+                    attempt_trace=trace,
+                )
+            try:
+                claims = parse_claims_json(reply, turns)
+            except ProviderError as exc:
+                raise ProviderError(
+                    "modal", self.client._safe(str(exc)), retryable=True,
+                    attempt_trace=trace,
+                ) from None
+            return claims, trace
+
+        return with_one_retry(attempt, guard=self.guard, model_id=GLIMMER_MODEL_ID, estimate=estimate)
+
+
+__all__ = ["GLIMMER_MODEL_ID", "GLIMMER_TIMEOUT_S", "GlimmerClaimExtractor"]
diff --git a/scripts/intake_live.py b/scripts/intake_live.py
index f9fed25..b4a7cbb 100644
--- a/scripts/intake_live.py
+++ b/scripts/intake_live.py
@@ -2,21 +2,25 @@
 
     PYTHONPATH=. uv run python scripts/intake_live.py [--cap 5.00] [--session-usd 0.25]
     PYTHONPATH=. uv run python scripts/intake_live.py --case R1 --voice v1.wav --photo p1.jpg --lang ar \
-        [--repeat 10] [--top-k 3] [--reader baseten]
+        [--repeat 10] [--top-k 3] [--reader baseten|fireworks] [--extractor glimmer --glimmer-url URL]
 
 With no --case it runs the two synthetic notes (media: scripts/make_synthetic_media.sh). With --case it runs
 one staged case (evidence/batches/21/manifest.md): that voice note and those photos, in order, --repeat times.
---reader baseten makes Meta's open-weight Muse Spark Open on Baseten the label reader (key: BASETEN_API_KEY);
-everything else stays on Meta. It refuses any photo outside the public folders that docs/DATA_HANDLING.md lets
-go to Baseten, before the first call. Every voice note is re-written to its audio frames alone before any
-call, so no metadata chunk is sent or embedded in a brief.
+--reader baseten or --reader fireworks makes Meta's open-weight Muse Spark Open on Baseten or Fireworks the
+label reader (keys: BASETEN_API_KEY, FIREWORKS_API_KEY); everything else stays on Meta. It refuses any photo
+outside the public folders that docs/DATA_HANDLING.md lets go to Baseten or Fireworks, before the first call.
+--extractor glimmer makes the tuned Glimmer on Modal the claim extractor (token: MODAL_PROXY_TOKEN, URL from
+--glimmer-url or GLIMMER_URL); it refuses any voice note but the synthetic ones under
+evidence/raw/media/public/voice/ and any URL off .modal.run, before the first call. Every voice note is
+re-written to its audio frames alone before any call, so no metadata chunk is sent or embedded in a brief.
 The key comes from MODEL_API_KEY in the environment or the macOS Keychain (service META_API_KEY), and is never
 printed or saved. Each intake runs inside a SessionGuard (per-intake $ and call caps) in front of
 evidence/spend/ledger.jsonl.
 Output, per run:
 - evidence/live/<date>/report_<name>.json, the ReconciliationReport (<name>: the language, or case and run);
-- one summary line in evidence/live/<date>/runs.jsonl: findings, calls, spend, wall-clock time, and the
-  latency of each claim-extraction request against the client's 30 s timeout;
+- one summary line in evidence/live/<date>/runs.jsonl: findings, calls, spend, wall-clock time, the reader
+  (spark, baseten or fireworks) and the extractor (spark or glimmer), and the latency of each
+  claim-extraction request against the extractor client's timeout;
 - the brief, evidence/raw/briefs/<date>/<name>.html (git-ignored: it embeds the photos and the voice note).
 """
 
@@ -32,6 +36,7 @@ from dataclasses import dataclass
 from datetime import UTC, datetime
 from decimal import Decimal
 from pathlib import Path
+from urllib.parse import urlparse
 
 from anamnesis.agent import run_intake
 from anamnesis.agent.loop import SAM_CONCEPTS
@@ -39,6 +44,7 @@ from anamnesis.brief import render_brief
 from anamnesis.core.catalogue import load_catalogue
 from anamnesis.providers import SpendGuard
 from anamnesis.providers.claims import MetaClaimExtractor
+from anamnesis.providers.glimmer import GLIMMER_TIMEOUT_S, GlimmerClaimExtractor
 from anamnesis.providers.meta import MetaClient, MetaLabelReader, MetaSegmenter, MetaTranscriber
 from anamnesis.providers.openweight import PRESETS, OpenWeightClient, OpenWeightLabelReader
 from anamnesis.providers.spend import SessionGuard
@@ -78,6 +84,18 @@ class TimedClient:
         return getattr(self.client, name)
 
 
+def _timeout_ms(timed: TimedClient) -> int:
+    """The wrapped client's own timeout in ms, for the printed claim-request line."""
+    timeout = getattr(getattr(timed.client, "_http", None), "timeout", None)
+    if isinstance(timeout, (int, float)):
+        return int(timeout * 1000)
+    for attr in ("read", "connect", "write", "pool"):
+        value = getattr(timeout, attr, None)
+        if isinstance(value, (int, float)):
+            return int(value * 1000)
+    return 30000
+
+
 @dataclass
 class Run:
     ledger: SpendGuard
@@ -87,7 +105,8 @@ class Run:
     top_k: int
     reports: Path
     briefs: Path
-    open_client: OpenWeightClient | None = None  # set: Muse Spark Open on Baseten reads the labels
+    open_client: OpenWeightClient | None = None  # set: Muse Spark Open reads the labels
+    glimmer_client: OpenWeightClient | None = None  # set: the tuned Glimmer on Modal extracts the claims
 
 
 def intake(run: Run, name: str, audio: bytes, images: list[tuple[bytes, str]],
@@ -99,17 +118,22 @@ def intake(run: Run, name: str, audio: bytes, images: list[tuple[bytes, str]],
     # budget keeps --session-usd the real bound (supervisor 23 round 3 #6).
     guard = SessionGuard(run.ledger, max_usd=run.session_usd, max_calls=2 * calls)
     timed = TimedClient(run.client)
+    if run.glimmer_client is None:
+        extractor, claim_timed = MetaClaimExtractor(timed, guard), timed
+    else:
+        claim_timed = TimedClient(run.glimmer_client)
+        extractor = GlimmerClaimExtractor(claim_timed, guard)
     keywords = [n for entry in run.catalogue.entries for n in (entry.brand, *entry.aliases)]
     if run.open_client is None:
         reader = MetaLabelReader(run.client, guard)
     else:
-        reader = OpenWeightLabelReader(run.open_client, guard, model=PRESETS["baseten"]["model"],
-                                       price_key="muse-spark-open@baseten",
-                                       json_mode=PRESETS["baseten"]["json_mode"])
+        provider = run.open_client.provider
+        reader = OpenWeightLabelReader(run.open_client, guard, model=PRESETS[provider]["model"],
+                                       price_key=f"muse-spark-open@{provider}", json_mode=False)
     start = time.monotonic()
     report = run_intake(
         audio, images,
-        transcriber=MetaTranscriber(run.client, guard), extractor=MetaClaimExtractor(timed, guard),
+        transcriber=MetaTranscriber(run.client, guard), extractor=extractor,
         segmenter=MetaSegmenter(run.client, guard), reader=reader,
         catalogue=run.catalogue, language_bias=LANGUAGES[lang], keywords=keywords, lang_hint=lang,
         max_provider_calls=calls, top_k=run.top_k,
@@ -119,13 +143,16 @@ def intake(run: Run, name: str, audio: bytes, images: list[tuple[bytes, str]],
     brief = render_brief(report, images, (audio, "audio/wav"), run.catalogue)
     (run.briefs / f"{name}.html").write_text(brief, encoding="utf-8")
     line = {"run": name, "at": datetime.now(UTC).isoformat(timespec="seconds"),
-            "reader": "spark" if run.open_client is None else "baseten", "calls": report.calls,
-            "spend_usd": str(report.spend_usd), "wall_s": wall_s, "claim_request_ms": timed.latencies_ms,
+            "reader": "spark" if run.open_client is None else run.open_client.provider,
+            "extractor": "spark" if run.glimmer_client is None else "glimmer",
+            "calls": report.calls,
+            "spend_usd": str(report.spend_usd), "wall_s": wall_s,
+            "claim_request_ms": claim_timed.latencies_ms,
             "findings": [[f.type.value, f.claim_id, f.observation_id] for f in report.findings]}
     with (run.reports / "runs.jsonl").open("a", encoding="utf-8") as out:
         out.write(json.dumps(line) + "\n")
     print(f"intake {name}: {report.calls} calls, ${report.spend_usd:.5f}, {wall_s} s, "
-          f"claim requests {timed.latencies_ms} ms (timeout 30000)")
+          f"claim requests {claim_timed.latencies_ms} ms (timeout {_timeout_ms(claim_timed)})")
     for step in report.steps:
         print(f"      {step.n:2} {step.action.value:16} {step.target[:28]:28} {step.outcome}")
     for f in report.findings:
@@ -165,21 +192,46 @@ def main() -> None:
     parser.add_argument("--lang", choices=sorted(LANGUAGES), default="en")
     parser.add_argument("--repeat", type=int, default=1)
     parser.add_argument("--top-k", type=int, default=3, help="SAM regions kept per photo")
-    parser.add_argument("--reader", choices=("spark", "baseten"), default="spark",
-                        help="label reader: Spark 1.3, or Muse Spark Open on Baseten (public photos only)")
+    parser.add_argument("--reader", choices=("spark", "baseten", "fireworks"), default="spark",
+                        help="label reader: Spark 1.3, or Muse Spark Open on Baseten or Fireworks "
+                             "(public photos only)")
+    parser.add_argument("--extractor", choices=("spark", "glimmer"), default="spark",
+                        help="claim extractor: Spark 1.3, or the tuned Glimmer on Modal "
+                             "(synthetic voice only)")
+    parser.add_argument("--glimmer-url", default=os.environ.get("GLIMMER_URL"),
+                        help="the Modal extract URL (default: GLIMMER_URL)")
     args = parser.parse_args()
     if args.case and not args.voice:
         sys.exit("--case needs --voice")
     if args.top_k < 0:  # SAM's top_regions refuses it, but only mid-run, after spend (M8 #1)
         sys.exit("--top-k must be 0 or more")
-    if args.reader == "baseten":
+    if args.reader in ("baseten", "fireworks"):
         if not args.case:
-            sys.exit("--reader baseten needs --case: the synthetic notes' pack image may not go to Baseten")
+            if args.reader == "baseten":
+                sys.exit("--reader baseten needs --case: "
+                         "the synthetic notes' pack image may not go to Baseten")
+            sys.exit("--reader fireworks needs --case: "
+                     "only a staged case's public photos may go to Fireworks")
         for path in args.photo:  # checked before any call
             resolved = Path(path).resolve()
             if not any(resolved.is_relative_to(folder.resolve()) for folder in OPEN_WEIGHT_PHOTOS):
-                sys.exit(f"{path} is not a public photo that may go to Baseten (docs/DATA_HANDLING.md). "
-                         "Ahmed's own media never go there.")
+                if args.reader == "baseten":
+                    sys.exit(f"{path} is not a public photo that may go to Baseten "
+                             "(docs/DATA_HANDLING.md). Ahmed's own media never go there.")
+                sys.exit(f"{path} is not a public photo that may go to Fireworks "
+                         "(docs/DATA_HANDLING.md). Ahmed's own media never go there.")
+    if args.extractor == "glimmer":
+        if not args.case:
+            sys.exit("--extractor glimmer needs --case: "
+                     "only a staged case's synthetic voice note may go to Modal")
+        if not args.voice or not Path(args.voice).resolve().is_relative_to(
+                (MEDIA / "public/voice").resolve()):
+            sys.exit(f"{args.voice} is not a synthetic voice note that may go to Modal "
+                     "(docs/DATA_HANDLING.md). Ahmed's own voice never goes there.")
+        host = urlparse(args.glimmer_url).hostname if args.glimmer_url else None
+        if (not args.glimmer_url or not args.glimmer_url.startswith("https://")
+                or not (host and host.endswith(".modal.run"))):
+            sys.exit(f"{args.glimmer_url} is not an https:// URL on a .modal.run host.")
     day = datetime.now(UTC).strftime("%Y-%m-%d")
     run = Run(SpendGuard(LEDGER, cap_usd=Decimal(args.cap)),
               MetaClient(api_key=os.environ.get("MODEL_API_KEY") or keychain("META_API_KEY")),
@@ -189,6 +241,14 @@ def main() -> None:
         run.open_client = OpenWeightClient(
             api_key=os.environ.get("BASETEN_API_KEY") or keychain("BASETEN_API_KEY"),
             base_url=PRESETS["baseten"]["base_url"], provider="baseten")
+    elif args.reader == "fireworks":
+        run.open_client = OpenWeightClient(
+            api_key=os.environ.get("FIREWORKS_API_KEY") or keychain("FIREWORKS_API_KEY"),
+            base_url=PRESETS["fireworks"]["base_url"], provider="fireworks")
+    if args.extractor == "glimmer":
+        run.glimmer_client = OpenWeightClient(
+            api_key=os.environ.get("MODAL_PROXY_TOKEN") or keychain("MODAL_PROXY_TOKEN"),
+            base_url=args.glimmer_url, provider="modal", timeout=GLIMMER_TIMEOUT_S)
     run.reports.mkdir(parents=True, exist_ok=True)
     run.briefs.mkdir(parents=True, exist_ok=True)
     start = run.ledger.total_usd
diff --git a/tests/unit/test_b26_extra.py b/tests/unit/test_b26_extra.py
new file mode 100644
index 0000000..7646ce8
--- /dev/null
+++ b/tests/unit/test_b26_extra.py
@@ -0,0 +1,177 @@
+"""Batch 26 gaps the contract leaves: GPU pricing, Glimmer request shape and validation."""
+
+import importlib.util
+import json
+from decimal import Decimal
+from pathlib import Path
+
+import httpx
+import pytest
+
+from anamnesis.providers import ProviderError, SpendGuard, cost_usd
+from anamnesis.providers.claims import _SYSTEM_PROMPT as SPARK_SYSTEM_PROMPT
+from anamnesis.providers.claims import MetaClaimExtractor
+from anamnesis.providers.glimmer import (
+    _SYSTEM_PROMPT,
+    GLIMMER_MODEL_ID,
+    GLIMMER_TIMEOUT_S,
+    GlimmerClaimExtractor,
+)
+from anamnesis.providers.meta import MetaClient
+from anamnesis.providers.openweight import OpenWeightClient
+from anamnesis.schema import AudioTurn
+
+ROOT = Path(__file__).resolve().parents[2]
+TOKEN = "wk-extra1.ws-extra2"
+URL = "https://example--anamnesis-glimmer-serve-server-web.modal.run"
+TURNS = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=3200,
+                  transcript="I take Concor five milligrams once a day.")]
+CLAIM = {
+    "name_text": "Concor", "inn": None, "strength": None,
+    "intake_amount": {"inn": "bisoprolol", "amount": "5", "unit": "mg"},
+    "regimen": {"units_per_intake": None, "intakes_per_day": "1", "as_needed": None},
+    "status": "active", "turn_ids": ["turn-0"],
+}
+RATE = Decimal("0.00127284")
+
+
+def _payload(**change: object) -> dict:
+    return {"id": "glimmer-call-1", "reply": json.dumps({"claims": [CLAIM]}), "opened_answer": True,
+            "first_finish": "stop", "answer_finish": "stop", "prompt_tokens": 1200,
+            "completion_tokens": 150, **change}
+
+
+def _extractor(tmp_path: Path, replies: list, cap: Decimal = Decimal(5)):
+    seen: list[httpx.Request] = []
+
+    def handler(request: httpx.Request) -> httpx.Response:
+        seen.append(request)
+        reply = replies[min(len(seen), len(replies)) - 1]
+        if isinstance(reply, int):
+            return httpx.Response(reply, json={"error": {"message": "no"}})
+        return httpx.Response(200, json=reply)
+
+    client = OpenWeightClient(api_key=TOKEN, base_url=URL, provider="modal",
+                              transport=httpx.MockTransport(handler))
+    guard = SpendGuard(tmp_path / "ledger.jsonl", cap_usd=cap)
+    return GlimmerClaimExtractor(client, guard), guard, seen
+
+
+def test_gpu_seconds_round_up_like_audio_seconds():
+    assert cost_usd(GLIMMER_MODEL_ID, gpu_ms=0) == 0
+    assert cost_usd(GLIMMER_MODEL_ID, gpu_ms=1) == RATE
+    assert cost_usd(GLIMMER_MODEL_ID, gpu_ms=1000) == RATE
+    assert cost_usd(GLIMMER_MODEL_ID, gpu_ms=1001) == 2 * RATE
+    with pytest.raises(ValueError):
+        cost_usd(GLIMMER_MODEL_ID, gpu_ms=-1)
+
+
+def test_other_prices_and_calls_are_unchanged():
+    assert cost_usd("muse-spark-1.3", input_tokens=1_000_000) == Decimal("1.25")
+    assert cost_usd("muse-voice-transcribe-1.0", audio_ms=1) == Decimal("0.18") / 3600
+    assert cost_usd("sam-3.1", images=1) == Decimal("2.50") / 1000
+
+
+def test_the_system_prompt_is_sparks_plus_the_reasoning_line():
+    assert _SYSTEM_PROMPT == SPARK_SYSTEM_PROMPT + "\nReasoning strength: low"
+
+
+def test_the_user_message_matches_sparks_byte_for_byte(tmp_path):
+    def spark_handler(request: httpx.Request) -> httpx.Response:
+        spark_seen.append(json.loads(request.content))
+        return httpx.Response(200, json={"id": "x", "choices": [{"message": {
+            "content": json.dumps({"claims": [CLAIM]})}, "finish_reason": "stop"}],
+            "usage": {"prompt_tokens": 10, "completion_tokens": 5}})
+
+    spark_seen: list[dict] = []
+    spark = MetaClaimExtractor(
+        MetaClient(api_key="k", transport=httpx.MockTransport(spark_handler)),
+        SpendGuard(tmp_path / "spark.jsonl", cap_usd=Decimal(5)))
+    spark.extract(TURNS)
+    extractor, _, seen = _extractor(tmp_path, [_payload()])
+    extractor.extract(TURNS)
+    assert json.loads(seen[0].content)["messages"][1] == spark_seen[0]["messages"][1]
+
+
+@pytest.mark.parametrize("change", [
+    {"prompt_tokens": True},  # a bool is not an int
+    {"completion_tokens": -1},
+    {"opened_answer": 1},
+    {"first_finish": 5},
+    {"answer_finish": 0},
+    {"id": None},
+])
+def test_more_malformed_replies_retry_and_charge_estimates(tmp_path, change):
+    estimate = cost_usd(GLIMMER_MODEL_ID, gpu_ms=int(GLIMMER_TIMEOUT_S * 1000))
+    extractor, guard, seen = _extractor(tmp_path, [_payload(**change)])
+    with pytest.raises(ProviderError) as caught:
+        extractor.extract(TURNS)
+    assert caught.value.provider == "modal" and caught.value.retryable
+    assert len(seen) == 2 and guard.total_usd == 2 * estimate
+
+
+def test_a_reply_missing_a_field_is_malformed(tmp_path):
+    payload = _payload()
+    del payload["answer_finish"]
+    extractor, guard, seen = _extractor(tmp_path, [payload])
+    with pytest.raises(ProviderError) as caught:
+        extractor.extract(TURNS)
+    assert caught.value.provider == "modal" and caught.value.retryable
+    assert len(seen) == 2
+
+
+def test_a_length_stop_carries_its_trace_and_is_not_retryable(tmp_path):
+    extractor, guard, seen = _extractor(tmp_path, [_payload(first_finish="length")])
+    with pytest.raises(ProviderError) as caught:
+        extractor.extract(TURNS)
+    assert caught.value.provider == "modal" and not caught.value.retryable
+    assert caught.value.attempt_trace is not None
+    assert caught.value.attempt_trace.call_id == "glimmer-call-1"
+    assert len(seen) == 1 and guard.total_usd == caught.value.attempt_trace.cost_usd
+
+
+def test_a_missing_answer_carries_its_trace_and_retries(tmp_path):
+    extractor, _, seen = _extractor(tmp_path, [_payload(reply=None, answer_finish=None)])
+    with pytest.raises(ProviderError) as caught:
+        extractor.extract(TURNS)
+    assert caught.value.provider == "modal" and caught.value.retryable
+    assert caught.value.attempt_trace is not None and len(seen) == 2
+
+
+def test_a_rejected_reply_carries_its_trace_and_hides_the_key(tmp_path):
+    bad = json.dumps({"claims": [{**CLAIM, "name_text": "Lipitor"}]})
+    extractor, _, seen = _extractor(tmp_path, [_payload(reply=bad)])
+    with pytest.raises(ProviderError) as caught:
+        extractor.extract(TURNS)
+    assert caught.value.provider == "modal" and caught.value.retryable
+    assert caught.value.attempt_trace is not None and len(seen) == 2
+    assert TOKEN not in str(caught.value)
+
+
+def _intake_live():
+    spec = importlib.util.spec_from_file_location("intake_live_b26_extra", ROOT / "scripts/intake_live.py")
+    module = importlib.util.module_from_spec(spec)
+    spec.loader.exec_module(module)
+    return module
+
+
+def test_the_printed_timeout_is_the_extractor_clients_own():
+    il = _intake_live()
+    spark_timed = il.TimedClient(MetaClient(api_key="k"))
+    assert il._timeout_ms(spark_timed) == 30000
+    modal_timed = il.TimedClient(OpenWeightClient(api_key="k", base_url=URL, provider="modal",
+                                                 timeout=GLIMMER_TIMEOUT_S))
+    assert il._timeout_ms(modal_timed) == int(GLIMMER_TIMEOUT_S * 1000)
+
+
+def test_the_docstring_lists_the_new_options():
+    text = (ROOT / "scripts/intake_live.py").read_text(encoding="utf-8").split('"""')[1]
+    assert "--extractor" in text and "--glimmer-url" in text and "fireworks" in text
+
+
+def test_the_server_names_the_app_adapter_and_deploy_command():
+    source = (ROOT / "finetune/modal_serve.py").read_text(encoding="utf-8")
+    assert 'modal.App("anamnesis-glimmer-serve")' in source
+    assert 'LoRARequest("r1", 1, "/runs/r1/adapter")' in source
+    assert "~/.local/bin/modal deploy finetune/modal_serve.py" in source
+    assert "/health" in source and '"ready": True' in source
```

## The new server, `finetune/modal_serve.py` (untracked)
```python
"""Serve the r1 Glimmer LoRA on Modal for the product's optional claim extractor.

Deploy it:

    ~/.local/bin/modal deploy finetune/modal_serve.py

Then warm it up: GET /health with the proxy token in an Authorization header, waiting up to 10 minutes for
the container to load the weights and the adapter. Only the synthetic-voice transcripts of staged cases go
to this endpoint (docs/DATA_HANDLING.md).
"""

import sys
import uuid
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import glimmer  # noqa: E402
import modal_glimmer  # noqa: E402

app = modal.App("anamnesis-glimmer-serve")
image = modal_glimmer.eval_image.add_local_file(HERE / "modal_glimmer.py", "/root/modal_glimmer.py")


def _valid_body(body) -> tuple | None:
    """The extract request's (messages, schema, max_tokens), or None for a bad body."""
    if not isinstance(body, dict):
        return None
    messages, schema, max_tokens = body.get("messages"), body.get("schema"), body.get("max_tokens")
    if (
        not isinstance(messages, list)
        or len(messages) != 2
        or not all(isinstance(message, dict) for message in messages)
        or messages[0].get("role") != "system"
        or messages[1].get("role") != "user"
        or not all(
            isinstance(message.get("content"), str) and message["content"]
            for message in messages
        )
    ):
        return None
    if not isinstance(schema, dict):
        return None
    if type(max_tokens) is not int or not 1 <= max_tokens <= 16000:
        return None
    return messages, schema, max_tokens


@app.cls(
    image=image,
    gpu=glimmer.GPU,
    timeout=600,
    scaledown_window=600,
    max_containers=1,
    **modal_glimmer.MACHINE,
)
class Server:
    @modal.enter()
    def load(self) -> None:
        from vllm import LLM
        from vllm.lora.request import LoRARequest

        modal_glimmer.runs.reload()
        self.llm = LLM(
            model=modal_glimmer.WEIGHTS,
            enable_lora=True,
            max_lora_rank=glimmer.LORA["r"],
            max_loras=1,
            max_model_len=glimmer.MAX_MODEL_LEN,
            limit_mm_per_prompt={"image": 0, "video": 0},
            seed=glimmer.EVAL_SEED,
        )
        self.tokenizer = self.llm.get_tokenizer()
        self.lora = LoRARequest("r1", 1, "/runs/r1/adapter")

    @modal.asgi_app(requires_proxy_auth=True)
    def web(self):
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse

        web_app = FastAPI()

        @web_app.get("/health")
        def health():
            return {"ready": True, "adapter": "r1", "revision": glimmer.REVISION}

        @web_app.post("/extract")
        async def extract(request: Request):
            checked = _valid_body(await request.json())
            if checked is None:
                return JSONResponse({"error": "bad extract body"}, status_code=400)
            messages, schema, max_tokens = checked
            row = modal_glimmer._two_passes(
                self.llm, self.tokenizer, [messages], self.lora, schema, max_tokens
            )["rows"][0]
            return {
                "id": uuid.uuid4().hex,
                "reply": row["reply"],
                "opened_answer": row["opened_answer"],
                "first_finish": row["first_finish"],
                "answer_finish": row.get("answer_finish"),
                "prompt_tokens": len(glimmer.prompt_ids(self.tokenizer, messages)),
                "completion_tokens": row["first_tokens"] + row.get("answer_tokens", 0),
            }

        return web_app
```
