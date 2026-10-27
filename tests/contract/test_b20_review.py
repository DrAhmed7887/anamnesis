"""Batch 20 contract, part 2: the clinician signs off, and can ask the patient for one new photo first. Written by the
CEO; Muse must not edit it.

SPEC §8 and the §7 additions. From the legal-agent workshop (meta-models, 27 Oct): the run pauses for a person, the
person releases new evidence, the run resumes for that one item only, and nothing is final until a human approves.
Here the clinician chooses and the code checks the choice is allowed; no model chooses anything. Only the new photo
goes to a model, the answered pack is replaced only when the new photo gave a reading, and a brief or an approval is
bound to the exact report (its intake_id).
"""

import hashlib
import io
from decimal import Decimal
from html.parser import HTMLParser

import pytest
from PIL import Image
from pydantic import ValidationError

from anamnesis.agent import run_intake
from anamnesis.brief import coverage_lines, render_brief
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.guardrails import assert_no_advice
from anamnesis.providers import ProviderTrace
from anamnesis.providers.spark import LabelReading
from anamnesis.review import (
    add_photo,
    approve,
    new_review,
    request_message,
    request_photo,
    requestable,
    withdraw,
)
from anamnesis.schema import AudioTurn, DoseRegimen, ImageRegion, IngredientAmount, PatientClaim, Strength
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.report import AgentAction, ReconciliationReport
from anamnesis.schema.review import PhotoRequest, RequestKind, RequestStatus, Review, ReviewStatus

CAT = load_catalogue()
DRAFT = "Draft: not yet reviewed by a clinician."
APPROVED = "Reviewed and approved by the clinician."
REQUESTED = "A new photo has been requested from the patient."
REPLACED = "Replaced by a newer photo."
UNREADABLE_MESSAGE = ("Please send one new photo of this medicine pack, with the label facing the camera, "
                      "in good light.")


# --- a small DOM, from the standard library parser ------------------------------------------------------------

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []

    def walk(self):
        for child in self.children:
            if isinstance(child, Node):
                yield child
                yield from child.walk()

    def find_all(self, tag=None, **attrs):
        return [node for node in self.walk() if (tag is None or node.tag == tag)
                and all(node.attrs.get(key.replace("_", "-")) == value for key, value in attrs.items())]

    def by_id(self, ident):
        found = [node for node in self.walk() if node.attrs.get("id") == ident]
        assert len(found) == 1, f"{len(found)} elements with id {ident!r}"
        return found[0]

    def text(self):
        parts = [child.text() if isinstance(child, Node) else child for child in self.children
                 if not (isinstance(child, Node) and child.tag in ("script", "style"))]
        return " ".join(" ".join(parts).split())


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = self.current = Node("#root", [], None)
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in VOID:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        self.current.children.append(Node(tag, attrs, self.current))

    def handle_endtag(self, tag):
        node = self.current
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.current = node.parent

    def handle_data(self, data):
        self.current.children.append(data)


# --- fakes with the live adapters' interfaces --------------------------------------------------------------

def png(w, h, colour):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), colour).save(buf, "PNG")
    return buf.getvalue()


def region_on(image, box, obj):
    sha = hashlib.sha256(image).hexdigest()
    w, h = Image.open(io.BytesIO(image)).size
    return ImageRegion(region_id=f"{sha[:12]}-{obj}", image_sha256=sha, object_id=obj, x1=box[0], y1=box[1],
                       x2=box[2], y2=box[3], frame_w=w, frame_h=h, confidence=0.9)


def trace(cid):
    return ProviderTrace(call_id=cid, model_id="fixture:test", latency_ms=1, input_tokens=0, output_tokens=0,
                         cost_usd=Decimal("0.001"))


class Transcriber:
    def transcribe(self, audio, *, language_bias=None, keywords=None, lang_hint=None):
        return list(TURNS), trace("voice")


class Extractor:
    def extract(self, turns):
        return list(CLAIMS), trace("claims")


class Segmenter:
    """The regions of each photo, keyed by its sha256; records which photos it was shown."""

    def __init__(self, by_sha):
        self.by_sha, self.seen = dict(by_sha), []

    def segment(self, image, concept, *, mime):
        sha = hashlib.sha256(image).hexdigest()
        self.seen.append(sha)
        return list(self.by_sha.get(sha, [])), trace(f"sam-{len(self.seen)}")


class Reader:
    """Answers from a script of readings per region, in call order; records which regions it read."""

    def __init__(self, script):
        self.script, self.seen = {key: list(value) for key, value in script.items()}, []

    def read(self, image, region, *, mime, cropped=False):
        self.seen.append(region.region_id)
        reading = self.script[region.region_id].pop(0)
        return reading.model_copy(update={"region_id": region.region_id}), trace(f"read-{len(self.seen)}")


def mg(inn, amount):
    return IngredientAmount(inn=inn, amount=Decimal(str(amount)), unit="mg")


def reading(label=None, strength=None, readability="readable"):
    return LabelReading(region_id="r", label_text=label, strength=strength, readability=readability)


# --- the patient: Concor photographed, one pack nobody can read, Beloc-Zok mentioned but not photographed ------

PHOTO = png(600, 300, (200, 200, 200))
PHOTO2 = png(400, 300, (180, 190, 200))   # the re-photo: it was the Beloc-Zok
RC = region_on(PHOTO, (10, 20, 139, 279), 0)
RU = region_on(PHOTO, (160, 20, 289, 279), 1)
R2 = region_on(PHOTO2, (20, 20, 379, 279), 0)
SHA2 = hashlib.sha256(PHOTO2).hexdigest()
AUDIO = (b"RIFF fixture voice note", "audio/wav")
IMAGES = [(PHOTO, "image/png")]
TURNS = [
    AudioTurn(turn_id="turn-0", start_ms=0, end_ms=4000, transcript="I use Concor 5 mg once a day."),
    AudioTurn(turn_id="turn-1", start_ms=4000, end_ms=9000, transcript="And Beloc-Zok, 50 mg twice a day."),
    AudioTurn(turn_id="turn-2", start_ms=9000, end_ms=13000, transcript="I stopped Panadol last month."),
]
CLAIMS = [
    PatientClaim(claim_id="c1", name_text="Concor", intake_amount=mg("Concor", 5),
                 regimen=DoseRegimen(intakes_per_day=Decimal(1)), status="active", audio_evidence=["turn-0"]),
    PatientClaim(claim_id="c2", name_text="Beloc-Zok", intake_amount=mg("Beloc-Zok", 50),
                 regimen=DoseRegimen(intakes_per_day=Decimal(2)), status="active", audio_evidence=["turn-1"]),
    PatientClaim(claim_id="c3", name_text="Panadol", status="discontinued", audio_evidence=["turn-2"]),
]
BELOC_50 = reading("Beloc-Zok 50 mg\nMetoprolol succinate\nProlonged-release tablets",
                   Strength(ingredients=[mg("metoprolol succinate", 50)], per="tablet", release="modified"))


def first_intake():
    reads = {RC.region_id: [reading("Concor 5 mg\nBisoprolol fumarate",
                                    Strength(ingredients=[mg("bisoprolol fumarate", 5)], per="tablet",
                                             release="immediate"))],
             RU.region_id: [reading(readability="unreadable"), reading(readability="unreadable")]}
    return run_intake(AUDIO[0], IMAGES, transcriber=Transcriber(), extractor=Extractor(),
                      segmenter=Segmenter({RC.image_sha256: [RC, RU]}), reader=Reader(reads), catalogue=CAT)


def answer(report, review, request_id, photo=(PHOTO2, "image/png"), regions=(R2,), reads=None, **kw):
    segmenter = Segmenter({SHA2: list(regions)})
    reader = Reader(reads if reads is not None else {R2.region_id: [BELOC_50]})
    new_report, new_review_ = add_photo(report, review, request_id, photo, IMAGES, AUDIO, segmenter=segmenter,
                                        reader=reader, catalogue=CAT, **kw)
    return new_report, new_review_, segmenter, reader


def finding_for(report, *, claim_id=None, observation_id=None):
    return [f for f in report.findings if (claim_id is None or f.claim_id == claim_id)
            and (observation_id is None or f.observation_id == observation_id)]


@pytest.fixture
def report():
    return first_intake()


def test_the_fixture_is_what_the_tests_assume(report):
    assert [o.observation_id for o in report.observations] == ["o0", "o1"]
    assert report.observations[1].visual_evidence == [RU.region_id]
    assert [f.type for f in finding_for(report, observation_id="o1")] == [D.UNREADABLE_SOURCE]
    [beloc] = finding_for(report, claim_id="c2")
    assert beloc.type is D.MISSING_MODALITY and beloc.observation_id is None


# --- what can be requested ---------------------------------------------------------------------------------

def test_a_new_review_is_a_draft_with_no_requests(report):
    review = new_review(report)
    assert review == Review(intake_id=report.intake_id, status=ReviewStatus.DRAFT, requests=[])


def test_an_unreadable_pack_and_an_unphotographed_medicine_can_be_requested_in_finding_order(report):
    expected = []
    for finding in report.findings:
        if finding.type is D.UNREADABLE_SOURCE:
            expected.append((RequestKind.UNREADABLE, finding.observation_id))
        if finding.type is D.MISSING_MODALITY and finding.claim_id == "c2":
            expected.append((RequestKind.NOT_PHOTOGRAPHED, "c2"))
    assert requestable(report) == expected and len(expected) == 2


@pytest.mark.parametrize("target", ["c3", "c1", "o0", "o9", "", "turn-0"])
def test_a_stopped_medicine_a_matched_one_or_an_unknown_id_cannot_be_requested(report, target):
    review = new_review(report)
    with pytest.raises(ValueError):
        request_photo(review, report, target)


def test_a_request_opens_and_the_review_waits_for_the_patient(report):
    review = new_review(report)
    waiting = request_photo(review, report, "o1")
    assert waiting.status is ReviewStatus.AWAITING_PATIENT
    assert waiting.requests == [PhotoRequest(request_id="r1", kind=RequestKind.UNREADABLE, target_id="o1",
                                             status=RequestStatus.OPEN, photo_index=None)]
    both = request_photo(waiting, report, "c2")
    assert [(r.request_id, r.kind, r.target_id) for r in both.requests] == \
        [("r1", RequestKind.UNREADABLE, "o1"), ("r2", RequestKind.NOT_PHOTOGRAPHED, "c2")]
    assert review.status is ReviewStatus.DRAFT and review.requests == []  # inputs are never changed
    assert len(waiting.requests) == 1


def test_the_same_target_cannot_be_requested_twice_while_open(report):
    waiting = request_photo(new_review(report), report, "o1")
    with pytest.raises(ValueError):
        request_photo(waiting, report, "o1")


def test_a_review_of_another_report_is_refused(report):
    other = new_review(report).model_copy(update={"intake_id": "0" * 64})
    with pytest.raises(ValueError):
        request_photo(other, report, "o1")


def test_withdrawing_closes_a_request_and_only_an_open_one(report):
    waiting = request_photo(request_photo(new_review(report), report, "o1"), report, "c2")
    one = withdraw(waiting, "r1")
    assert [r.status for r in one.requests] == [RequestStatus.WITHDRAWN, RequestStatus.OPEN]
    assert one.status is ReviewStatus.AWAITING_PATIENT
    none = withdraw(one, "r2")
    assert none.status is ReviewStatus.DRAFT
    for request_id in ("r1", "r3"):
        with pytest.raises(ValueError):
            withdraw(none, request_id)
    assert waiting.requests[0].status is RequestStatus.OPEN


def test_a_withdrawn_target_can_be_requested_again(report):
    again = request_photo(withdraw(request_photo(new_review(report), report, "o1"), "r1"), report, "o1")
    assert [(r.request_id, r.status) for r in again.requests] == [("r1", RequestStatus.WITHDRAWN),
                                                                    ("r2", RequestStatus.OPEN)]


# --- the review's own rules --------------------------------------------------------------------------------

def open_request(request_id="r1", **kw):
    return PhotoRequest(request_id=request_id, kind=RequestKind.UNREADABLE, target_id="o1",
                        status=RequestStatus.OPEN, **kw)


@pytest.mark.parametrize("status,requests", [
    (ReviewStatus.DRAFT, [open_request()]),
    (ReviewStatus.AWAITING_PATIENT, []),
    (ReviewStatus.APPROVED, [open_request()]),
])
def test_the_status_must_agree_with_the_requests(status, requests):
    with pytest.raises(ValidationError):
        Review(intake_id="a" * 64, status=status, requests=requests)


def test_an_answered_request_has_its_photo_and_no_other_does():
    with pytest.raises(ValidationError):
        PhotoRequest(request_id="r1", kind=RequestKind.UNREADABLE, target_id="o1", status=RequestStatus.ANSWERED)
    with pytest.raises(ValidationError):
        open_request(photo_index=2)
    with pytest.raises(ValidationError):
        Review(intake_id="a" * 64, status=ReviewStatus.DRAFT, requests=[], surprise=1)


# --- the message to the patient ----------------------------------------------------------------------------

def test_the_messages_to_the_patient_are_fixed_text_and_give_no_advice(report):
    review = request_photo(request_photo(new_review(report), report, "o1"), report, "c2")
    unreadable, unphotographed = (request_message(report, r) for r in review.requests)
    assert unreadable == UNREADABLE_MESSAGE
    assert unphotographed == "Please send one photo of the pack of the medicine you mentioned as “Beloc-Zok”."
    for text in (unreadable, unphotographed):
        assert_no_advice(text)


# --- the new photo -----------------------------------------------------------------------------------------

def test_the_answer_replaces_the_unreadable_pack_and_only_the_new_photo_goes_to_a_model(report):
    before, review = report.model_dump(), request_photo(new_review(report), report, "o1")
    after, answered, segmenter, reader = answer(report, review, "r1")
    assert segmenter.seen == [SHA2] and reader.seen == [R2.region_id]
    assert after.superseded == ["o1"]
    assert [o.observation_id for o in after.observations] == ["o0", "o1", "o2"]
    assert after.observations[2].visual_evidence == [R2.region_id]
    assert not finding_for(after, observation_id="o1")
    [beloc] = finding_for(after, claim_id="c2")
    assert beloc.observation_id == "o2" and beloc.type is D.MATCH
    assert after.regions == report.regions + [R2] and after.turns == report.turns and after.claims == report.claims
    assert report.model_dump() == before and review.requests[0].status is RequestStatus.OPEN


def test_the_steps_continue_and_the_spend_adds_up(report):
    review = request_photo(new_review(report), report, "o1")
    after, _, _, _ = answer(report, review, "r1")
    assert after.steps[:len(report.steps)] == report.steps
    assert [step.n for step in after.steps] == list(range(len(after.steps)))
    new = after.steps[len(report.steps):]
    assert new[0].action is AgentAction.SEGMENT and new[0].target.startswith(SHA2[:12] + ":")
    assert [step.action for step in new] == [AgentAction.SEGMENT, AgentAction.READ, AgentAction.RECONCILE]
    assert after.calls == report.calls + 2
    assert after.spend_usd == report.spend_usd + Decimal("0.002")


def test_the_request_is_answered_and_the_review_follows_the_new_report(report):
    review = request_photo(request_photo(new_review(report), report, "o1"), report, "c2")
    after, answered, _, _ = answer(report, review, "r1")
    assert answered.requests[0].status is RequestStatus.ANSWERED and answered.requests[0].photo_index == 2
    assert answered.requests[1].status is RequestStatus.OPEN and answered.status is ReviewStatus.AWAITING_PATIENT
    assert answered.intake_id == after.intake_id != report.intake_id


def test_the_new_report_belongs_to_all_the_photos_and_to_nothing_else(report):
    review = request_photo(new_review(report), report, "o1")
    after, answered, _, _ = answer(report, review, "r1")
    render_brief(after, IMAGES + [(PHOTO2, "image/png")], AUDIO, CAT, review=answered)
    with pytest.raises(ValueError):
        render_brief(after, IMAGES, AUDIO, CAT)
    with pytest.raises(ValueError):
        render_brief(after, [(PHOTO2, "image/png"), (PHOTO, "image/png")], AUDIO, CAT)
    assert ReconciliationReport.model_validate(after.model_dump()) == after


def test_an_unphotographed_medicine_is_paired_with_its_new_photo_and_nothing_is_replaced(report):
    review = request_photo(new_review(report), report, "c2")
    after, answered, _, _ = answer(report, review, "r1")
    assert after.superseded == []
    [beloc] = finding_for(after, claim_id="c2")
    assert beloc.observation_id == "o2" and beloc.type is D.MATCH
    assert [f.type for f in finding_for(after, observation_id="o1")] == [D.UNREADABLE_SOURCE]
    assert answered.status is ReviewStatus.DRAFT


def test_a_photo_that_cannot_be_opened_answers_the_request_but_replaces_nothing(report):
    review = request_photo(new_review(report), report, "o1")
    bad = (b"not an image", "image/png")
    after, answered, segmenter, reader = answer(report, review, "r1", photo=bad, reads={})
    assert segmenter.seen == [] and reader.seen == [] and after.calls == report.calls
    step = after.steps[len(report.steps)]
    assert step.action is AgentAction.SEGMENT and step.target == hashlib.sha256(bad[0]).hexdigest()[:12]
    assert step.outcome == "error: image cannot be decoded"
    assert after.superseded == [] and [f.type for f in finding_for(after, observation_id="o1")] == \
        [D.UNREADABLE_SOURCE]
    assert answered.requests[0].status is RequestStatus.ANSWERED and answered.requests[0].photo_index == 2
    assert "Photo 2: could not be opened; no model saw it." in coverage_lines(after, IMAGES + [bad], AUDIO)


def test_a_photo_with_no_pack_replaces_nothing(report):
    review = request_photo(new_review(report), report, "o1")
    after, _, _, _ = answer(report, review, "r1", regions=())
    assert after.superseded == [] and len(after.observations) == 2


def test_the_new_photo_has_its_own_call_budget(report):
    review = request_photo(new_review(report), report, "o1")
    after, _, _, reader = answer(report, review, "r1", max_provider_calls=1)
    assert reader.seen == [] and after.calls == report.calls + 1
    assert after.steps[-1].action is AgentAction.BUDGET_EXHAUSTED
    assert after.superseded == [] and [f.type for f in finding_for(after, observation_id="o1")] == \
        [D.UNREADABLE_SOURCE]


def test_an_unreadable_re_photo_is_reported_and_can_be_requested_again(report):
    review = request_photo(new_review(report), report, "o1")
    reads = {R2.region_id: [reading(readability="unreadable"), reading(readability="unreadable")]}
    after, answered, _, _ = answer(report, review, "r1", reads=reads)
    assert after.superseded == ["o1"]
    assert [f.type for f in finding_for(after, observation_id="o2")] == [D.UNREADABLE_SOURCE]
    again = request_photo(answered, after, "o2")
    assert again.requests[-1].request_id == "r2" and again.status is ReviewStatus.AWAITING_PATIENT


@pytest.mark.parametrize("case", ["not open", "unknown", "withdrawn", "other media", "same photo"])
def test_a_refused_answer_changes_nothing(report, case):
    review = request_photo(new_review(report), report, "o1")
    images, photo, request_id = IMAGES, (PHOTO2, "image/png"), "r1"
    if case == "not open":
        report, review, _, _ = answer(report, review, "r1")
    elif case == "unknown":
        request_id = "r7"
    elif case == "withdrawn":
        review = withdraw(review, "r1")
    elif case == "other media":
        images = [(PHOTO2, "image/png")]
    elif case == "same photo":
        photo = (PHOTO, "image/png")
    segmenter = Segmenter({SHA2: [R2], RC.image_sha256: [RC, RU]})
    before = (report.model_dump(), review.model_dump())
    with pytest.raises(ValueError):
        add_photo(report, review, request_id, photo, images, AUDIO, segmenter=segmenter,
                  reader=Reader({R2.region_id: [BELOC_50]}), catalogue=CAT)
    assert segmenter.seen == [] and (report.model_dump(), review.model_dump()) == before


# --- superseded observations in the report -----------------------------------------------------------------

def test_a_superseded_id_must_exist_and_no_finding_may_cite_it(report):
    data = report.model_dump()
    with pytest.raises(ValidationError):
        ReconciliationReport.model_validate({**data, "superseded": ["o9"]})
    with pytest.raises(ValidationError):
        ReconciliationReport.model_validate({**data, "superseded": ["o1"]})  # the unreadable_source finding cites o1
    assert ReconciliationReport.model_validate({k: v for k, v in data.items() if k != "superseded"}).superseded == []


# --- sign-off ----------------------------------------------------------------------------------------------

def test_approval_waits_for_every_open_request_and_is_final(report):
    waiting = request_photo(new_review(report), report, "o1")
    with pytest.raises(ValueError):
        approve(waiting, report)
    after, answered, _, _ = answer(report, waiting, "r1")
    with pytest.raises(ValueError):
        approve(answered, report)  # the review now belongs to the new report
    signed = approve(answered, after)
    assert signed.status is ReviewStatus.APPROVED and signed.intake_id == after.intake_id
    assert answered.status is ReviewStatus.DRAFT
    with pytest.raises(ValueError):
        request_photo(signed, after, "c2")
    withdrawable = approve(withdraw(request_photo(new_review(report), report, "c2"), "r1"), report)
    assert withdrawable.status is ReviewStatus.APPROVED
    with pytest.raises(ValueError):
        withdraw(withdrawable, "r1")


# --- on the brief ------------------------------------------------------------------------------------------

def page_of(report, images, review=None):
    kw = {} if review is None else {"review": review}
    return Page(render_brief(report, images, AUDIO, CAT, **kw)).root


def status_text(page):
    header = page.by_id("scope")
    [line] = header.find_all("p", id="review-status")
    return line.text()


def article_of(page, finding):
    return page.by_id(f"finding:{finding.finding_id}")


def test_the_header_says_the_brief_is_a_draft_until_approved(report):
    assert status_text(page_of(report, IMAGES)) == DRAFT
    assert status_text(page_of(report, IMAGES, new_review(report))) == DRAFT
    signed = approve(new_review(report), report)
    assert status_text(page_of(report, IMAGES, signed)) == APPROVED


def test_open_requests_show_on_their_findings_and_in_the_header(report):
    review = request_photo(request_photo(new_review(report), report, "o1"), report, "c2")
    page = page_of(report, IMAGES, review)
    assert status_text(page) == "Waiting for the patient: new photos requested 2."
    [unreadable] = finding_for(report, observation_id="o1")
    [unphotographed] = finding_for(report, claim_id="c2")
    for finding, request_id in ((unreadable, "r1"), (unphotographed, "r2")):
        [line] = article_of(page, finding).find_all("p", data_request=request_id)
        assert line.text() == REQUESTED
    assert len(page.find_all("p", data_request="r1")) == 1 and len(page.find_all("p", data_request="r2")) == 1
    assert page.by_id("coverage").find_all("li")[-1].text() == "Photos requested 2, received 0."


def test_after_the_answer_the_old_pack_says_it_was_replaced(report):
    review = request_photo(request_photo(new_review(report), report, "o1"), report, "c2")
    after, answered, _, _ = answer(report, review, "r1")
    images = IMAGES + [(PHOTO2, "image/png")]
    page = page_of(after, images, answered)
    assert status_text(page) == "Waiting for the patient: new photos requested 1."
    assert REPLACED in page.by_id(f"region:{RU.region_id}").text()
    assert REPLACED not in page.by_id(f"region:{RC.region_id}").text()
    assert REPLACED not in page.by_id(f"region:{R2.region_id}").text()
    assert not page.find_all("p", data_request="r1") and not page.find_all("p", data_request="r2")
    assert page.by_id("coverage").find_all("li")[-1].text() == "Photos requested 2, received 1."
    done = approve(withdraw(answered, "r2"), after)
    page = page_of(after, images, done)
    assert status_text(page) == APPROVED
    assert page.by_id("coverage").find_all("li")[-1].text() == "Photos requested 1, received 1."


def test_a_withdrawn_request_shows_nowhere_but_the_count(report):
    review = withdraw(request_photo(new_review(report), report, "o1"), "r1")
    page = page_of(report, IMAGES, review)
    assert not page.find_all("p", data_request="r1") and status_text(page) == DRAFT
    assert not any(li.text().startswith("Photos requested") for li in page.by_id("coverage").find_all("li"))


def test_no_request_means_no_request_line_in_coverage(report):
    lines = [li.text() for li in page_of(report, IMAGES, new_review(report)).by_id("coverage").find_all("li")]
    assert not any(line.startswith("Photos requested") for line in lines)


def test_a_brief_refuses_a_review_of_another_report(report):
    other = new_review(report).model_copy(update={"intake_id": "0" * 64})
    with pytest.raises(ValueError):
        render_brief(report, IMAGES, AUDIO, CAT, review=other)


def test_the_new_text_on_the_brief_gives_no_advice(report):
    for text in (DRAFT, APPROVED, REQUESTED, REPLACED, "Waiting for the patient: new photos requested 2.",
                 "Photos requested 2, received 1.", UNREADABLE_MESSAGE):
        assert_no_advice(text)
