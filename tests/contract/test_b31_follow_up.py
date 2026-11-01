"""Batch 31 contract: the follow-up runs by itself. Written by the CEO; Muse must not edit it.

SPEC §8, "The follow-up by itself". For the Best Agentic Use-Case prize: after the intake, Anamnesis asks the patient
for a photo of every medicine they mentioned but didn't photograph, takes the replies, and leaves the brief a draft for
the clinician to approve. Code fixes the targets, their order and when to stop; models only read the new photos; every
message is a template that names the medicine. A pack that couldn't be read stays with the clinician (supervisor 31
#2: one template can't say which pack is meant). Round 2 pins the supervisor's #1, #3, #4 and #7; round 3 its round-2
#1 (the findings are those of an intake given every photo at once), #2, #3 (a late answer) and #4.
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
from anamnesis.review import (
    PhotoAlreadyGiven,
    add_photo,
    approve,
    follow_up,
    new_review,
    request_message,
    request_photo,
    requestable,
    withdraw,
)
from anamnesis.schema import AudioTurn, DoseRegimen, ImageRegion, IngredientAmount, PatientClaim, Strength
from anamnesis.schema import DiscrepancyType as D
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
LINE = ("Anamnesis sent the follow-up itself, for medicines mentioned but not photographed: photos asked for {asked}, "
        "received {received}.")
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
    def __init__(self, turns=None):
        self.turns = turns

    def transcribe(self, audio, *, language_bias=None, keywords=None, lang_hint=None):
        return list(self.turns if self.turns is not None else TURNS), trace("voice")


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
PHOTO5 = png(460, 300, (40, 40, 40))      # and a third
PHOTO6 = png(480, 300, (150, 170, 190))   # one photo of both the Beloc-Zok and a Norvasc
SHA2, SHA3, SHA4, SHA5, SHA6 = (hashlib.sha256(p).hexdigest() for p in (PHOTO2, PHOTO3, PHOTO4, PHOTO5, PHOTO6))
RC = region_on(PHOTO, (10, 20, 139, 279), 0)
RU = region_on(PHOTO, (160, 20, 289, 279), 1)
R2 = region_on(PHOTO2, (20, 20, 379, 279), 0)
R3 = region_on(PHOTO3, (20, 20, 399, 279), 0)
R4 = region_on(PHOTO4, (20, 20, 419, 279), 0)
R5 = region_on(PHOTO5, (20, 20, 439, 279), 0)
R6A = region_on(PHOTO6, (10, 20, 229, 279), 0)
R6B = region_on(PHOTO6, (250, 20, 469, 279), 1)
AUDIO = (b"RIFF fixture voice note", "audio/wav")
IMAGES = [(PHOTO, "image/png")]
GIVE2, GIVE3, GIVE4, GIVE5, GIVE6 = ((p, "image/png") for p in (PHOTO2, PHOTO3, PHOTO4, PHOTO5, PHOTO6))
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
NORVASC_5 = reading("Norvasc 5 mg\nAmlodipine besilate",
                    Strength(ingredients=[mg("amlodipine besilate", 5)], per="tablet", release="immediate"))
NV_TURN = AudioTurn(turn_id="turn-3", start_ms=13000, end_ms=16000, transcript="And Norvasc 5 mg once a day.")
NORVASC = PatientClaim(claim_id="c4", name_text="Norvasc", intake_amount=mg("Norvasc", 5),
                       regimen=DoseRegimen(intakes_per_day=Decimal(1)), status="active", audio_evidence=["turn-3"])


def intake(claims=CLAIMS, regions=(RC, RU), turns=None):
    reads = {RC.region_id: [CONCOR_5], RU.region_id: [DARK, DARK]}
    return run_intake(AUDIO[0], IMAGES, transcriber=Transcriber(turns), extractor=Extractor(claims),
                      segmenter=Segmenter({RC.image_sha256: list(regions)}), reader=Reader(reads), catalogue=CAT)


def adapters():
    """One segmenter and one reader for every answering photo of a run, as the live script passes them."""
    segmenter = Segmenter({SHA2: [R2], SHA3: [R3], SHA4: [R4], SHA5: [R5], SHA6: [R6A, R6B]})
    reader = Reader({R2.region_id: [BELOC_50], R3.region_id: [DARK, DARK], R4.region_id: [DARK, DARK],
                     R5.region_id: [DARK, DARK], R6A.region_id: [BELOC_50], R6B.region_id: [NORVASC_5]})
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


def quiet():
    """Nothing for the follow-up to ask: Concor matched, and at most a dark pack that stays with the clinician."""
    return intake(claims=CLAIMS[:1], regions=(RC,))


# --- the run -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("regions", [(RC,), (RC, RU)])
def test_with_no_medicine_left_to_photograph_it_returns_its_inputs_and_asks_nobody(regions):
    calm = intake(claims=CLAIMS[:1], regions=regions)
    assert all(kind is UNREADABLE for kind, _ in requestable(calm))
    review, patient = new_review(calm), Patient(GIVE2)
    new, out, given, log, segmenter, reader = run(calm, review, patient)
    assert (new, out, given, log) == (calm, review, IMAGES, [])
    assert patient.asked == [] and segmenter.seen == [] and reader.seen == []


def test_a_medicine_mentioned_but_not_photographed_is_asked_for_by_name_and_answered(report):
    patient = Patient(GIVE2)
    new, review, given, log, segmenter, reader = run(report, new_review(report), patient)
    assert [(req.request_id, req.kind, req.target_id) for req, _ in patient.asked] == [("r1", NOT_PHOTOGRAPHED, "c2")]
    assert patient.asked[0][1] == BELOC_MESSAGE
    assert log == [FollowUpStep(round=1, request_id="r1", target_id="c2", kind=NOT_PHOTOGRAPHED, outcome=GOT)]
    assert [(r.request_id, r.status, r.photo_index) for r in review.requests] == [("r1", ANSWERED, 2)]
    assert review.status is ReviewStatus.DRAFT and review.intake_id == new.intake_id
    assert given == [*IMAGES, GIVE2]
    assert new.superseded == []                        # an answer about a medicine replaces no pack
    assert [f.type for f in new.findings if f.claim_id == "c2"] == [D.MATCH]
    assert requestable(new) == [(UNREADABLE, "o1")]    # the dark pack stays with the clinician
    assert set(segmenter.seen) == {SHA2}


def test_an_unreadable_pack_is_never_the_follow_ups_to_ask_for(report):
    patient = Patient(GIVE3, GIVE4, GIVE5)
    new, review, *_ = run(report, new_review(report), patient, max_rounds=3)
    assert patient.asked and all(req.kind is NOT_PHOTOGRAPHED for req, _ in patient.asked)
    assert all(r.kind is NOT_PHOTOGRAPHED for r in review.requests)
    assert "o1" not in new.superseded


def test_the_message_names_the_medicine_and_is_its_template(report):
    patient = Patient(None)
    new, review, given, log, segmenter, reader = run(report, new_review(report), patient)
    [(request, message)] = patient.asked
    assert (request.request_id, request.kind, request.target_id, request.status) == ("r1", NOT_PHOTOGRAPHED, "c2",
                                                                                      OPEN)
    assert message == BELOC_MESSAGE == request_message(report, request)
    assert_no_advice(message)
    assert [(s.round, s.request_id, s.target_id, s.outcome) for s in log] == [(1, "r1", "c2", NONE)]
    assert review.status is ReviewStatus.AWAITING_PATIENT
    assert [r.status for r in review.requests] == [OPEN]
    assert (new, given) == (report, IMAGES)
    assert segmenter.seen == [] and reader.seen == []


@pytest.mark.parametrize("max_rounds", [1, 2, 3])
def test_a_photo_that_cannot_be_read_is_asked_for_again_once_per_round(report, max_rounds):
    patient = Patient(GIVE3, GIVE4, GIVE5)
    new, review, given, log, *_ = run(report, new_review(report), patient, max_rounds=max_rounds)
    assert [(s.round, s.target_id, s.outcome) for s in log] == [(r, "c2", GOT) for r in range(1, max_rounds + 1)]
    assert len(patient.asked) == max_rounds
    assert [f.type for f in new.findings if f.claim_id == "c2"] == [D.MISSING_MODALITY]
    assert given == [*IMAGES, GIVE3, GIVE4, GIVE5][:1 + max_rounds]


def test_a_photo_already_given_is_logged_as_a_duplicate_and_goes_to_no_model(report):
    patient = Patient(IMAGES[0])
    new, review, given, log, segmenter, reader = run(report, new_review(report), patient)
    assert [(s.target_id, s.outcome) for s in log] == [("c2", AGAIN)]
    assert len(patient.asked) == 1
    assert segmenter.seen == [] and reader.seen == []
    assert [r.status for r in review.requests] == [OPEN]
    assert (new, given) == (report, IMAGES)


def test_a_repeated_photo_is_refused_with_its_own_error(report):
    review = request_photo(new_review(report), report, "c2")
    with pytest.raises(PhotoAlreadyGiven, match="photo was already given"):
        add_photo(report, review, "r1", IMAGES[0], IMAGES, AUDIO, segmenter=Segmenter({}), reader=Reader({}),
                  catalogue=CAT)
    assert issubclass(PhotoAlreadyGiven, ValueError)


@pytest.mark.parametrize("withdrawn", [False, True])
def test_a_medicine_the_clinician_asked_for_or_withdrew_is_left_alone(report, withdrawn):
    review = request_photo(new_review(report), report, "c2")
    if withdrawn:
        review = withdraw(review, "r1")
    patient = Patient(GIVE2)
    new, out, given, log, *_ = run(report, review, patient)
    assert patient.asked == [] and log == []
    assert (new, out, given) == (report, review, IMAGES)


def test_it_never_approves_and_the_clinician_still_has_to(report):
    new, review, *_ = run(report, new_review(report), Patient(GIVE2))
    assert review.status is ReviewStatus.DRAFT
    assert approve(review, new).status is ReviewStatus.APPROVED
    same, waiting, *_ = run(report, new_review(report), Patient(None))
    assert waiting.status is ReviewStatus.AWAITING_PATIENT
    with pytest.raises(ValueError):
        approve(waiting, same)


@pytest.mark.parametrize("calm", [False, True])
@pytest.mark.parametrize("case", ["another report", "approved", "no rounds", "rounds not an int", "rounds a bool",
                                  "other media"])
def test_a_refused_follow_up_changes_nothing_and_asks_nobody(report, calm, case):
    base = quiet() if calm else report   # with nothing to ask, no other check can refuse first
    review, images, kw = new_review(base), IMAGES, {}
    if case == "another report":
        review = Review(intake_id="0" * 64, status=ReviewStatus.DRAFT)
    elif case == "approved":
        review = approve(new_review(base), base)
    elif case == "no rounds":
        kw = {"max_rounds": 0}
    elif case == "rounds not an int":
        kw = {"max_rounds": 1.5}
    elif case == "rounds a bool":
        kw = {"max_rounds": True}
    else:
        images = [GIVE2]
    before = (base.model_dump(), review.model_dump())
    patient = Patient(GIVE2)
    with pytest.raises(ValueError):
        run(base, review, patient, images=images, **kw)
    assert patient.asked == []
    assert (base.model_dump(), review.model_dump()) == before


def test_the_inputs_are_left_as_they_were(report):
    review, images = new_review(report), list(IMAGES)
    before = (report.model_dump(), review.model_dump(), list(images))
    segmenter, reader = adapters()
    follow_up(report, review, images, AUDIO, reply=Patient(GIVE3, GIVE4), segmenter=segmenter, reader=reader,
              catalogue=CAT)
    assert (report.model_dump(), review.model_dump(), images) == before


def test_turns_claims_and_earlier_evidence_are_kept(report):
    new, *_ = run(report, new_review(report), Patient(GIVE3, GIVE4))
    assert new.turns == report.turns and new.claims == report.claims
    assert new.observations[:len(report.observations)] == report.observations
    assert new.steps[:len(report.steps)] == report.steps


def test_only_the_answering_photos_go_to_a_model_each_within_its_budget(report):
    new, review, given, log, segmenter, reader = run(report, new_review(report), Patient(GIVE3, GIVE4))
    assert set(segmenter.seen) == {SHA3, SHA4}
    assert set(reader.seen) == {R3.region_id, R4.region_id}
    answered = [s for s in log if s.outcome is GOT]
    assert len(answered) == 2
    assert 0 < new.calls - report.calls <= len(answered) * (len(SAM_CONCEPTS) + 2 * 3)


def test_what_reply_does_to_its_request_reaches_nothing(report):
    def meddling(request, message):
        request.target_id, request.kind = "o0", UNREADABLE   # tries to aim the answer at the matched Concor pack
        return GIVE2
    new, review, given, log, *_ = run(report, new_review(report), meddling)
    assert [(r.request_id, r.kind, r.target_id, r.status) for r in review.requests] == [
        ("r1", NOT_PHOTOGRAPHED, "c2", ANSWERED)]
    assert (log[0].target_id, log[0].kind) == ("c2", NOT_PHOTOGRAPHED)
    assert new.superseded == []
    assert [f.type for f in new.findings if f.observation_id == "o0"] == [
        f.type for f in report.findings if f.observation_id == "o0"]


def test_the_log_is_strict():
    ok = {"round": 1, "request_id": "r1", "target_id": "c2", "kind": "not_photographed", "outcome": "answered"}
    assert FollowUpStep(**ok).outcome is GOT
    for bad in ({**ok, "round": 0}, {**ok, "outcome": "approved"}, {**ok, "kind": "other"}, {**ok, "extra": 1}):
        with pytest.raises(ValidationError):
            FollowUpStep(**bad)
    assert {o.value for o in FollowUpOutcome} == {"answered", "no_reply", "duplicate"}


# --- the brief ---------------------------------------------------------------------------------------------

def test_the_line_is_fixed_text_that_gives_no_advice():
    assert FOLLOW_UP_DONE == LINE
    assert_no_advice(FOLLOW_UP_DONE.format(asked=2, received=1))


@pytest.mark.parametrize(("answers", "line", "status"), [
    ((GIVE2,), LINE.format(asked=1, received=1), DRAFT),
    ((None,), LINE.format(asked=1, received=0), "Waiting for the patient: new photos requested 1."),
])
def test_the_brief_says_anamnesis_sent_the_follow_up(report, answers, line, status):
    new, review, given, log, *_ = run(report, new_review(report), Patient(*answers))
    page = Page(render_brief(new, given, AUDIO, CAT, review=review, follow_up=log))
    assert page.one("follow-up").text() == line
    assert page.one("review-status").text() == status


def test_the_line_counts_the_log_not_the_review(report):
    review = request_photo(new_review(report), report, "o1")   # the clinician asked for the dark pack first
    new, out, given, log, *_ = run(report, review, Patient(GIVE2))
    assert len(out.requests) == 2 and len(log) == 1
    page = Page(render_brief(new, given, AUDIO, CAT, review=out, follow_up=log))
    assert page.one("follow-up").text() == LINE.format(asked=1, received=1)


def test_without_a_log_there_is_no_follow_up_line(report):
    for log in (None, []):
        page = Page(render_brief(report, IMAGES, AUDIO, CAT, review=new_review(report), follow_up=log))
        assert page.root.with_id("follow-up") == []


@pytest.mark.parametrize("case", ["no review", "unknown request", "a step twice", "another target", "another kind",
                                  "answered but open"])
def test_a_log_is_shown_only_with_the_review_it_belongs_to(report, case):
    new, review, given, log, *_ = run(report, new_review(report), Patient(GIVE2))         # r1 answered
    still, waiting, kept, _, *_ = run(report, new_review(report), Patient(None))         # r1 open
    on, kw = (new, given), {"review": review, "follow_up": log}
    step = log[0]
    if case == "no review":
        kw = {"follow_up": log}
    elif case == "unknown request":
        kw["follow_up"] = [step.model_copy(update={"request_id": "r9"})]
    elif case == "a step twice":
        kw["follow_up"] = [step, step]
    elif case == "another target":
        kw["follow_up"] = [step.model_copy(update={"target_id": "o1"})]
    elif case == "another kind":
        kw["follow_up"] = [step.model_copy(update={"kind": UNREADABLE})]
    else:
        on, kw = (still, kept), {"review": waiting, "follow_up": log}
    with pytest.raises(ValueError):
        render_brief(on[0], on[1], AUDIO, CAT, **kw)


def test_a_late_answer_keeps_the_log_valid(report):
    new, review, given, log, *_ = run(report, new_review(report), Patient(None))   # r1 for c2: no reply yet
    later, answered = add_photo(new, review, "r1", GIVE2, given, AUDIO, segmenter=Segmenter({SHA2: [R2]}),
                                reader=Reader({R2.region_id: [BELOC_50]}), catalogue=CAT)
    page = Page(render_brief(later, [*given, GIVE2], AUDIO, CAT, review=answered, follow_up=log))
    assert page.one("follow-up").text() == LINE.format(asked=1, received=0)   # it can only understate


def test_a_request_the_follow_up_never_makes_is_not_credited_to_it(report):
    review = request_photo(new_review(report), report, "o1")                       # the clinician's own request
    later, answered = add_photo(report, review, "r1", GIVE3, IMAGES, AUDIO, segmenter=Segmenter({SHA3: [R3]}),
                                reader=Reader({R3.region_id: [DARK, DARK]}), catalogue=CAT)
    step = FollowUpStep(round=1, request_id="r1", target_id="o1", kind=UNREADABLE, outcome=GOT)
    with pytest.raises(ValueError):
        render_brief(later, [*IMAGES, GIVE3], AUDIO, CAT, review=answered, follow_up=[step])



def test_a_step_must_name_its_requests_own_kind(report):
    review = request_photo(new_review(report), report, "o1")                       # the clinician's own request
    later, answered = add_photo(report, review, "r1", GIVE3, IMAGES, AUDIO, segmenter=Segmenter({SHA3: [R3]}),
                                reader=Reader({R3.region_id: [DARK, DARK]}), catalogue=CAT)
    step = FollowUpStep(round=1, request_id="r1", target_id="o1", kind=NOT_PHOTOGRAPHED, outcome=GOT)
    with pytest.raises(ValueError):                # supervisor 31 round 3 #1: the kind must be its request's
        render_brief(later, [*IMAGES, GIVE3], AUDIO, CAT, review=answered, follow_up=[step])

# --- round 3: what one answer can resolve -----------------------------------------------------------------

def test_a_medicine_an_earlier_answer_this_round_resolved_is_not_asked_for():
    base = intake(claims=[*CLAIMS[:2], NORVASC], regions=(RC,), turns=[*TURNS, NV_TURN])
    assert requestable(base) == [(NOT_PHOTOGRAPHED, "c2"), (NOT_PHOTOGRAPHED, "c4")]
    patient = Patient(GIVE6)                       # the reply about Beloc-Zok shows the Norvasc too
    new, review, given, log, *_ = run(base, new_review(base), patient)
    assert [(s.request_id, s.target_id, s.outcome) for s in log] == [("r1", "c2", GOT)]
    assert len(patient.asked) == 1
    assert requestable(new) == []


def test_after_the_follow_up_the_findings_are_those_of_an_intake_with_every_photo(report):
    new, review, given, log, *_ = run(report, new_review(report), Patient(GIVE2))
    together = run_intake(AUDIO[0], given, transcriber=Transcriber(), extractor=Extractor(CLAIMS),
                          segmenter=Segmenter({RC.image_sha256: [RC, RU], SHA2: [R2]}),
                          reader=Reader({RC.region_id: [CONCOR_5], RU.region_id: [DARK, DARK],
                                         R2.region_id: [BELOC_50]}), catalogue=CAT)
    def found(r):
        return sorted((f.type.value, f.claim_id or "", f.observation_id or "") for f in r.findings)
    assert new.intake_id == together.intake_id
    assert found(new) == found(together)
