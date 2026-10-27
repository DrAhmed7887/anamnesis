"""Batch 19 contract, part 2: the clinician brief, cross-medication observations and coverage. Written by the CEO;
Muse must not edit it.

SPEC §7 (supervisor 27 Oct #1-#4 and #6; pre-B16 J2, J3, Z5, A3) and the §3 pairing preference. One self-contained
static HTML page per intake: disagreements first, both sources side by side, every fact linked to its audio turn and
image region, the crop the reader saw, a coverage block that is never silent, and fixed scope lines. Observations
across medicines come from what the patient reports, never from the photos.
"""

import base64
import hashlib
import io
from decimal import Decimal
from html.parser import HTMLParser

import pytest
from PIL import Image

from anamnesis.agent import crop_region, prepare_image, run_intake
from anamnesis.brief import coverage_lines, render_brief
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.guardrails import assert_no_advice
from anamnesis.core.overlap import DRUG_CLASSES, OverlapKind, cross_medication
from anamnesis.core.reconcile import reconcile_all
from anamnesis.providers import ProviderError, ProviderTrace
from anamnesis.providers.spark import LabelReading
from anamnesis.schema import (
    AudioTurn,
    DoseRegimen,
    ImageRegion,
    IngredientAmount,
    PackObservation,
    PatientClaim,
    Strength,
)
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.templates import PATIENT_QUESTIONS, TEMPLATES

CAT = load_catalogue()
SECTIONS = ["disagree", "across", "unconfirmed", "agree", "stopped", "coverage", "photos", "voice"]
SAME_INGREDIENT = ("More than one product the patient mentioned, and did not report as stopped, contains this "
                   "ingredient. Concurrent use is unconfirmed.")
SAME_CLASS = ("More than one medicine the patient mentioned, and did not report as stopped, belongs to this class. "
              "Concurrent use is unconfirmed.")
SCOPE = [
    "Anamnesis reports where the patient's account and the pack photos disagree. It gives no medical advice.",
    "Prescribed directions, timing, adherence and supply were not assessed.",
    "Over-the-counter, herbal and non-tablet products may be missing from this brief: ask about them.",
]


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
        """Descendants by tag and attributes (data_side="pack" matches data-side="pack")."""
        return [node for node in self.walk() if (tag is None or node.tag == tag)
                and all(node.attrs.get(key.replace("_", "-")) == value for key, value in attrs.items())]

    def by_id(self, ident):
        found = [node for node in self.walk() if node.attrs.get("id") == ident]
        assert len(found) == 1, f"{len(found)} elements with id {ident!r}"
        return found[0]

    def text(self):
        """Visible text, whitespace collapsed; script and style content is not text."""
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


def b64(data):
    return base64.b64encode(data).decode("ascii")


# --- fakes with the live adapters' interfaces --------------------------------------------------------------

def png(w, h, colour=(200, 200, 200)):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), colour).save(buf, "PNG")
    return buf.getvalue()


def region_on(image, box, obj, confidence=0.9):
    sha = hashlib.sha256(image).hexdigest()
    w, h = Image.open(io.BytesIO(image)).size
    return ImageRegion(region_id=f"{sha[:12]}-{obj}", image_sha256=sha, object_id=obj, x1=box[0], y1=box[1],
                       x2=box[2], y2=box[3], frame_w=w, frame_h=h, confidence=confidence)


def trace(cid):
    return ProviderTrace(call_id=cid, model_id="fixture:test", latency_ms=1, input_tokens=0, output_tokens=0,
                         cost_usd=Decimal("0.001"))


class Transcriber:
    def __init__(self, turns=(), fail=False):
        self.turns, self.fail = list(turns), fail

    def transcribe(self, audio, *, language_bias=None, keywords=None, lang_hint=None):
        if self.fail:
            raise ProviderError("voice", "unavailable")
        return list(self.turns), trace("voice")


class Extractor:
    def __init__(self, claims=(), fail=False):
        self.claims, self.fail = list(claims), fail

    def extract(self, turns):
        if self.fail:
            raise ProviderError("spark", "unavailable")
        return list(self.claims), trace("claims")


class Segmenter:
    """The regions of each photo, keyed by its sha256, for every concept; fail=True fails every call."""

    def __init__(self, by_sha=None, fail=False):
        self.by_sha, self.fail = dict(by_sha or {}), fail

    def segment(self, image, concept, *, mime):
        if self.fail:
            raise ProviderError("sam", "unavailable")
        return list(self.by_sha.get(hashlib.sha256(image).hexdigest(), [])), trace("sam")


class Reader:
    """Answers from a script of readings per region, in call order, and records the bytes each read was shown."""

    def __init__(self, script):
        self.script, self.seen = {key: list(value) for key, value in script.items()}, {}

    def read(self, image, region, *, mime, cropped=False):
        self.seen.setdefault(region.region_id, image)
        reading = self.script[region.region_id].pop(0)
        return reading.model_copy(update={"region_id": region.region_id}), trace("read")


def mg(inn, amount, unit="mg"):
    return IngredientAmount(inn=inn, amount=Decimal(str(amount)), unit=unit)


def st(*parts, release="unknown"):
    return Strength(ingredients=list(parts), per="tablet", release=release)


def claim(cid, name, turns=None, status="active", intake=None, per_day=None, strength=None):
    regimen = DoseRegimen(intakes_per_day=Decimal(per_day)) if per_day else None
    return PatientClaim(claim_id=cid, name_text=name, strength=strength, intake_amount=intake, regimen=regimen,
                        status=status, audio_evidence=turns or [f"turn-{cid}"])


def reading(label=None, strength=None, readability="readable"):
    return LabelReading(region_id="r", label_text=label, strength=strength, readability=readability)


def intake(audio, images, *, turns=(), claims=(), by_sha=None, reads=None, **kw):
    return run_intake(audio, images, transcriber=Transcriber(turns), extractor=Extractor(claims),
                      segmenter=Segmenter(by_sha), reader=Reader(reads or {}), catalogue=CAT, **kw)


# --- the showcase patient: two beta-blockers, a split tablet, a stopped and an unphotographed medicine -------

PHOTO = png(600, 300)
RC = region_on(PHOTO, (10, 20, 139, 279), 0, 0.95)    # Concor
RB = region_on(PHOTO, (160, 20, 289, 279), 1, 0.9)    # Beloc-Zok
RN = region_on(PHOTO, (310, 20, 439, 279), 2, 0.85)   # Norvasc: photographed, never mentioned
RU = region_on(PHOTO, (460, 20, 589, 279), 3, 0.8)    # a label nobody can read
AUDIO = (b"RIFF fixture voice note", "audio/wav")
TURNS = [
    AudioTurn(turn_id="turn-0", start_ms=0, end_ms=4000, transcript="I use Concor 5 mg once a day."),
    AudioTurn(turn_id="turn-1", start_ms=4000, end_ms=9000, transcript="And Beloc-Zok, 50 mg twice a day."),
    AudioTurn(turn_id="turn-2", start_ms=9000, end_ms=13000, transcript="I stopped Panadol last month."),
    AudioTurn(turn_id="turn-3", start_ms=13000, end_ms=16000, transcript="Sometimes Gelocatil for headaches."),
]
CLAIMS = [
    claim("c1", "Concor", ["turn-0"], intake=mg("Concor", 5), per_day=1),
    claim("c2", "Beloc-Zok", ["turn-1"], intake=mg("Beloc-Zok", 50), per_day=2),
    claim("c3", "Panadol", ["turn-2"], status="discontinued"),
    claim("c4", "Gelocatil", ["turn-3"]),
]


def reads():
    return {
        RC.region_id: [reading("Concor 5 mg\nBisoprolol fumarate", st(mg("bisoprolol fumarate", 5),
                                                                       release="immediate"))],
        RB.region_id: [reading("Beloc-Zok 100 mg\nMetoprolol succinate", st(mg("metoprolol succinate", 100),
                                                                             release="modified"))],
        RN.region_id: [reading("Norvasc 5 mg\nAmlodipine", st(mg("amlodipine", 5), release="immediate"))],
        RU.region_id: [reading(readability="unreadable"), reading(readability="unreadable")],
    }


def showcase():
    reader = Reader(reads())
    report = run_intake(AUDIO[0], [(PHOTO, "image/png")], transcriber=Transcriber(TURNS),
                        extractor=Extractor(CLAIMS), segmenter=Segmenter({RC.image_sha256: [RC, RB, RN, RU]}),
                        reader=reader, catalogue=CAT, top_k=4)
    html = render_brief(report, [(PHOTO, "image/png")], AUDIO, CAT)
    return report, html, Page(html).root, reader


def section_ids(page):
    return [node.attrs["id"] for node in page.find_all("section") if "id" in node.attrs]


def article_ids(section):
    return [node.attrs["id"] for node in section.find_all("article") if "id" in node.attrs]


def hrefs(node):
    return {link.attrs.get("href") for link in node.find_all("a")}


# --- order: disagreements first --------------------------------------------------------------------------

def test_sections_come_in_a_fixed_order_with_disagreements_first():
    report, _, page, _ = showcase()
    assert {f.finding_id: f.type for f in report.findings} == {
        "-:o2": D.MISSING_MODALITY, "-:o3": D.UNREADABLE_SOURCE, "c1:o0": D.MATCH,
        "c2:o1": D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH, "c3:-": D.MISSING_MODALITY, "c4:-": D.MISSING_MODALITY,
    }
    assert section_ids(page) == SECTIONS
    assert article_ids(page.by_id("disagree")) == ["finding:c2:o1"]
    assert article_ids(page.by_id("unconfirmed")) == ["finding:-:o2", "finding:-:o3", "finding:c4:-"]
    assert article_ids(page.by_id("agree")) == ["finding:c1:o0"]
    assert article_ids(page.by_id("stopped")) == ["finding:c3:-"]


def test_every_finding_shows_its_template_and_links_all_its_evidence():
    report, _, page, _ = showcase()
    for finding in report.findings:
        node = page.by_id(f"finding:{finding.finding_id}")
        assert node.tag == "article" and node.attrs["data-type"] == finding.type.value
        assert TEMPLATES[finding.type] in node.text()
        wanted = {f"#turn:{t}" for t in finding.audio_evidence} | {f"#region:{r}" for r in finding.visual_evidence}
        assert wanted <= hrefs(node)


def test_the_two_sources_stand_side_by_side():
    _, _, page, _ = showcase()
    node = page.by_id("finding:c2:o1")
    assert node.find_all("h3")[0].text() == "Beloc-Zok"
    [patient] = node.find_all(data_side="patient")
    [pack] = node.find_all(data_side="pack")
    assert "50 mg" in patient.text() and "active" in patient.text() and "100 mg" not in patient.text()
    assert "Beloc-Zok 100 mg" in pack.text() and "100 mg" in pack.text() and "50 mg" not in pack.text()
    assert PATIENT_QUESTIONS["intake"] in node.text()
    assert {"#turn:turn-1", f"#region:{RB.region_id}"} <= hrefs(node)


def test_one_sided_findings_say_which_source_is_missing():
    _, _, page, _ = showcase()
    pack_only = page.by_id("finding:-:o2")
    assert pack_only.find_all("h3")[0].text() == "Norvasc 5 mg"
    assert "Photographed, not mentioned" in pack_only.text()
    assert "Not mentioned." in pack_only.find_all(data_side="patient")[0].text()
    said_only = page.by_id("finding:c4:-")
    assert said_only.find_all("h3")[0].text() == "Gelocatil"
    assert "Mentioned, not photographed" in said_only.text()
    assert "Not photographed." in said_only.find_all(data_side="pack")[0].text()
    stopped = page.by_id("finding:c3:-")
    assert "Reported as stopped, not photographed" in stopped.text()
    assert "discontinued" in stopped.find_all(data_side="patient")[0].text()
    assert page.by_id("finding:-:o3").find_all("h3")[0].text() == "Unnamed pack"


def test_two_beta_blockers_are_shown_across_medicines():
    _, _, page, _ = showcase()
    [node] = page.by_id("across").find_all("article")
    assert node.attrs["data-kind"] == "same_class"
    text = node.text()
    assert SAME_CLASS in text and "beta-blockers" in text and "Concor" in text and "Beloc-Zok" in text
    assert {"#turn:turn-0", "#turn:turn-1"} <= hrefs(node)


# --- evidence on the page ------------------------------------------------------------------------------------

def test_the_photo_is_shown_prepared_with_its_sam_boxes():
    report, _, page, _ = showcase()
    figure = page.by_id("photo:1")
    data, mime = prepare_image(PHOTO, "image/png")
    assert [img.attrs["src"] for img in figure.find_all("img")] == [f"data:{mime};base64,{b64(data)}"]
    [svg] = figure.find_all("svg")
    assert svg.attrs["viewbox"].split() == ["0", "0", "600", "300"]
    boxes = {}
    for link in svg.find_all("a"):
        [rect] = link.find_all("rect")
        boxes[link.attrs["href"]] = tuple(float(rect.attrs[key]) for key in ("x", "y", "width", "height"))
    assert boxes == {f"#region:{r.region_id}": (r.x1, r.y1, r.x2 - r.x1 + 1, r.y2 - r.y1 + 1)
                     for r in report.regions}


def test_each_region_shows_the_crop_the_reader_saw():
    report, _, page, reader = showcase()
    prepared = prepare_image(PHOTO, "image/png")[0]
    for region in report.regions:
        crop = crop_region(prepared, region)
        assert reader.seen[region.region_id] == crop
        srcs = [img.attrs["src"] for img in page.by_id(f"region:{region.region_id}").find_all("img")]
        assert f"data:image/png;base64,{b64(crop)}" in srcs


def test_each_turn_can_be_played_on_its_own():
    _, _, page, _ = showcase()
    [audio] = page.find_all("audio")
    assert audio.attrs["src"] == f"data:audio/wav;base64,{b64(AUDIO[0])}"
    for turn in TURNS:
        node = page.by_id(f"turn:{turn.turn_id}")
        assert node.tag == "li" and turn.transcript in node.text()
        assert (node.attrs["data-start-ms"], node.attrs["data-end-ms"]) == (str(turn.start_ms), str(turn.end_ms))


def test_the_page_is_self_contained_and_every_link_resolves():
    _, html, page, _ = showcase()
    nodes = list(page.walk())
    assert not [node for node in nodes if node.tag == "link"]
    assert all(node.attrs["src"].startswith("data:") for node in nodes if "src" in node.attrs)
    ids = {node.attrs["id"] for node in nodes if "id" in node.attrs}
    links = [node.attrs["href"] for node in nodes if "href" in node.attrs]
    assert links and all(link.startswith("#") and link[1:] in ids for link in links)
    scripts = [node for node in nodes if node.tag == "script"]
    assert len(scripts) == 1 and "src" not in scripts[0].attrs
    assert not [name for node in nodes for name in node.attrs if name.startswith("on")]  # no event attributes
    assert "@import" not in html and "url(http" not in html.replace(" ", "")


def test_the_same_inputs_give_the_same_page():
    assert showcase()[1] == showcase()[1]


def test_scope_lines_are_always_in_the_header_and_the_brief_adds_no_advice():
    _, _, page, _ = showcase()
    header = page.by_id("scope")
    assert header.tag == "header" and all(line in header.text() for line in SCOPE)
    assert_no_advice(page.text())  # the fixture's own sources are advice-free, so any hit is the brief's text


def test_source_text_is_escaped_never_markup():
    hostile = "Concor </script><marquee onclick=go()>5</marquee> mg"
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=1000, transcript=hostile)]
    label = '<script>alert(1)</script> Concor 5 mg" onmouseover="go()'
    report = intake(b"wav", [(PHOTO, "image/png")], turns=turns, claims=[claim("c1", "Concor <blink>", ["turn-0"])],
                    by_sha={RC.image_sha256: [RC]}, reads={RC.region_id: [reading(label, st(mg("bisoprolol", 5)))]})
    page = Page(render_brief(report, [(PHOTO, "image/png")], (b"wav", "audio/wav"), CAT)).root
    tags = [node.tag for node in page.walk()]
    assert tags.count("script") == 1 and "marquee" not in tags and "blink" not in tags
    assert not [name for node in page.walk() for name in node.attrs if name.startswith("on")]
    assert hostile in page.text() and label in page.text() and "Concor <blink>" in page.text()


# --- coverage: never silent -----------------------------------------------------------------------------

def coverage_items(report, images, audio):
    page = Page(render_brief(report, images, audio, CAT)).root
    return [item.text() for item in page.by_id("coverage").find_all("li")], page


def test_coverage_names_every_photo_and_the_voice_note():
    two = png(300, 200, (90, 90, 90))
    first, second = region_on(two, (10, 10, 99, 99), 0, 0.9), region_on(two, (150, 10, 249, 99), 1, 0.8)
    images = [(two, "image/png"), (b"not an image", "image/png"), (png(300, 200, (30, 30, 30)), "image/png")]
    report = intake(None, images, by_sha={first.image_sha256: [first, second]}, top_k=1,
                    reads={first.region_id: [reading("Concor 5 mg", st(mg("bisoprolol", 5)))]})
    expected = [
        "Photos received: 3.",
        "Photo 1: packs found 2, labels read 1, not fully readable 0.",
        "Photo 2: could not be opened; no model saw it.",
        "Photo 3: no pack found.",
        "Voice note: none.",
    ]
    assert coverage_lines(report, images, None) == expected
    items, page = coverage_items(report, images, None)
    assert items == expected
    assert page.by_id("photo:1") and page.by_id("photo:3") and not page.find_all(id="photo:2")


def test_the_showcase_coverage_counts_the_unreadable_label():
    report = showcase()[0]
    assert coverage_lines(report, [(PHOTO, "image/png")], AUDIO) == [
        "Photos received: 1.",
        "Photo 1: packs found 4, labels read 4, not fully readable 1.",
        "Voice note: turns 4, medicines mentioned 4.",
    ]


def test_coverage_says_when_the_budget_cut_the_intake_short():
    images = [(PHOTO, "image/png")]
    report = intake(b"wav", images, turns=TURNS[:1], claims=CLAIMS[:1], by_sha={RC.image_sha256: [RC]},
                    max_provider_calls=2)
    expected = [
        "Photos received: 1.",
        "Photo 1: not examined; the call budget ran out first.",
        "Voice note: turns 1, medicines mentioned 1.",
        "The intake stopped early: the call budget ran out, so later steps were skipped.",
    ]
    assert coverage_lines(report, images, (b"wav", "audio/wav")) == expected
    assert coverage_items(report, images, (b"wav", "audio/wav"))[0] == expected


def test_coverage_reports_failed_detection_transcription_and_extraction():
    images = [(PHOTO, "image/png")]
    report = run_intake(b"wav", images, transcriber=Transcriber(fail=True), extractor=Extractor(),
                        segmenter=Segmenter(fail=True), reader=Reader({}), catalogue=CAT)
    assert coverage_lines(report, images, (b"wav", "audio/wav")) == [
        "Photos received: 1.", "Photo 1: pack detection failed.", "Voice note: not transcribed.",
    ]
    report = run_intake(b"wav", [], transcriber=Transcriber(TURNS[:1]), extractor=Extractor(fail=True),
                        segmenter=Segmenter(), reader=Reader({}), catalogue=CAT)
    assert coverage_lines(report, [], (b"wav", "audio/wav")) == [
        "Photos received: 0.", "Voice note: turns 1; medicines could not be extracted.",
    ]


def test_an_empty_intake_still_renders_every_section():
    report = intake(None, [])
    items, page = coverage_items(report, [], None)
    assert section_ids(page) == SECTIONS
    assert all("None." in page.by_id(section).text()
               for section in ("disagree", "across", "unconfirmed", "agree", "stopped"))
    assert items == ["Photos received: 0.", "Voice note: none."]


# --- cross-medication observations: what the patient reports, never the photos -------------------------------

@pytest.mark.parametrize(("names", "expected"), [
    (["Concor", "Beloc-Zok"], [("same_class", "beta-blockers", ("c1", "c2"))]),
    (["Panadol", "Gelocatil"], [("same_ingredient", "paracetamol", ("c1", "c2"))]),
    (["Panadol", "paracetamol"], [("same_ingredient", "paracetamol", ("c1", "c2"))]),
    (["Panadol", "Panadol Extra"], [("same_ingredient", "paracetamol", ("c1", "c2"))]),
    (["Panadol", "بنادول"], []),  # one brand said twice, in two scripts
    (["Concor", "كونكور"], []),
    (["Concor", "Xyzzy"], []),  # an unresolvable name has no identity set
    (["Concor", "Norvasc"], []),
    (["Panadol", "Gelocatil", "Panadol Extra"], [("same_ingredient", "paracetamol", ("c1", "c2", "c3"))]),
    (["Gelocatil", "Beloc-Zok", "Panadol", "Concor"],
     [("same_ingredient", "paracetamol", ("c1", "c3")), ("same_class", "beta-blockers", ("c2", "c4"))]),
])
def test_cross_medication_from_what_the_patient_reports(names, expected):
    claims = [claim(f"c{i}", name) for i, name in enumerate(names, 1)]
    found = [(o.kind, o.key, tuple(o.claim_ids)) for o in cross_medication(claims, CAT)]
    assert found == [(OverlapKind(kind), key, ids) for kind, key, ids in expected]


def test_stopped_medicines_never_count_but_an_unknown_status_does():
    claims = [claim("c1", "Panadol", status="discontinued"), claim("c2", "Gelocatil"),
              claim("c3", "Concor", status="unknown"), claim("c4", "Beloc-Zok")]
    [found] = cross_medication(claims, CAT)
    assert (found.kind, found.key, tuple(found.claim_ids)) == (OverlapKind.SAME_CLASS, "beta-blockers", ("c3", "c4"))


def test_an_observation_carries_its_claims_turns_and_its_fixed_note():
    claims = [claim("c1", "Concor", ["turn-2", "turn-0"]), claim("c2", "Beloc-Zok", ["turn-0"])]
    [found] = cross_medication(claims, CAT)
    assert tuple(found.audio_evidence) == ("turn-0", "turn-2") and found.note == SAME_CLASS
    [found] = cross_medication([claim("c1", "Panadol"), claim("c2", "Gelocatil")], CAT)
    assert found.note == SAME_INGREDIENT


def test_identity_can_come_from_the_strength_not_only_the_name():
    pill = claim("c1", "my heart pill", strength=st(mg("bisoprolol", 5)))
    [found] = cross_medication([pill, claim("c2", "Beloc-Zok")], CAT)
    assert (found.kind, found.key) == (OverlapKind.SAME_CLASS, "beta-blockers")


def test_the_class_map_is_small_and_explicit():
    assert {name: set(members) for name, members in DRUG_CLASSES.items()} == {
        "beta-blockers": {"bisoprolol", "metoprolol"}}


def test_photographed_packs_never_make_an_overlap():
    photo = png(400, 200, (170, 170, 170))
    panadol, gelocatil = region_on(photo, (10, 10, 189, 189), 0, 0.9), region_on(photo, (210, 10, 389, 189), 1, 0.8)
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=3000, transcript="Panadol when I need it.")]
    report = intake(b"wav", [(photo, "image/png")], turns=turns, claims=[claim("c1", "Panadol", ["turn-0"])],
                    by_sha={panadol.image_sha256: [panadol, gelocatil]},
                    reads={panadol.region_id: [reading("Panadol 500 mg", st(mg("paracetamol", 500)))],
                           gelocatil.region_id: [reading("Gelocatil 1 g", st(mg("paracetamol", 1, "g")))]})
    assert cross_medication(report.claims, CAT) == []
    page = Page(render_brief(report, [(photo, "image/png")], (b"wav", "audio/wav"), CAT)).root
    assert not page.by_id("across").find_all("article") and "None." in page.by_id("across").text()


# --- the hero case (J2): two brand names, one medicine ----------------------------------------------------

def test_gelocatil_is_in_the_catalogue():
    entry = CAT.resolve("Gelocatil 1 g")
    assert entry is not None and entry.brand == "Gelocatil" and entry.inns == frozenset({"paracetamol"})
    assert entry.countries == ("ES",) and entry.synthetic and entry.release.value == "immediate"
    assert entry.splittable is None
    assert all(CAT.resolve(name).brand == "Gelocatil" for name in ("جيلوكاتيل", "جلوكاتيل", "والجيلوكاتيل"))
    assert CAT.resolve("Panadol 500 mg paracetamol").brand == "Panadol"


def hero_packs():
    return [
        PackObservation(observation_id="o0", label_text="Panadol 500 mg", readability="readable",
                        strength=st(mg("paracetamol", 500), release="immediate"), visual_evidence=["r-0"]),
        PackObservation(observation_id="o1", label_text="Gelocatil 1 g", readability="readable",
                        strength=st(mg("paracetamol", 1, "g"), release="immediate"), visual_evidence=["r-1"]),
    ]


def test_pairing_prefers_the_same_product_within_a_score():
    # Mentioned in the opposite order to the photos: ID order alone would pair Gelocatil's claim with Panadol's pack.
    claims = [claim("c1", "Gelocatil", intake=mg("paracetamol", 1, "g")),
              claim("c2", "Panadol", intake=mg("paracetamol", 500))]
    findings = reconcile_all(claims, hero_packs(), CAT)
    assert {(f.claim_id, f.observation_id): f.type for f in findings} == {("c1", "o1"): D.MATCH,
                                                                           ("c2", "o0"): D.MATCH}
    assert reconcile_all(claims[::-1], hero_packs()[::-1], CAT) == findings


def test_two_brand_names_one_medicine_in_the_brief():
    photo = png(400, 200, (180, 180, 180))
    panadol, gelocatil = region_on(photo, (10, 10, 189, 189), 0, 0.9), region_on(photo, (210, 10, 389, 189), 1, 0.8)
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=5000, transcript="Gelocatil 1 g for headaches."),
             AudioTurn(turn_id="turn-1", start_ms=5000, end_ms=9000, transcript="Panadol 500 mg for my back.")]
    claims = [claim("c1", "Gelocatil", ["turn-0"], intake=mg("paracetamol", 1, "g")),
              claim("c2", "Panadol", ["turn-1"], intake=mg("paracetamol", 500))]
    images = [(photo, "image/png")]
    report = intake(b"wav", images, turns=turns, claims=claims, by_sha={panadol.image_sha256: [panadol, gelocatil]},
                    reads={panadol.region_id: [reading("Panadol 500 mg", st(mg("paracetamol", 500),
                                                                          release="immediate"))],
                           gelocatil.region_id: [reading("Gelocatil 1 g", st(mg("paracetamol", 1, "g"),
                                                                           release="immediate"))]})
    assert {(f.claim_id, f.observation_id): f.type for f in report.findings} == {("c1", "o1"): D.MATCH,
                                                                                  ("c2", "o0"): D.MATCH}
    page = Page(render_brief(report, images, (b"wav", "audio/wav"), CAT)).root
    assert "None." in page.by_id("disagree").text()
    assert article_ids(page.by_id("agree")) == ["finding:c1:o1", "finding:c2:o0"]
    [node] = page.by_id("across").find_all("article")
    assert node.attrs["data-kind"] == "same_ingredient"
    assert SAME_INGREDIENT in node.text() and "paracetamol" in node.text()
    assert {"#turn:turn-0", "#turn:turn-1"} <= hrefs(node)
