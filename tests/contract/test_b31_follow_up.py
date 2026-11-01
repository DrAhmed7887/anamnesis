"""Batch 31 contract: the follow-up runs by itself. Written by the CEO; Muse must not edit it.

SPEC §8, "The follow-up by itself". For the Best Agentic Use-Case prize: after the intake, Anamnesis asks the patient
for every photo the brief is missing, takes the replies, and leaves the brief a draft for the clinician to approve.
Code fixes the targets, their order and when to stop; models only read the new photos; every message is a template.
Each round asks only the targets pending when it starts, so a pack that stays unreadable gets one ask per round.
"""

import hashlib
import io
from decimal import Decimal
from html.parser import HTMLParser

import pytest
from PIL import Image
from pydantic import ValidationError

from anamnesis.agent import run_intake
from anamnesis.agent.loop import SAM_CONCEPTS
from anamnesis.brief import render_brief
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.guardrails import assert_no_advice
from anamnesis.providers import ProviderTrace
from anamnesis.providers.spark import LabelReading
from anamnesis.review import approve, follow_up, new_review, request_message, request_photo, requestable
from anamnesis.schema import AudioTurn, DoseRegimen, ImageRegion, IngredientAmount, PatientClaim, Strength
from anamnesis.schema.review import (
    FollowUpOutcome,
    FollowUpStep,
    RequestKind,
    RequestStatus,
    Review,
    ReviewStatus,
)
from anamnesis.schema.templates import FOLLOW_UP_DONE

CAT = load_catalogue()
DRAFT = "Draft: not yet reviewed by a clinician."
UNREADABLE_MESSAGE = ("Please send one new photo of this medicine pack, with the label facing the camera, "
                      "in good light.")
BELOC_MESSAGE = "Please send one photo of the pack of the medicine you mentioned as “Beloc-Zok”."
OPEN, ANSWERED = RequestStatus.OPEN, RequestStatus.ANSWERED
UNREADABLE, NOT_PHOTOGRAPHED = RequestKind.UNREADABLE, RequestKind.NOT_PHOTOGRAPHED
GOT, NONE, AGAIN = FollowUpOutcome.ANSWERED, FollowUpOutcome.NO_REPLY, FollowUpOutcome.DUPLICATE


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

    def with_id(self, ident):
        return [node for node in self.walk() if node.attrs.get("id") == ident]

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

    def one(self, ident):
        found = self.root.with_id(ident)
        assert len(found) == 1, f"{len(found)} elements with id {ident!r}"
        return found[0]


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
    def __init__(self, claims):
        self.claims = list(claims)

    def extract(self, turns):
        return list(self.claims), trace("claims")


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


class Patient:
    """The patient's side of `reply`: answers each request from a script, in call order (None once it runs out),
    and records what it was asked."""

    def __init__(self, *answers):
        self.answers, self.asked = list(answers), []

    def __call__(self, request, message):
        self.asked.append((request, message))
        return self.answers.pop(0) if self.answers else None


def mg(inn, amount):
    return IngredientAmount(inn=inn, amount=Decimal(str(amount)), unit="mg")


def reading(label=None, strength=None, readability="readable"):
    return LabelReading(region_id="r", label_text=label, strength=strength, readability=readability)


# --- the patient: Concor photographed, one pack nobody can read, Beloc-Zok mentioned but not photographed ------

PHOTO = png(600, 300, (200, 200, 200))
PHOTO2 = png(400, 300, (180, 190, 200))   # a re-photo that turns out to be the Beloc-Zok
PHOTO3 = png(420, 300, (90, 90, 90))      # a re-photo still too dark to read
PHOTO4 = png(440, 300, (60, 60, 60))      # and another
SHA2, SHA3, SHA4 = (hashlib.sha256(p).hexdigest() for p in (PHOTO2, PHOTO3, PHOTO4))
RC = region_on(PHOTO, (10, 20, 139, 279), 0)
RU = region_on(PHOTO, (160, 20, 289, 279), 1)
R2 = region_on(PHOTO2, (20, 20, 379, 279), 0)
R3 = region_on(PHOTO3, (20, 20, 399, 279), 0)
R4 = region_on(PHOTO4, (20, 20, 419, 279), 0)
AUDIO = (b"RIFF fixture voice note", "audio/wav")
IMAGES = [(PHOTO, "image/png")]
GIVE2, GIVE3, GIVE4 = (PHOTO2, "image/png"), (PHOTO3, "image/png"), (PHOTO4, "image/png")
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
CONCOR_5 = reading("Concor 5 mg\nBisoprolol fumarate",
                   Strength(ingredients=[mg("bisoprolol fumarate", 5)], per="tablet", release="immediate"))
BELOC_50 = reading("Beloc-Zok 50 mg\nMetoprolol succinate\nProlonged-release tablets",
                   Strength(ingredients=[mg("metoprolol succinate", 50)], per="tablet", release="modified"))
DARK = reading(readability="unreadable")


def intake(claims=CLAIMS, regions=(RC, RU)):
    reads = {RC.region_id: [CONCOR_5], RU.region_id: [DARK, DARK]}
    return run_intake(AUDIO[0], IMAGES, transcriber=Transcriber(), extractor=Extractor(claims),
                      segmenter=Segmenter({RC.image_sha256: list(regions)}), reader=Reader(reads), catalogue=CAT)


def adapters():
    """One segmenter and one reader for every answering photo of a run, as the live script passes them."""
    segmenter = Segmenter({SHA2: [R2], SHA3: [R3], SHA4: [R4]})
    reader = Reader({R2.region_id: [BELOC_50], R3.region_id: [DARK, DARK], R4.region_id: [DARK, DARK]})
    return segmenter, reader


def run(report, review, patient, images=IMAGES, audio=AUDIO, **kw):
    segmenter, reader = adapters()
    new, out, given, log = follow_up(report, review, list(images), audio, reply=patient, segmenter=segmenter,
                                     reader=reader, catalogue=CAT, **kw)
    return new, out, given, log, segmenter, reader


@pytest.fixture
def report():
    return intake()


def test_the_fixture_is_what_the_tests_assume(report):
    assert requestable(report) == [(UNREADABLE, "o1"), (NOT_PHOTOGRAPHED, "c2")]


# --- the run -----------------------------------------------------------------------------------------------

def test_with_nothing_to_ask_it_returns_its_inputs_and_asks_nobody():
    clean = intake(claims=CLAIMS[:1], regions=(RC,))
    assert requestable(clean) == []
    review, patient = new_review(clean), Patient(GIVE2)
    new, out, given, log, segmenter, reader = run(clean, review, patient)
    assert (new, out, given, log) == (clean, review, IMAGES, [])
    assert patient.asked == [] and segmenter.seen == [] and reader.seen == []


def test_the_unreadable_pack_is_asked_for_and_answered_without_a_clinician(report):
    patient = Patient(GIVE2)
    new, review, given, log, segmenter, reader = run(report, new_review(report), patient)
    assert log == [FollowUpStep(round=1, request_id="r1", target_id="o1", kind=UNREADABLE, outcome=GOT)]
    assert len(patient.asked) == 1
    assert [(r.request_id, r.status, r.photo_index) for r in review.requests] == [("r1", ANSWERED, 2)]
    assert review.status is ReviewStatus.DRAFT and review.intake_id == new.intake_id
    assert given == [*IMAGES, GIVE2]
    assert new.superseded == ["o1"]
    assert requestable(new) == []          # the re-photo was the Beloc-Zok, so nothing is left to ask
    assert set(segmenter.seen) == {SHA2}


def test_every_target_is_asked_once_in_finding_order_with_its_template_message(report):
    patient = Patient(None, None)
    new, review, given, log, segmenter, reader = run(report, new_review(report), patient)
    assert [(req.request_id, req.kind, req.target_id, req.status) for req, _ in patient.asked] == [
        ("r1", UNREADABLE, "o1", OPEN), ("r2", NOT_PHOTOGRAPHED, "c2", OPEN)]
    assert [message for _, message in patient.asked] == [UNREADABLE_MESSAGE, BELOC_MESSAGE]
    for request, message in patient.asked:
        assert message == request_message(report, request)
        assert_no_advice(message)
    assert [(s.round, s.request_id, s.target_id, s.outcome) for s in log] == [(1, "r1", "o1", NONE),
                                                                               (1, "r2", "c2", NONE)]
    assert review.status is ReviewStatus.AWAITING_PATIENT
    assert [r.status for r in review.requests] == [OPEN, OPEN]
    assert (new, given) == (report, IMAGES)
    assert segmenter.seen == [] and reader.seen == []


@pytest.mark.parametrize(("max_rounds", "asked"), [(1, ["o1", "c2"]), (2, ["o1", "c2", "o2"])])
def test_a_pack_that_stays_unreadable_gets_one_ask_per_round_and_no_more(report, max_rounds, asked):
    patient = Patient(GIVE3, None, GIVE4)
    new, review, given, log, *_ = run(report, new_review(report), patient, max_rounds=max_rounds)
    assert [s.target_id for s in log] == asked
    assert [s.round for s in log] == [1, 1, 2][:len(asked)]
    assert [s.outcome for s in log] == [GOT, NONE, GOT][:len(asked)]
    newest = new.observations[-1].observation_id
    assert newest not in [r.target_id for r in review.requests]   # it appeared in the last round: it waits
    assert (UNREADABLE, newest) in requestable(new)
    assert given == [*IMAGES, GIVE3, GIVE4][:len(IMAGES) + asked.count("o1") + asked.count("o2")]


def test_a_photo_already_given_is_logged_as_a_duplicate_and_goes_to_no_model(report):
    patient = Patient(IMAGES[0], None)
    new, review, given, log, segmenter, reader = run(report, new_review(report), patient)
    assert [(s.target_id, s.outcome) for s in log] == [("o1", AGAIN), ("c2", NONE)]
    assert len(patient.asked) == 2
    assert segmenter.seen == [] and reader.seen == []
    assert [r.status for r in review.requests] == [OPEN, OPEN]
    assert (new, given) == (report, IMAGES)


def test_a_target_with_an_open_request_is_never_asked_again(report):
    review = request_photo(new_review(report), report, "o1")     # the clinician asked first
    patient = Patient(None)
    new, out, given, log, *_ = run(report, review, patient)
    assert [(req.request_id, req.target_id) for req, _ in patient.asked] == [("r2", "c2")]
    assert [s.request_id for s in log] == ["r2"]
    assert [(r.request_id, r.status) for r in out.requests] == [("r1", OPEN), ("r2", OPEN)]


def test_it_never_approves_and_the_clinician_still_has_to(report):
    new, review, *_ = run(report, new_review(report), Patient(GIVE2))
    assert review.status is ReviewStatus.DRAFT
    assert approve(review, new).status is ReviewStatus.APPROVED
    same, waiting, *_ = run(report, new_review(report), Patient(None, None))
    assert waiting.status is ReviewStatus.AWAITING_PATIENT
    with pytest.raises(ValueError):
        approve(waiting, same)


@pytest.mark.parametrize("case", ["another report", "approved", "no rounds", "other media"])
def test_a_refused_follow_up_changes_nothing_and_asks_nobody(report, case):
    review, images, kw = new_review(report), IMAGES, {}
    if case == "another report":
        review = Review(intake_id="0" * 64, status=ReviewStatus.DRAFT)
    elif case == "approved":
        review = approve(new_review(report), report)
    elif case == "no rounds":
        kw = {"max_rounds": 0}
    else:
        images = [GIVE2]
    before = (report.model_dump(), review.model_dump())
    patient = Patient(GIVE2)
    with pytest.raises(ValueError):
        run(report, review, patient, images=images, **kw)
    assert patient.asked == []
    assert (report.model_dump(), review.model_dump()) == before


def test_the_inputs_are_left_as_they_were(report):
    review, images = new_review(report), list(IMAGES)
    before = (report.model_dump(), review.model_dump(), list(images))
    segmenter, reader = adapters()
    follow_up(report, review, images, AUDIO, reply=Patient(GIVE3, None, GIVE4), segmenter=segmenter, reader=reader,
              catalogue=CAT)
    assert (report.model_dump(), review.model_dump(), images) == before


def test_turns_claims_and_earlier_evidence_are_kept(report):
    new, *_ = run(report, new_review(report), Patient(GIVE3, None, GIVE4))
    assert new.turns == report.turns and new.claims == report.claims
    assert new.observations[:len(report.observations)] == report.observations
    assert new.steps[:len(report.steps)] == report.steps


def test_only_the_answering_photos_go_to_a_model_each_within_its_budget(report):
    new, review, given, log, segmenter, reader = run(report, new_review(report), Patient(GIVE3, None, GIVE4))
    assert set(segmenter.seen) == {SHA3, SHA4}
    assert set(reader.seen) == {R3.region_id, R4.region_id}
    answered = [s for s in log if s.outcome is GOT]
    assert len(answered) == 2
    assert 0 < new.calls - report.calls <= len(answered) * (len(SAM_CONCEPTS) + 2 * 3)


def test_the_log_is_strict():
    ok = {"round": 1, "request_id": "r1", "target_id": "o1", "kind": "unreadable", "outcome": "answered"}
    assert FollowUpStep(**ok).outcome is GOT
    for bad in ({**ok, "round": 0}, {**ok, "outcome": "approved"}, {**ok, "kind": "other"}, {**ok, "extra": 1}):
        with pytest.raises(ValidationError):
            FollowUpStep(**bad)
    assert {o.value for o in FollowUpOutcome} == {"answered", "no_reply", "duplicate"}


# --- the brief ---------------------------------------------------------------------------------------------

def test_the_line_is_fixed_text_that_gives_no_advice():
    assert FOLLOW_UP_DONE == "Anamnesis sent the follow-up itself: new photos asked for {asked}, received {received}."
    assert_no_advice(FOLLOW_UP_DONE.format(asked=2, received=1))


@pytest.mark.parametrize(("answers", "line", "status"), [
    ((GIVE2,), "Anamnesis sent the follow-up itself: new photos asked for 1, received 1.", DRAFT),
    ((None, None), "Anamnesis sent the follow-up itself: new photos asked for 2, received 0.",
     "Waiting for the patient: new photos requested 2."),
])
def test_the_brief_says_anamnesis_sent_the_follow_up(report, answers, line, status):
    new, review, given, log, *_ = run(report, new_review(report), Patient(*answers))
    page = Page(render_brief(new, given, AUDIO, CAT, review=review, follow_up=log))
    assert page.one("follow-up").text() == line
    assert page.one("review-status").text() == status


def test_without_a_log_there_is_no_follow_up_line(report):
    for log in (None, []):
        page = Page(render_brief(report, IMAGES, AUDIO, CAT, review=new_review(report), follow_up=log))
        assert page.root.with_id("follow-up") == []


def test_a_log_is_shown_only_with_the_review_it_belongs_to(report):
    new, review, given, log, *_ = run(report, new_review(report), Patient(GIVE2))
    with pytest.raises(ValueError):
        render_brief(new, given, AUDIO, CAT, follow_up=log)
    with pytest.raises(ValueError):
        render_brief(new, given, AUDIO, CAT, review=review, follow_up=[log[0].model_copy(update={"request_id": "r9"})])
