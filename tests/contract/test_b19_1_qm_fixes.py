"""Batch 19.1 contract: the quality manager's M4 fixes (evidence/grills/m4-muse-brief/effect.md). Written by the CEO;
Muse must not edit it.

SPEC §2: the Arabic decimal sign parses; Arabic advice words are caught with attached clitics and marks.
SPEC §3: feminine Arabic release words count as said; the formulation note names salt or release.
SPEC §7: both salts show on the brief; a conflicted claim makes no overlap; a scope line says what the checks across
medicines cover; a region whose photo is missing is refused; turn playback is run in Node; Arabic source text is
marked dir="auto".
"""

import json
import shutil
import subprocess
from decimal import Decimal

import pytest

from anamnesis.brief import render_brief
from anamnesis.core.guardrails import AdviceLeak, assert_no_advice
from anamnesis.core.overlap import OverlapKind, cross_medication
from anamnesis.core.reconcile import reconcile_pair
from anamnesis.providers.numbers import parse_amount_text
from anamnesis.schema import AudioTurn, ImageRegion, PackObservation
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.templates import TEMPLATES
from tests.contract.test_b19_brief import (
    AUDIO,
    CAT,
    PHOTO,
    RC,
    Page,
    claim,
    intake,
    mg,
    reading,
    showcase,
    st,
)

FORMULATION_NOTE = "Reported and pack formulations differ (salt or release form)."
ACROSS_SCOPE = ("Checks across medicines cover shared ingredients and one curated class (beta-blockers); "
                "interactions were not assessed.")


# --- §2: Arabic numbers and advice words ------------------------------------------------------------------

@pytest.mark.parametrize(("text", "value"), [
    ("٢٫٥", Decimal("2.5")), ("2٫5", Decimal("2.5")), ("٠٫١٢٥", Decimal("0.125")),
    ("٥", Decimal(5)), ("١٠٠", Decimal(100)), ("٢,٥", Decimal("2.5")),
])
def test_arabic_digits_and_the_arabic_decimal_sign_parse(text, value):
    assert parse_amount_text(text) == value


@pytest.mark.parametrize("text", ["١٬٠٠٠", "١٫٠٠٠", "٢٫٥٫١", "٫٥"])
def test_ambiguous_arabic_amounts_do_not_parse(text):
    assert parse_amount_text(text) is None


@pytest.mark.parametrize("text", [
    "وتناول قرصا", "فيجب أن", "بتناول الدواء", "لتوقف", "والتناول", "تَناوَل", "تـناول", "Take one daily",
])
def test_arabic_advice_words_are_caught_with_clitics_and_marks(text):
    with pytest.raises(AdviceLeak):
        assert_no_advice(text)


@pytest.mark.parametrize("text", ["كونكور ٥ ملغ", "البنادول", "بيلوك زوك", "metoprolol succinate", "الصيدلية", "مناولة"])
def test_names_without_advice_still_pass(text):
    assert_no_advice(text)


# --- §3: feminine release words, the formulation note --------------------------------------------------

BELOC = PackObservation(observation_id="o0", label_text="Beloc-Zok 100 mg", readability="readable",
                        strength=st(mg("metoprolol succinate", 100), release="modified"), visual_evidence=["r-0"])


@pytest.mark.parametrize("said", [
    "ميتوبرولول ممتد", "ميتوبرولول ممتدة", "ميتوبرولول الممتدة", "ميتوبرولول بطيئة", "ميتوبرولول والبطيئة",
])
def test_feminine_arabic_release_words_count_as_said(said):
    # Said, the claim's modified release counts and agrees with the pack; unsaid, it falls back to unknown.
    stated = claim("c1", said, strength=st(mg("metoprolol", 100), release="modified"))
    assert reconcile_pair(stated, BELOC, CAT).type is D.MATCH


def test_the_formulation_note_names_salt_or_release():
    assert TEMPLATES[D.FORMULATION_MISMATCH] == FORMULATION_NOTE
    assert_no_advice(FORMULATION_NOTE)


# --- §7: the brief -------------------------------------------------------------------------------------

def test_both_salts_show_when_only_the_salts_differ():
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=3000, transcript="Metoprolol 100, half a tablet.")]
    said = claim("c1", "Metoprolol", ["turn-0"], strength=st(mg("metoprolol tartrate", 100)),
                 intake=mg("metoprolol tartrate", 50))
    read = reading("Beloc-Zok 100 mg", st(mg("metoprolol succinate", 100), release="modified"))
    report = intake(b"wav", [(PHOTO, "image/png")], turns=turns, claims=[said], by_sha={RC.image_sha256: [RC]},
                    reads={RC.region_id: [read]})
    [finding] = report.findings
    assert finding.type is D.FORMULATION_MISMATCH
    page = Page(render_brief(report, [(PHOTO, "image/png")], (b"wav", "audio/wav"), CAT)).root
    node = page.by_id(f"finding:{finding.finding_id}")
    patient = node.find_all(data_side="patient")[0].text()
    pack = node.find_all(data_side="pack")[0].text()
    assert patient.count("tartrate") == 2 and "succinate" not in patient  # the strength and the intake
    assert "succinate" in pack and "tartrate" not in pack
    assert FORMULATION_NOTE in node.text()


def test_a_conflicted_claim_makes_no_overlap():
    conflicted = claim("c1", "Concor", strength=st(mg("metoprolol", 50)))  # the name says bisoprolol
    assert cross_medication([conflicted, claim("c2", "Beloc-Zok")], CAT) == []
    two_products = claim("c1", "Concor Beloc-Zok", strength=st(mg("bisoprolol", 5)))
    assert cross_medication([two_products, claim("c2", "Beloc-Zok")], CAT) == []
    found = cross_medication([conflicted, claim("c2", "Panadol"), claim("c3", "Gelocatil")], CAT)
    assert [(o.kind, o.key, tuple(o.claim_ids)) for o in found] == [
        (OverlapKind.SAME_INGREDIENT, "paracetamol", ("c2", "c3"))]


def test_the_brief_states_what_the_checks_across_medicines_cover():
    _, _, page, _ = showcase()
    assert ACROSS_SCOPE in page.by_id("scope").text()


def test_a_region_whose_photo_is_missing_is_refused():
    report = showcase()[0]
    stray = ImageRegion(region_id="ffffffffffff-9", image_sha256="f" * 64, object_id=9, x1=0, y1=0, x2=9, y2=9,
                        frame_w=10, frame_h=10)
    with pytest.raises(ValueError):
        render_brief(report.model_copy(update={"regions": [*report.regions, stray]}), [(PHOTO, "image/png")],
                     AUDIO, CAT)


def direction(node):
    """The nearest dir attribute, on the node or an ancestor."""
    while node is not None and node.tag != "#root":
        if "dir" in node.attrs:
            return node.attrs["dir"]
        node = node.parent
    return None


def test_arabic_source_text_is_marked_dir_auto():
    transcript = "انا باخد كونكور خمسة ملي جرام وبيلوك زوك خمسين"
    turns = [AudioTurn(turn_id="turn-0", start_ms=0, end_ms=5000, transcript=transcript)]
    claims = [claim("c1", "كونكور", ["turn-0"]), claim("c2", "بيلوك زوك", ["turn-0"])]
    label = "كونكور ٥ ملغ"
    report = intake(b"wav", [(PHOTO, "image/png")], turns=turns, claims=claims, by_sha={RC.image_sha256: [RC]},
                    reads={RC.region_id: [reading(label, st(mg("bisoprolol", 5)))]})
    page = Page(render_brief(report, [(PHOTO, "image/png")], (b"wav", "audio/wav"), CAT)).root
    for text in ("كونكور", "بيلوك زوك", label, transcript):
        holders = [node for node in page.walk() for child in node.children if isinstance(child, str) and text in child]
        assert holders and all(direction(node) == "auto" for node in holders), text


# The page's one script, run in Node against a small DOM: the turn list, the links to turns, and one audio element.
HARNESS = r"""
function matches(element, selector) {
  return selector.split(",").some(function (one) {
    const m = one.trim().match(/^([a-z]*)(?:\[([\w-]+)(?:(\^?=)"([^"]*)")?\])?$/);
    if (!m) throw new Error("unsupported selector: " + one);
    const tag = m[1], attr = m[2], op = m[3], value = m[4];
    if (tag && element.tag !== tag) return false;
    if (!attr) return Boolean(tag);
    const found = element.getAttribute(attr);
    if (found === null) return false;
    if (!op) return true;
    return op === "^=" ? found.startsWith(value) : found === value;
  });
}
function element(tag, attrs) {
  const node = {tag: tag, attrs: attrs, listeners: {}, id: attrs.id || "",
    getAttribute: function (name) { return name in attrs ? String(attrs[name]) : null; },
    hasAttribute: function (name) { return name in attrs; },
    addEventListener: function (type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); },
    removeEventListener: function (type, fn) {
      this.listeners[type] = (this.listeners[type] || []).filter(function (f) { return f !== fn; }); },
    matches: function (selector) { return matches(this, selector); },
    closest: function (selector) { return matches(this, selector) ? this : null; }};
  node.dataset = new Proxy({}, {get: function (_, key) {
    const value = node.getAttribute("data-" + String(key).replace(/[A-Z]/g, function (c) { return "-" + c.toLowerCase(); }));
    return value === null ? undefined : value; }});
  return node;
}
const audio = element("audio", {});
audio.currentTime = 0; audio.paused = true;
audio.play = function () { this.paused = false; return Promise.resolve(); };
audio.pause = function () { this.paused = true; };
const turns = PAGE.turns.map(function (t) { return element("li", {id: t.id, "data-start-ms": t.start, "data-end-ms": t.end}); });
const links = PAGE.links.map(function (href) { return element("a", {href: href}); });
const all = [audio].concat(turns, links);
const docListeners = {};
function listen(type, fn) { (docListeners[type] = docListeners[type] || []).push(fn); }
const document = {readyState: "loading", addEventListener: listen,
  querySelector: function (s) { return all.find(function (e) { return matches(e, s); }) || null; },
  querySelectorAll: function (s) { return all.filter(function (e) { return matches(e, s); }); },
  getElementById: function (id) { return all.find(function (e) { return e.attrs.id === id; }) || null; }};
const window = {document: document, addEventListener: listen};
function click(target) {
  const event = {type: "click", target: target, currentTarget: target, preventDefault: function () {},
                 stopPropagation: function () {}};
  (target.listeners.click || []).forEach(function (fn) { fn.call(target, event); });
  (docListeners.click || []).forEach(function (fn) { fn.call(document, event); });
}
function tick(seconds) {
  audio.currentTime = seconds;
  (audio.listeners.timeupdate || []).forEach(function (fn) { fn.call(audio, {type: "timeupdate"}); });
}
eval(SCRIPT);
(docListeners.DOMContentLoaded || []).forEach(function (fn) { fn({type: "DOMContentLoaded"}); });
const steps = [];
function note() { steps.push([audio.currentTime, audio.paused]); }
click(document.getElementById("turn:turn-0")); note();
tick(1); note();
click(document.getElementById("turn:turn-2")); note();
tick(9.25); note();
tick(13.05); note();
click(links.find(function (l) { return l.attrs.href === "#turn:turn-1"; })); note();
tick(9.05); note();
console.log(JSON.stringify({steps: steps, timeupdate_listeners: (audio.listeners.timeupdate || []).length}));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_turn_playback_plays_one_turn_at_a_time(tmp_path):
    _, _, page, _ = showcase()
    [script] = [node for node in page.walk() if node.tag == "script"]
    code = "".join(child for child in script.children if isinstance(child, str))
    turns = [{"id": n.attrs["id"], "start": n.attrs["data-start-ms"], "end": n.attrs["data-end-ms"]}
             for n in page.walk() if n.tag == "li" and n.attrs.get("id", "").startswith("turn:")]
    links = sorted({n.attrs["href"] for n in page.walk() if n.tag == "a" and n.attrs.get("href", "").startswith("#turn:")})
    harness = tmp_path / "play.js"
    harness.write_text(f"const PAGE = {json.dumps({'turns': turns, 'links': links})};\n"
                       f"const SCRIPT = {json.dumps(code)};\n{HARNESS}", encoding="utf-8")
    run = subprocess.run(["node", str(harness)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result["timeupdate_listeners"] == 1  # one listener, however many turns are clicked
    assert result["steps"] == [
        [0, False],      # turn-0 starts
        [1, False],
        [9, False],      # turn-2 clicked while turn-0 plays
        [9.25, False],   # turn-0's end (4 s) no longer applies
        [13.05, True],   # turn-2 stops at its own end
        [4, False],      # an evidence link plays turn-1
        [9.05, True],    # and it stops at turn-1's end
    ]
