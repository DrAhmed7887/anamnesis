# Batch 31 audit: double-check another Muse session's build, read-only

You are auditing code that another Muse Code session just wrote for batch 31 of Anamnesis. Work read-only:
- don't create, edit or delete any file;
- run no git command that changes state;
- make no network call, use no API key, and run no `modal` command;
- don't open anything under `evidence/` or `finetune/data*`, nor any `.env` file.

## 1. Goal
The audit is done ONLY when your reply has the three sections in §3, and every finding cites a file and line you opened, or a line of the diff below.

## 2. What the code must do
SPEC.md §8, the subsection "The follow-up by itself (`follow_up`, batch 31)": open it in the repository. `follow_up` asks the patient for every photo the brief is missing, takes the replies through `add_photo`, and leaves a draft for the clinician. Code fixes the targets, their order and when to stop, and every message is a template.

The contract is `tests/contract/test_b31_follow_up.py`, and the build passes it. Look for what it doesn't catch:
- any way the loop runs on without end, or asks a target that has an open request;
- a reply that changes evidence it shouldn't, or images that drift from the report's `intake_id`;
- spend across rounds;
- any path to an approved review, or to text that isn't a template;
- a refusal that changes something;
- the brief line and its refusals.

## 3. Reply
1. **Verdict:** one line.
2. **Findings:** numbered, each with severity, file:line, the evidence and a fix.
3. **What you checked and found fine:** a short list.

Keep it under 500 words.

## The build: `git diff HEAD` (uncommitted in the batch worktree; this copy of the repository is at the contract commit)
```diff
diff --git a/anamnesis/brief.py b/anamnesis/brief.py
index e709512..f9cb431 100644
--- a/anamnesis/brief.py
+++ b/anamnesis/brief.py
@@ -96,11 +96,18 @@ def _voice_line(report: ReconciliationReport, audio: Image | None) -> str:
 
 def render_brief(
     report: ReconciliationReport, images: list[Image], audio: Image | None, catalogue,
-    review=None,
+    review=None, follow_up=None,
 ) -> str:
     """Render one deterministic self-contained HTML page for a finished report."""
     if review is not None and review.intake_id != report.intake_id:
         raise ValueError("review is for another report")
+    if follow_up:
+        if review is None:
+            raise ValueError("a follow-up log needs its review")
+        known = {item.request_id for item in review.requests}
+        for step in follow_up:
+            if step.request_id not in known:
+                raise ValueError("a follow-up step names no request of the review")
     prepared = _checked_prepared(report, images, audio)
     claims = {claim.claim_id: claim for claim in report.claims}
     observations = {obs.observation_id: obs for obs in report.observations}
@@ -121,7 +128,7 @@ def render_brief(
         '<head><meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width, initial-scale=1">'
         f"<title>{BRIEF_TITLE}</title><style>{_STYLE}</style></head>",
-        "<body>", _scope_html(review),
+        "<body>", _scope_html(review, follow_up),
     ]
     for name in SECTION_ORDER:
         body = "".join(sections[name]) or f"<p>{NONE_TEXT}</p>"
diff --git a/anamnesis/brief_html.py b/anamnesis/brief_html.py
index 664fd71..44d6fc0 100644
--- a/anamnesis/brief_html.py
+++ b/anamnesis/brief_html.py
@@ -7,7 +7,7 @@ from anamnesis.agent.crop import crop_region
 from anamnesis.core.overlap import cross_medication
 from anamnesis.core.reconcile import claim_identity_conflict, pack_identity_conflict
 from anamnesis.schema import DiscrepancyType as D
-from anamnesis.schema.review import RequestKind, RequestStatus, ReviewStatus
+from anamnesis.schema.review import FollowUpOutcome, RequestKind, RequestStatus, ReviewStatus
 from anamnesis.schema.templates import (
     BRIEF_TITLE,
     CATALOGUE_CODES_ATC,
@@ -24,6 +24,7 @@ from anamnesis.schema.templates import (
     FIELD_REGIMEN,
     FIELD_STATUS,
     FIELD_STRENGTH,
+    FOLLOW_UP_DONE,
     HEARD_IN,
     HEARD_TURN,
     MENTIONED_NOT_PHOTOGRAPHED,
@@ -473,9 +474,13 @@ def _review_status(review) -> str:
     return REVIEW_WAITING.format(n=open_count)
 
 
-def _scope_html(review=None) -> str:
+def _scope_html(review=None, follow_up=None) -> str:
     lines = "".join(f"<p>{line}</p>" for line in SCOPE_LINES)
     lines += f'<p id="review-status">{_review_status(review)}</p>'
+    if follow_up:
+        asked = len(follow_up)
+        received = sum(1 for step in follow_up if step.outcome is FollowUpOutcome.ANSWERED)
+        lines += f'<p id="follow-up">{FOLLOW_UP_DONE.format(asked=asked, received=received)}</p>'
     return f'<header id="scope"><h1>{BRIEF_TITLE}</h1>{lines}</header>'
 
 
diff --git a/anamnesis/review.py b/anamnesis/review.py
index b8ff4b9..c08b233 100644
--- a/anamnesis/review.py
+++ b/anamnesis/review.py
@@ -14,7 +14,15 @@ from anamnesis.agent.session import IntakeSession
 from anamnesis.core.reconcile import reconcile_all
 from anamnesis.schema import DiscrepancyType as D
 from anamnesis.schema.report import AgentAction, AgentStep, ReconciliationReport
-from anamnesis.schema.review import PhotoRequest, RequestKind, RequestStatus, Review, ReviewStatus
+from anamnesis.schema.review import (
+    FollowUpOutcome,
+    FollowUpStep,
+    PhotoRequest,
+    RequestKind,
+    RequestStatus,
+    Review,
+    ReviewStatus,
+)
 from anamnesis.schema.templates import REQUEST_NOT_PHOTOGRAPHED, REQUEST_UNREADABLE
 
 Image = tuple[bytes, str]
@@ -172,3 +180,59 @@ def approve(review: Review, report: ReconciliationReport) -> Review:
         raise ValueError("an open request remains")
     return Review(intake_id=review.intake_id, status=ReviewStatus.APPROVED,
                   requests=list(review.requests))
+
+
+def follow_up(
+    report: ReconciliationReport, review: Review, images: list[Image], audio: Image | None,
+    *, reply, segmenter, reader, catalogue, second_reader=None,
+    concepts: tuple[str, ...] = SAM_CONCEPTS, top_k: int = 3, max_rounds: int = 2,
+) -> tuple[ReconciliationReport, Review, list[Image], list[FollowUpStep]]:
+    """Ask the patient for every missing photo, take the replies, leave a draft (SPEC §8)."""
+    if review.intake_id != report.intake_id:
+        raise ValueError("review is for another report")
+    if review.status is ReviewStatus.APPROVED:
+        raise ValueError("review is approved")
+    if max_rounds < 1:
+        raise ValueError("max_rounds is below 1")
+    prepared = _prepare(images)
+    audio_bytes = audio[0] if audio is not None else None
+    if _intake_id(audio_bytes, [item for item, _, _ in prepared]) != report.intake_id:
+        raise ValueError("media do not match the report")
+    given = list(images)
+    log: list[FollowUpStep] = []
+    for round_no in range(1, max_rounds + 1):
+        waiting = {
+            item.target_id for item in review.requests if item.status is RequestStatus.OPEN
+        }
+        targets = [entry for entry in requestable(report) if entry[1] not in waiting]
+        if not targets:
+            break
+        for kind, target in targets:
+            if (kind, target) not in requestable(report):
+                continue
+            review = request_photo(review, report, target)
+            asked = review.requests[-1]
+            photo = reply(asked, request_message(report, asked))
+            if photo is None:
+                log.append(FollowUpStep(round=round_no, request_id=asked.request_id,
+                                        target_id=target, kind=kind,
+                                        outcome=FollowUpOutcome.NO_REPLY))
+                continue
+            try:
+                report, review = add_photo(
+                    report, review, asked.request_id, photo, given, audio,
+                    segmenter=segmenter, reader=reader, catalogue=catalogue,
+                    second_reader=second_reader, concepts=concepts, top_k=top_k,
+                )
+            except ValueError as exc:
+                if str(exc) != "photo was already given":
+                    raise
+                log.append(FollowUpStep(round=round_no, request_id=asked.request_id,
+                                        target_id=target, kind=kind,
+                                        outcome=FollowUpOutcome.DUPLICATE))
+                continue
+            given.append(photo)
+            log.append(FollowUpStep(round=round_no, request_id=asked.request_id,
+                                    target_id=target, kind=kind,
+                                    outcome=FollowUpOutcome.ANSWERED))
+    return report, review, given, log
diff --git a/anamnesis/schema/review.py b/anamnesis/schema/review.py
index a98166c..540c4a2 100644
--- a/anamnesis/schema/review.py
+++ b/anamnesis/schema/review.py
@@ -25,6 +25,12 @@ class ReviewStatus(StrEnum):
     APPROVED = "approved"
 
 
+class FollowUpOutcome(StrEnum):
+    ANSWERED = "answered"
+    NO_REPLY = "no_reply"
+    DUPLICATE = "duplicate"
+
+
 class PhotoRequest(BaseModel):
     model_config = ConfigDict(extra="forbid")
 
@@ -54,3 +60,13 @@ class Review(BaseModel):
         if waiting != any(r.status is RequestStatus.OPEN for r in self.requests):
             raise ValueError("awaiting_patient exactly when a request is open")
         return self
+
+
+class FollowUpStep(BaseModel):
+    model_config = ConfigDict(extra="forbid")
+
+    round: Annotated[int, Field(ge=1)]
+    request_id: NonEmptyStr
+    target_id: NonEmptyStr
+    kind: RequestKind
+    outcome: FollowUpOutcome
diff --git a/anamnesis/schema/templates.py b/anamnesis/schema/templates.py
index 4854018..2516969 100644
--- a/anamnesis/schema/templates.py
+++ b/anamnesis/schema/templates.py
@@ -128,6 +128,7 @@ REVIEW_REPLACED = "Replaced by a newer photo."
 REQUEST_UNREADABLE = ("Please send one new photo of this medicine pack, with the label facing the camera, "
                       "in good light.")
 REQUEST_NOT_PHOTOGRAPHED = "Please send one photo of the pack of the medicine you mentioned as “{name}”."
+FOLLOW_UP_DONE = "Anamnesis sent the follow-up itself: new photos asked for {asked}, received {received}."
 
 TIMELINE_HEADING = "How it got here"
 TIMELINE_COLUMNS = ("#", "Step", "Target", "Outcome", "Model", "Tokens in", "Tokens out", "Time", "Cost")
diff --git a/tests/unit/test_b31_extra.py b/tests/unit/test_b31_extra.py
new file mode 100644
index 0000000..bcc2360
--- /dev/null
+++ b/tests/unit/test_b31_extra.py
@@ -0,0 +1,203 @@
+"""Extra offline checks for batch 31 follow-up (SPEC §8, "The follow-up by itself")."""
+
+import hashlib
+import io
+from decimal import Decimal
+
+import pytest
+from PIL import Image as PILImage
+
+from anamnesis.agent.loop import _intake_id, _prepare
+from anamnesis.brief import render_brief
+from anamnesis.core.catalogue import load_catalogue
+from anamnesis.providers import ProviderTrace
+from anamnesis.providers.spark import LabelReading
+from anamnesis.review import follow_up, new_review, requestable
+from anamnesis.schema import AudioTurn, Finding, ImageRegion, PatientClaim
+from anamnesis.schema import DiscrepancyType as D
+from anamnesis.schema.medication import PackObservation
+from anamnesis.schema.report import AgentAction, AgentStep, ReconciliationReport
+from anamnesis.schema.review import FollowUpOutcome, FollowUpStep, RequestKind, RequestStatus, ReviewStatus
+from anamnesis.schema.templates import FOLLOW_UP_DONE, QUESTION_FOR, TEMPLATES
+
+CAT = load_catalogue()
+GOT, NONE, AGAIN = FollowUpOutcome.ANSWERED, FollowUpOutcome.NO_REPLY, FollowUpOutcome.DUPLICATE
+
+
+def _png(w, h, colour):
+    buf = io.BytesIO()
+    PILImage.new("RGB", (w, h), colour).save(buf, "PNG")
+    return buf.getvalue()
+
+
+PHOTO = _png(600, 300, (200, 200, 200))
+PHOTO2 = _png(400, 300, (180, 190, 200))
+IMAGES = [(PHOTO, "image/png")]
+GIVE2 = (PHOTO2, "image/png")
+AUDIO = (b"RIFF b31 extra fixture", "audio/wav")
+SHA2 = hashlib.sha256(PHOTO2).hexdigest()
+
+
+def _region(image, box, obj):
+    sha = hashlib.sha256(image).hexdigest()
+    w, h = PILImage.open(io.BytesIO(image)).size
+    return ImageRegion(region_id=f"{sha[:12]}-{obj}", image_sha256=sha, object_id=obj,
+                       x1=box[0], y1=box[1], x2=box[2], y2=box[3], frame_w=w, frame_h=h,
+                       confidence=0.9)
+
+
+R0 = _region(PHOTO, (10, 20, 139, 279), 0)
+R2 = _region(PHOTO2, (20, 20, 379, 279), 0)
+DARK = LabelReading(region_id="x", readability="unreadable")
+
+
+def _trace(cid):
+    return ProviderTrace(call_id=cid, model_id="fixture:test", latency_ms=1, input_tokens=0,
+                         output_tokens=0, cost_usd=Decimal("0.001"))
+
+
+class _Segmenter:
+    """Regions per photo sha, but only for the allowed concepts; records every call."""
+
+    def __init__(self, by_sha, concepts=None):
+        self.by_sha, self.concepts, self.seen = dict(by_sha), concepts, []
+
+    def segment(self, image, concept, *, mime):
+        self.seen.append((hashlib.sha256(image).hexdigest(), concept))
+        if self.concepts is not None and concept not in self.concepts:
+            return [], _trace(f"s-{len(self.seen)}")
+        sha = hashlib.sha256(image).hexdigest()
+        return list(self.by_sha.get(sha, [])), _trace(f"s-{len(self.seen)}")
+
+
+class _Reader:
+    def __init__(self, script):
+        self.script, self.seen = {key: list(value) for key, value in script.items()}, []
+
+    def read(self, image, region, *, mime, cropped=False):
+        self.seen.append(region.region_id)
+        reading = self.script[region.region_id].pop(0)
+        return reading.model_copy(update={"region_id": region.region_id}), _trace(f"r-{len(self.seen)}")
+
+
+class _Patient:
+    def __init__(self, *answers):
+        self.answers, self.asked = list(answers), []
+
+    def __call__(self, request, message):
+        self.asked.append((request, message))
+        return self.answers.pop(0) if self.answers else None
+
+
+def _finding(fid, kind, claim_id=None, observation_id=None, audio=(), visual=()):
+    return Finding.model_validate({
+        "finding_id": fid, "type": kind, "claim_id": claim_id,
+        "observation_id": observation_id, "audio_evidence": list(audio),
+        "visual_evidence": list(visual),
+        "needs_clinician_review": kind is not D.MATCH,
+        "clinician_note": TEMPLATES[kind], "patient_question_id": QUESTION_FOR[kind],
+    })
+
+
+def _report(with_claim=True):
+    prepared = _prepare(IMAGES)
+    intake = _intake_id(AUDIO[0], [photo for photo, _, _ in prepared])
+    claims, findings = [], [_finding("f0", D.UNREADABLE_SOURCE, observation_id="o0",
+                                     visual=[R0.region_id])]
+    if with_claim:
+        claims.append(PatientClaim(claim_id="c9", name_text="Sortis", status="active",
+                                   audio_evidence=["turn-0"]))
+        findings.append(_finding("f1", D.MISSING_MODALITY, claim_id="c9", audio=["turn-0"]))
+    return ReconciliationReport(
+        intake_id=intake,
+        turns=[AudioTurn(turn_id="turn-0", start_ms=0, end_ms=1000, transcript="Sortis")],
+        claims=claims, regions=[R0],
+        observations=[PackObservation(observation_id="o0", readability="unreadable",
+                                      visual_evidence=[R0.region_id])],
+        findings=findings,
+        steps=[AgentStep(n=0, action=AgentAction.RECONCILE, target="all", outcome="done")],
+        calls=0, spend_usd=Decimal(0))
+
+
+def _run(report, patient, **kw):
+    kw.setdefault("segmenter", _Segmenter({SHA2: [R2]}))
+    kw.setdefault("reader", _Reader({R2.region_id: [DARK, DARK]}))
+    return follow_up(report, new_review(report), list(IMAGES), AUDIO, reply=patient,
+                     catalogue=CAT, **kw)
+
+
+def test_the_log_parses_plain_strings():
+    step = FollowUpStep(round=2, request_id="r1", target_id="c9", kind="not_photographed",
+                        outcome="no_reply")
+    assert step.kind is RequestKind.NOT_PHOTOGRAPHED and step.outcome is NONE
+    assert FollowUpOutcome("duplicate") is AGAIN
+
+
+def test_unanswered_targets_wait_and_later_rounds_stop():
+    report = _report()
+    assert requestable(report) == [(RequestKind.UNREADABLE, "o0"),
+                                   (RequestKind.NOT_PHOTOGRAPHED, "c9")]
+    patient = _Patient(None, None, None)
+    new, review, given, log = _run(report, patient, max_rounds=3)
+    assert [(s.round, s.target_id, s.outcome) for s in log] == [(1, "o0", NONE), (1, "c9", NONE)]
+    assert len(patient.asked) == 2  # round 2 has no targets, so the run stops
+    assert review.status is ReviewStatus.AWAITING_PATIENT
+    assert [r.status for r in review.requests] == [RequestStatus.OPEN, RequestStatus.OPEN]
+    assert (new, given) == (report, IMAGES)
+
+
+def test_a_rephoto_still_unreadable_is_asked_again_next_round():
+    new, review, given, log = _run(_report(), _Patient(GIVE2, None, None), max_rounds=2)
+    assert [(s.round, s.target_id, s.outcome) for s in log] == [(1, "o0", GOT), (1, "c9", NONE),
+                                                                (2, "o1", NONE)]
+    assert [s.request_id for s in log] == ["r1", "r2", "r3"]
+    assert [s.kind for s in log] == [RequestKind.UNREADABLE, RequestKind.NOT_PHOTOGRAPHED,
+                                     RequestKind.UNREADABLE]
+    assert [(r.request_id, r.status, r.photo_index) for r in review.requests] == [
+        ("r1", RequestStatus.ANSWERED, 2), ("r2", RequestStatus.OPEN, None),
+        ("r3", RequestStatus.OPEN, None)]
+    assert given == [*IMAGES, GIVE2]
+    assert review.intake_id == new.intake_id != _report().intake_id
+
+
+def test_a_repeat_of_an_answering_photo_is_a_duplicate_and_goes_to_no_model():
+    segmenter = _Segmenter({SHA2: [R2]})
+    new, review, given, log = _run(_report(), _Patient(GIVE2, None, GIVE2), max_rounds=2,
+                                   segmenter=segmenter)
+    assert [(s.target_id, s.outcome) for s in log] == [("o0", GOT), ("c9", NONE), ("o1", AGAIN)]
+    assert {sha for sha, _ in segmenter.seen} == {SHA2}
+    assert [r.status for r in review.requests] == [RequestStatus.ANSWERED, RequestStatus.OPEN,
+                                                   RequestStatus.OPEN]
+    assert review.status is ReviewStatus.AWAITING_PATIENT
+    assert given == [*IMAGES, GIVE2]
+    assert (RequestKind.UNREADABLE, "o1") in requestable(new)
+
+
+def test_custom_concepts_reach_the_photo_calls():
+    seen = {}
+    for name, kw in (("default", {}), ("package-only", {"concepts": ("package",)})):
+        segmenter = _Segmenter({SHA2: [R2]}, concepts={"package"})
+        _, _, _, log = _run(_report(with_claim=False), _Patient(GIVE2), max_rounds=1,
+                             segmenter=segmenter, **kw)
+        assert [s.outcome for s in log] == [GOT]
+        seen[name] = [concept for _, concept in segmenter.seen]
+    assert seen == {"default": ["medicine box", "label", "package"], "package-only": ["package"]}
+
+
+def test_a_negative_round_refuses_before_asking_anybody():
+    report = _report()
+    patient = _Patient(GIVE2)
+    with pytest.raises(ValueError):
+        _run(report, patient, max_rounds=-1)
+    assert patient.asked == []
+
+
+def test_the_brief_counts_a_mixed_log_inside_the_scope_header():
+    new, review, given, log = _run(_report(), _Patient(GIVE2, None, GIVE2), max_rounds=2)
+    assert len(log) == 3
+    page = render_brief(new, given, AUDIO, CAT, review=review, follow_up=log)
+    line = FOLLOW_UP_DONE.format(asked=3, received=1)
+    assert f'<p id="follow-up">{line}</p>' in page
+    assert page.index('id="follow-up"') < page.index("</header>")
+    plain = render_brief(new, given, AUDIO, CAT, review=review)
+    assert 'id="follow-up"' not in plain
```
