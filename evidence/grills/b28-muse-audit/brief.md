# Batch 28 audit: double-check another Muse session's build, read-only

You are auditing code that another Muse Code session just wrote for batch 28 of Anamnesis. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, use no API key, and run no `modal` command;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The audit is done ONLY when your reply has the three sections in §3, and every finding cites a file and line you opened, or a line of the diff below.

## 2. What the code must do
SPEC.md §4 step 5b, the §4 "Budget" line, §4 "The second reader in the live script (batch 28)" and §8's `add_photo` lines: open them in the repository. With a `second_reader`, a reading still partial or unreadable after the zoom gets one `second_read` of the first read's crop; it replaces the reading only when readable, for the same region, and agreeing on ingredients and strengths. Without one, nothing changes.

The contract is `tests/contract/test_b28_second_reader.py`, and the build passes it. Look for what it doesn't catch:
- any way a second reading overrides evidence it shouldn't, or a step-5 reading is lost;
- any change to the report, steps, calls or budget when no second reader is given;
- the budget and the session's dollar cap; the re-photo path; provenance of the crop; the brief's timeline;
- the live script's guards running before any key or client, and Ahmed's own photos never reaching Fireworks.

## 3. Reply
1. **Verdict:** one line.
2. **Findings:** numbered, each with severity, file:line, the evidence and a fix.
3. **What you checked and found fine:** a short list.

Keep it under 500 words.

## The build: `git diff HEAD` (uncommitted in the batch worktree; this copy of the repository is at the contract commit)
```diff
diff --git a/anamnesis/agent/loop.py b/anamnesis/agent/loop.py
index 966d9e6..d91dd70 100644
--- a/anamnesis/agent/loop.py
+++ b/anamnesis/agent/loop.py
@@ -12,7 +12,7 @@ from anamnesis.core.catalogue import Catalogue
 from anamnesis.core.reconcile import reconcile_all
 from anamnesis.providers.sam import top_regions
 from anamnesis.providers.spark import LabelReading
-from anamnesis.schema import ImageRegion, PackObservation, Readability
+from anamnesis.schema import ImageRegion, PackObservation, Readability, canonical_inn
 from anamnesis.schema.report import AgentAction, ReconciliationReport
 
 Image = tuple[bytes, str]
@@ -117,6 +117,59 @@ def _zoom(
     return zoomed
 
 
+def _named_ingredients(reading: LabelReading) -> frozenset[str] | None:
+    """Canonical INNs the reading names, or None when it names nothing (SPEC §4 step 5b)."""
+    if reading.strength is not None:
+        return frozenset(canonical_inn(part.inn) for part in reading.strength.ingredients)
+    if reading.inn is not None:
+        return frozenset({canonical_inn(reading.inn)})
+    return None
+
+
+def _strength_key(strength) -> frozenset:
+    """Ingredient, amount and unit per part; per and release don't count (SPEC §4 step 5b)."""
+    return frozenset(
+        (canonical_inn(part.inn), part.amount, part.unit.value) for part in strength.ingredients
+    )
+
+
+def _second_read(
+    session: IntakeSession, second_reader, image: Image, region: ImageRegion,
+    reading: LabelReading,
+) -> LabelReading:
+    """One second-model re-read of the first read's crop; a readable agreement replaces the first."""
+    if second_reader is None or reading.readability not in _NEEDS_ZOOM:
+        return reading
+    if session.exhausted:  # budget_exhausted is the last step: no crop, no log
+        return reading
+    try:
+        crop = crop_region(image[0], region)
+    except ValueError:
+        session.note(AgentAction.SECOND_READ, region.region_id, "error: crop failed")
+        return reading
+    second = session.call(
+        AgentAction.SECOND_READ, region.region_id,
+        lambda: second_reader.read(crop, region, mime="image/png", cropped=True),
+        lambda new: new.readability.value,
+    )
+    if second is None:
+        return reading
+    if second.region_id != region.region_id:
+        session.note(AgentAction.SECOND_READ, region.region_id, "error: reading for another region")
+        return reading
+    if second.readability is not Readability.READABLE:
+        return reading
+    first_names, second_names = _named_ingredients(reading), _named_ingredients(second)
+    if first_names is not None and second_names is not None and first_names != second_names:
+        session.note(AgentAction.SECOND_READ, region.region_id, "conflict: kept the first reading")
+        return reading
+    if reading.strength is not None and second.strength is not None:
+        if _strength_key(reading.strength) != _strength_key(second.strength):
+            session.note(AgentAction.SECOND_READ, region.region_id, "conflict: kept the first reading")
+            return reading
+    return second
+
+
 def _observation(index: int, reading: LabelReading) -> PackObservation:
     return PackObservation(
         observation_id=f"o{index}", label_text=reading.label_text, inn=reading.inn,
@@ -129,11 +182,12 @@ def run_intake(
     audio: bytes | None, images: list[Image], *, transcriber, extractor, segmenter, reader,
     catalogue: Catalogue, language_bias: list[str] | None = None, keywords: list[str] | None = None,
     lang_hint: str | None = None, concepts: tuple[str, ...] = SAM_CONCEPTS,
-    top_k: int = 3, max_provider_calls: int | None = None,
+    top_k: int = 3, max_provider_calls: int | None = None, second_reader=None,
 ) -> ReconciliationReport:
     """Run one patient intake in a fixed order and return the single report artifact."""
     if max_provider_calls is None:
-        max_provider_calls = 2 + (len(concepts) + 2 * top_k) * len(images)
+        per_region = 3 * top_k if second_reader is not None else 2 * top_k
+        max_provider_calls = 2 + (len(concepts) + per_region) * len(images)
     session = IntakeSession(max_provider_calls)
     turns = []
     if audio is not None:
@@ -160,10 +214,12 @@ def run_intake(
         kept, read = _read_photo(session, segmenter, reader, prepared, concepts, top_k)
         regions.update({region.region_id: region for region in kept})
         readings += read
-    final = [
-        _zoom(session, reader, image, region, reading) if reading.readability in _NEEDS_ZOOM else reading
-        for image, region, reading in readings
-    ]
+    final = []
+    for image, region, reading in readings:
+        if reading.readability in _NEEDS_ZOOM:
+            reading = _zoom(session, reader, image, region, reading)
+            reading = _second_read(session, second_reader, image, region, reading)
+        final.append(reading)
     observations = [_observation(index, reading) for index, reading in enumerate(final)]
     findings = reconcile_all(claims, observations, catalogue)
     if not session.exhausted:
diff --git a/anamnesis/review.py b/anamnesis/review.py
index dbd09e1..b8ff4b9 100644
--- a/anamnesis/review.py
+++ b/anamnesis/review.py
@@ -7,6 +7,7 @@ from anamnesis.agent.loop import (
     _observation,
     _prepare,
     _read_photo,
+    _second_read,
     _zoom,
 )
 from anamnesis.agent.session import IntakeSession
@@ -96,7 +97,7 @@ def request_message(report: ReconciliationReport, request: PhotoRequest) -> str:
 def add_photo(
     report: ReconciliationReport, review: Review, request_id: str, photo: Image,
     images: list[Image], audio: Image | None, *, segmenter, reader, catalogue,
-    concepts: tuple[str, ...] = SAM_CONCEPTS, top_k: int = 3,
+    second_reader=None, concepts: tuple[str, ...] = SAM_CONCEPTS, top_k: int = 3,
     max_provider_calls: int | None = None,
 ) -> tuple[ReconciliationReport, Review]:
     if review.intake_id != report.intake_id:
@@ -113,7 +114,8 @@ def add_photo(
     if any(fresh[0][0] == item[0][0] for item in prepared):
         raise ValueError("photo was already given")
     if max_provider_calls is None:
-        max_provider_calls = len(concepts) + 2 * top_k
+        per_region = 3 * top_k if second_reader is not None else 2 * top_k
+        max_provider_calls = len(concepts) + per_region
     session = IntakeSession(max_provider_calls)
     kept, readings = [], []
     if fresh[1] is None:
@@ -121,10 +123,12 @@ def add_photo(
             session.note(AgentAction.SEGMENT, fresh[2][:12], "error: image cannot be decoded")
     else:
         kept, readings = _read_photo(session, segmenter, reader, fresh, concepts, top_k)
-    final = [
-        _zoom(session, reader, image, region, reading) if reading.readability in _NEEDS_ZOOM else reading
-        for image, region, reading in readings
-    ]
+    final = []
+    for image, region, reading in readings:
+        if reading.readability in _NEEDS_ZOOM:
+            reading = _zoom(session, reader, image, region, reading)
+            reading = _second_read(session, second_reader, image, region, reading)
+        final.append(reading)
     fresh_observations = [
         _observation(len(report.observations) + index, reading)
         for index, reading in enumerate(final)
diff --git a/anamnesis/schema/report.py b/anamnesis/schema/report.py
index 7bc8e44..d48d8a8 100644
--- a/anamnesis/schema/report.py
+++ b/anamnesis/schema/report.py
@@ -19,6 +19,7 @@ class AgentAction(StrEnum):
     SEGMENT = "segment"
     READ = "read"
     ZOOM_READ = "zoom_read"
+    SECOND_READ = "second_read"
     RECONCILE = "reconcile"
     BUDGET_EXHAUSTED = "budget_exhausted"
 
diff --git a/scripts/intake_live.py b/scripts/intake_live.py
index 61f704a..575156f 100644
--- a/scripts/intake_live.py
+++ b/scripts/intake_live.py
@@ -2,7 +2,8 @@
 
     PYTHONPATH=. uv run python scripts/intake_live.py [--cap 5.00] [--session-usd 0.25]
     PYTHONPATH=. uv run python scripts/intake_live.py --case R1 --voice v1.wav --photo p1.jpg --lang ar \
-        [--repeat 10] [--top-k 3] [--reader baseten|fireworks] [--extractor glimmer --glimmer-url URL]
+        [--repeat 10] [--top-k 3] [--reader baseten|fireworks] [--extractor glimmer --glimmer-url URL] \
+        [--second-reader fireworks]
 
 With no --case it runs the two synthetic notes (media: scripts/make_synthetic_media.sh). With --case it runs
 one staged case (evidence/batches/21/manifest.md): that voice note and those photos, in order, --repeat times.
@@ -12,7 +13,10 @@ for low reasoning effort, as Spark 1.3's reader does. It refuses any photo
 outside the public folders that docs/DATA_HANDLING.md lets go to Baseten or Fireworks, before the first call.
 --extractor glimmer makes the tuned Glimmer on Modal the claim extractor (token: MODAL_PROXY_TOKEN, URL from
 --glimmer-url or GLIMMER_URL); it refuses any voice note but the synthetic ones under
-evidence/raw/media/public/voice/ and any URL off .modal.run, before the first call. Every voice note is
+evidence/raw/media/public/voice/ and any URL off .modal.run, before the first call. --second-reader fireworks
+gives the loop Muse Spark Open on Fireworks as a second label reader (SPEC §4 step 5b): when Spark 1.3 still
+can't read a pack after its zoom, the same crop is read once more (key: FIREWORKS_API_KEY); it needs --case,
+--reader spark and public photos only, before the first call. Every voice note is
 re-written to its audio frames alone before any call, so no metadata chunk is sent or embedded in a brief.
 The key comes from MODEL_API_KEY in the environment or the macOS Keychain (service META_API_KEY), and is never
 printed or saved. Each intake runs inside a SessionGuard (per-intake $ and call caps) in front of
@@ -20,8 +24,8 @@ evidence/spend/ledger.jsonl.
 Output, per run:
 - evidence/live/<date>/report_<name>.json, the ReconciliationReport (<name>: the language, or case and run);
 - one summary line in evidence/live/<date>/runs.jsonl: findings, calls, spend, wall-clock time, the reader
-  (spark, baseten or fireworks) and the extractor (spark or glimmer), and the latency of each
-  claim-extraction request against the extractor client's timeout;
+  (spark, baseten or fireworks), the extractor (spark or glimmer) and the second reader (fireworks or null),
+  and the latency of each claim-extraction request against the extractor client's timeout;
 - the brief, evidence/raw/briefs/<date>/<name>.html (git-ignored: it embeds the photos and the voice note).
 """
 
@@ -108,13 +112,15 @@ class Run:
     briefs: Path
     open_client: OpenWeightClient | None = None  # set: Muse Spark Open reads the labels
     glimmer_client: OpenWeightClient | None = None  # set: the tuned Glimmer on Modal extracts the claims
+    second_client: OpenWeightClient | None = None  # set: Muse Spark Open re-reads what Spark can't
 
 
 def intake(run: Run, name: str, audio: bytes, images: list[tuple[bytes, str]],
            lang: str) -> ReconciliationReport:
     # The loop's own default budget (SPEC §4 Budget): every call it can make. The dollar cap bounds the spend;
     # a fixed 12 dropped a sent pack on a four-photo intake (supervisor 23, round 2 #1).
-    calls = 2 + (len(SAM_CONCEPTS) + 2 * run.top_k) * len(images)
+    per_region = 3 * run.top_k if run.second_client is not None else 2 * run.top_k
+    calls = 2 + (len(SAM_CONCEPTS) + per_region) * len(images)
     # The guard counts every charged attempt and a call charges at most two (one retry), so twice the loop's
     # budget keeps --session-usd the real bound (supervisor 23 round 3 #6).
     guard = SessionGuard(run.ledger, max_usd=run.session_usd, max_calls=2 * calls)
@@ -132,13 +138,19 @@ def intake(run: Run, name: str, audio: bytes, images: list[tuple[bytes, str]],
         reader = OpenWeightLabelReader(run.open_client, guard, model=PRESETS[provider]["model"],
                                        price_key=f"muse-spark-open@{provider}", json_mode=False,
                                        reasoning_effort="low" if provider == "fireworks" else None)
+    if run.second_client is None:
+        second_reader = None
+    else:
+        second_reader = OpenWeightLabelReader(
+            run.second_client, guard, model=PRESETS["fireworks"]["model"],
+            price_key="muse-spark-open@fireworks", json_mode=False, reasoning_effort="low")
     start = time.monotonic()
     report = run_intake(
         audio, images,
         transcriber=MetaTranscriber(run.client, guard), extractor=extractor,
         segmenter=MetaSegmenter(run.client, guard), reader=reader,
         catalogue=run.catalogue, language_bias=LANGUAGES[lang], keywords=keywords, lang_hint=lang,
-        max_provider_calls=calls, top_k=run.top_k,
+        max_provider_calls=calls, top_k=run.top_k, second_reader=second_reader,
     )
     wall_s = round(time.monotonic() - start, 1)
     (run.reports / f"report_{name}.json").write_text(report.model_dump_json(indent=2) + "\n", "utf-8")
@@ -147,6 +159,7 @@ def intake(run: Run, name: str, audio: bytes, images: list[tuple[bytes, str]],
     line = {"run": name, "at": datetime.now(UTC).isoformat(timespec="seconds"),
             "reader": "spark" if run.open_client is None else run.open_client.provider,
             "extractor": "spark" if run.glimmer_client is None else "glimmer",
+            "second_reader": None if run.second_client is None else run.second_client.provider,
             "calls": report.calls,
             "spend_usd": str(report.spend_usd), "wall_s": wall_s,
             "claim_request_ms": claim_timed.latencies_ms,
@@ -203,6 +216,9 @@ def main() -> None:
     parser.add_argument("--glimmer-url", default=os.environ.get("GLIMMER_URL"),
                         help="the tuned Glimmer server's base URL (/extract is added to it) "
                              "(default: GLIMMER_URL)")
+    parser.add_argument("--second-reader", choices=("none", "fireworks"), default="none",
+                        help="second label reader: Muse Spark Open on Fireworks re-reads packs Spark 1.3 "
+                             "still can't read after its zoom (public photos only)")
     args = parser.parse_args()
     if args.case and not args.voice:
         sys.exit("--case needs --voice")
@@ -243,6 +259,18 @@ def main() -> None:
                                             or parsed.password is not None))
                 or (port is not None and port != 443)):
             sys.exit(f"{host or 'missing URL'} is not an https:// URL on a .modal.run host.")
+    if args.second_reader == "fireworks":
+        if not args.case:
+            sys.exit("--second-reader fireworks needs --case: "
+                     "only a staged case's public photos may go to Fireworks")
+        if args.reader != "spark":
+            sys.exit("--second-reader fireworks needs --reader spark: "
+                     "the first reader stays Spark 1.3")
+        for path in args.photo:  # checked before any key is read or client built
+            resolved = Path(path).resolve()
+            if not any(resolved.is_relative_to(folder.resolve()) for folder in OPEN_WEIGHT_PHOTOS):
+                sys.exit(f"{path} is not a public photo that may go to Fireworks "
+                         "(docs/DATA_HANDLING.md). Ahmed's own media never go there.")
     day = datetime.now(UTC).strftime("%Y-%m-%d")
     run = Run(SpendGuard(LEDGER, cap_usd=Decimal(args.cap)),
               MetaClient(api_key=os.environ.get("MODEL_API_KEY") or keychain("META_API_KEY")),
@@ -260,6 +288,10 @@ def main() -> None:
         run.glimmer_client = OpenWeightClient(
             api_key=os.environ.get("MODAL_PROXY_TOKEN") or keychain("MODAL_PROXY_TOKEN"),
             base_url=args.glimmer_url, provider="modal", timeout=GLIMMER_TIMEOUT_S)
+    if args.second_reader == "fireworks":
+        run.second_client = OpenWeightClient(
+            api_key=os.environ.get("FIREWORKS_API_KEY") or keychain("FIREWORKS_API_KEY"),
+            base_url=PRESETS["fireworks"]["base_url"], provider="fireworks")
     run.reports.mkdir(parents=True, exist_ok=True)
     run.briefs.mkdir(parents=True, exist_ok=True)
     start = run.ledger.total_usd
diff --git a/tests/unit/test_b28_extra.py b/tests/unit/test_b28_extra.py
new file mode 100644
index 0000000..16ddde7
--- /dev/null
+++ b/tests/unit/test_b28_extra.py
@@ -0,0 +1,168 @@
+"""Batch 28 gaps the contract leaves: check order, canonical names, units, crops, re-photo, runs line."""
+
+import hashlib
+import importlib.util
+import json
+from decimal import Decimal
+from pathlib import Path
+
+from anamnesis.agent import run_intake
+from anamnesis.core.catalogue import load_catalogue
+from anamnesis.providers import ProviderTrace
+from anamnesis.providers.meta import MetaClient
+from anamnesis.providers.openweight import PRESETS, OpenWeightClient
+from anamnesis.providers.spend import SpendGuard
+from anamnesis.review import add_photo, new_review, request_photo
+from anamnesis.schema import AudioTurn
+from anamnesis.schema.report import AgentAction
+from tests.contract.test_b19_brief import (
+    AUDIO,
+    PHOTO,
+    RC,
+    Extractor,
+    Reader,
+    Segmenter,
+    Transcriber,
+    claim,
+    mg,
+    png,
+    reading,
+    region_on,
+    st,
+)
+
+ROOT = Path(__file__).resolve().parents[2]
+CAT = load_catalogue()
+TURNS = [AudioTurn(turn_id="turn-c1", start_ms=0, end_ms=3000, transcript="I take Concor 5 mg once a day.")]
+CONCOR = claim("c1", "Concor", intake=mg("bisoprolol", 5), per_day="1")
+PARTIAL = reading(label="Con", readability="partial")
+CONCOR_5 = reading(label="Concor 5 mg\nBisoprolol fumarate", strength=st(mg("bisoprolol", 5)))
+
+
+class SecondReader(Reader):
+    def read(self, image, region, *, mime, cropped=False):
+        self.seen.setdefault(region.region_id, image)
+        answer = self.script[region.region_id].pop(0)
+        return answer.model_copy(update={"region_id": region.region_id}), ProviderTrace(
+            call_id="second", model_id="fixture:second", latency_ms=1, input_tokens=0,
+            output_tokens=0, cost_usd=Decimal("0.002"))
+
+
+class ElsewhereReader(SecondReader):
+    def read(self, image, region, *, mime, cropped=False):
+        found, trace = super().read(image, region, mime=mime, cropped=cropped)
+        return found.model_copy(update={"region_id": "elsewhere-0"}), trace
+
+
+def run(reads, second=None, regions=(RC,), claims=(CONCOR,), **kw):
+    by_sha = {RC.image_sha256: list(regions)}
+    report = run_intake(AUDIO[0], [(PHOTO, "image/png")], transcriber=Transcriber(TURNS),
+                        extractor=Extractor(list(claims)), segmenter=Segmenter(by_sha),
+                        reader=Reader(reads), catalogue=CAT, second_reader=second, **kw)
+    return report
+
+
+def steps_for(report, region):
+    return [(step.action, step.outcome) for step in report.steps if step.target == region.region_id]
+
+
+def test_a_second_reading_for_another_region_is_refused_before_the_readable_check():
+    second = ElsewhereReader({RC.region_id: [reading(label="Co", readability="unreadable")]})
+    report = run({RC.region_id: [PARTIAL, PARTIAL]}, second)
+    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "error: reading for another region")
+    assert report.observations[0].readability.value == "partial"
+
+
+def test_a_partial_second_with_other_ingredients_is_not_a_conflict():
+    first = reading(label="Concor", readability="partial").model_copy(update={"inn": "bisoprolol"})
+    other = reading(label="Panadol 500 mg", strength=st(mg("paracetamol", 500)), readability="partial")
+    report = run({RC.region_id: [first, first]}, SecondReader({RC.region_id: [other]}))
+    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "partial")
+    assert report.observations[0].readability.value == "partial"
+    assert report.observations[0].inn == "bisoprolol"
+
+
+def test_a_curated_alias_agrees_through_the_canonical_inn():
+    first = reading(label="Pan", readability="partial").model_copy(update={"inn": "acetaminophen"})
+    panadol = reading(label="Panadol 500 mg\nParacetamol", strength=st(mg("paracetamol", 500)))
+    report = run({RC.region_id: [first, first]}, SecondReader({RC.region_id: [panadol]}))
+    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "readable")
+    assert report.observations[0].readability.value == "readable"
+
+
+def test_a_unit_difference_keeps_the_first():
+    first = reading(label="Concor 5", strength=st(mg("bisoprolol", 5)), readability="partial")
+    other_unit = reading(label="Concor 5 mcg", strength=st(mg("bisoprolol", 5, "mcg")))
+    report = run({RC.region_id: [first, first]}, SecondReader({RC.region_id: [other_unit]}))
+    assert report.observations[0].readability.value == "partial"
+    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "conflict: kept the first reading")
+
+
+def test_release_alone_does_not_make_a_conflict():
+    first = reading(label="Concor 5", strength=st(mg("bisoprolol", 5)), readability="partial")
+    immediate = reading(label="Concor 5 mg", strength=st(mg("bisoprolol", 5), release="immediate"))
+    report = run({RC.region_id: [first, first]}, SecondReader({RC.region_id: [immediate]}))
+    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "readable")
+    assert report.observations[0].readability.value == "readable"
+
+
+def test_a_failed_second_crop_keeps_the_first(monkeypatch):
+    import anamnesis.agent.loop as loop
+
+    real_cut = loop.crop_region
+    calls = []
+
+    def third_cut_fails(image, region, margin=0.10):
+        calls.append(region.region_id)
+        if len(calls) == 3:
+            raise ValueError("crop failed")
+        return real_cut(image, region, margin)
+
+    monkeypatch.setattr(loop, "crop_region", third_cut_fails)
+    report = run({RC.region_id: [PARTIAL, PARTIAL]}, SecondReader({RC.region_id: [CONCOR_5]}))
+    assert steps_for(report, RC)[-1] == (AgentAction.SECOND_READ, "error: crop failed")
+    assert report.observations[0].readability.value == "partial"
+
+
+def test_a_re_photo_conflict_keeps_the_first_but_still_supersedes():
+    report = run({RC.region_id: [PARTIAL, PARTIAL]})
+    review = request_photo(new_review(report), report, "o0")
+    retake = png(600, 300, colour=(190, 190, 190))
+    region = region_on(retake, (10, 20, 139, 279), 0, 0.95)
+    first = reading(label="Concor 5", strength=st(mg("bisoprolol", 5)), readability="partial")
+    panadol = reading(label="Panadol 500 mg\nParacetamol", strength=st(mg("paracetamol", 500)))
+    updated, _ = add_photo(report, review, "r1", (retake, "image/png"), [(PHOTO, "image/png")], AUDIO,
+                           segmenter=Segmenter({hashlib.sha256(retake).hexdigest(): [region]}),
+                           reader=Reader({region.region_id: [first, first]}), catalogue=CAT,
+                           second_reader=SecondReader({region.region_id: [panadol]}))
+    assert updated.superseded == ["o0"]
+    assert updated.observations[-1].readability.value == "partial"
+    assert [(s.action, s.outcome) for s in updated.steps if s.target == region.region_id][-1] == (
+        AgentAction.SECOND_READ, "conflict: kept the first reading")
+
+
+def _intake_live():
+    spec = importlib.util.spec_from_file_location("intake_live_b28_extra", ROOT / "scripts/intake_live.py")
+    module = importlib.util.module_from_spec(spec)
+    spec.loader.exec_module(module)
+    return module
+
+
+def test_runs_lines_record_the_second_reader(monkeypatch, tmp_path):
+    il = _intake_live()
+    real = run({RC.region_id: [CONCOR_5]})
+    monkeypatch.setattr(il, "run_intake", lambda *args, **kwargs: real)
+    monkeypatch.setattr(il, "render_brief", lambda *args, **kwargs: "<p>brief</p>")
+    reports, briefs = tmp_path / "reports", tmp_path / "briefs"
+    reports.mkdir()
+    briefs.mkdir()
+
+    def line_for(**clients):
+        run_ = il.Run(SpendGuard(tmp_path / "ledger.jsonl", cap_usd=Decimal(1)), MetaClient("k"),
+                      load_catalogue(), Decimal("0.25"), 3, reports, briefs, **clients)
+        il.intake(run_, "x", b"audio", [(b"img", "image/png")], "en")
+        return json.loads((reports / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
+
+    assert line_for()["second_reader"] is None
+    fireworks = OpenWeightClient("k", base_url=PRESETS["fireworks"]["base_url"], provider="fireworks")
+    assert line_for(second_client=fireworks)["second_reader"] == "fireworks"
```
