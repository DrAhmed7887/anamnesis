"""Focused offline checks for the batch 19 clinician brief and its helpers."""

import hashlib
import io
from decimal import Decimal

from PIL import Image

from anamnesis.agent.loop import _intake_id, _prepare
from anamnesis.brief import coverage_lines, render_brief
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.guardrails import assert_no_advice
from anamnesis.core.overlap import DRUG_CLASSES, OverlapKind, cross_medication
from anamnesis.core.reconcile import reconcile_all
from anamnesis.providers.meta import spark_call_estimate
from anamnesis.schema import (
    AudioTurn,
    DoseRegimen,
    ImageRegion,
    IngredientAmount,
    PackObservation,
    PatientClaim,
    Strength,
)
from anamnesis.schema.report import AgentAction, AgentStep, ReconciliationReport
from anamnesis.schema.templates import (
    COVERAGE_BUDGET,
    FIELD_COUNTRY,
    FIELD_INN,
    FIELD_INTAKE,
    FIELD_LABEL,
    FIELD_NAME,
    FIELD_READABILITY,
    FIELD_REGIMEN,
    FIELD_STATUS,
    FIELD_STRENGTH,
    HEARD_IN,
    HEARD_TURN,
    MENTIONED_NOT_PHOTOGRAPHED,
    NO,
    NOT_MENTIONED,
    NOT_PHOTOGRAPHED,
    NOT_READ,
    PHOTO_ALT,
    PHOTOGRAPHED_NOT_MENTIONED,
    REGIMEN_AS_NEEDED,
    REGIMEN_INTAKES_PER_DAY,
    REGIMEN_UNITS_PER_INTAKE,
    REGION_ALT,
    REGION_CAPTION,
    REPORTED_STOPPED_NOT_PHOTOGRAPHED,
    SAME_CLASS_NOTE,
    SAME_INGREDIENT_NOTE,
    SCOPE_LINES,
    SECTION_HEADINGS,
    SECTION_ORDER,
    SEEN_IN,
    SEEN_REGION,
    STRENGTH_PER,
    TURN_BUTTON,
    YES,
)

CAT = load_catalogue()


def png(w=200, h=100):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (200, 200, 200)).save(buf, "PNG")
    return buf.getvalue()


def region_on(image, box, obj=0):
    sha = hashlib.sha256(image).hexdigest()
    w, h = Image.open(io.BytesIO(image)).size
    return ImageRegion(
        region_id=f"{sha[:12]}-{obj}", image_sha256=sha, object_id=obj,
        x1=box[0], y1=box[1], x2=box[2], y2=box[3], frame_w=w, frame_h=h,
    )


def mg(inn, amount):
    return IngredientAmount(inn=inn, amount=Decimal(str(amount)), unit="mg")


def claim(cid, name, turns=None, status="active"):
    return PatientClaim(
        claim_id=cid, name_text=name, status=status, audio_evidence=turns or [f"turn-{cid}"],
    )


def report(**over):
    base = {
        "intake_id": "0" * 64, "turns": [], "claims": [], "regions": [],
        "observations": [], "findings": [], "steps": [], "calls": 0,
        "spend_usd": Decimal(0),
    }
    return ReconciliationReport(**{**base, **over})


def valid_report(images, audio, **over):
    """A hand-made report whose intake_id matches the given media."""
    prepared = _prepare(images)
    audio_bytes = audio[0] if audio is not None else None
    intake_id = _intake_id(audio_bytes, [photo for photo, _, _ in prepared])
    return report(intake_id=intake_id, **over)


def step(action, target="t", outcome="ok"):
    return AgentStep(n=0, action=action, target=target, outcome=outcome)


def test_fixed_text_carries_no_advice():
    for line in [*SCOPE_LINES, SAME_INGREDIENT_NOTE, SAME_CLASS_NOTE, COVERAGE_BUDGET,
                 MENTIONED_NOT_PHOTOGRAPHED, PHOTOGRAPHED_NOT_MENTIONED,
                 REPORTED_STOPPED_NOT_PHOTOGRAPHED, NOT_MENTIONED, NOT_PHOTOGRAPHED,
                 NOT_READ, *SECTION_HEADINGS.values(),
                 FIELD_NAME, FIELD_INN, FIELD_STRENGTH, FIELD_INTAKE, FIELD_REGIMEN, FIELD_STATUS,
                 FIELD_LABEL, FIELD_READABILITY, FIELD_COUNTRY,
                 STRENGTH_PER, REGIMEN_UNITS_PER_INTAKE, REGIMEN_INTAKES_PER_DAY,
                 REGIMEN_AS_NEEDED, YES, NO, PHOTO_ALT, REGION_ALT,
                 HEARD_IN, SEEN_IN, SEEN_REGION, HEARD_TURN, TURN_BUTTON, REGION_CAPTION]:
        assert_no_advice(line)


def test_section_order_has_all_eight():
    assert SECTION_ORDER == (
        "disagree", "across", "unconfirmed", "agree", "stopped", "coverage", "photos", "voice",
    )


def test_class_map_has_only_beta_blockers():
    assert set(DRUG_CLASSES) == {"beta-blockers"}


def test_estimate_ignores_a_missing_reply_schema():
    body = {"model": "muse-spark-1.3", "max_tokens": 8,
            "messages": [{"role": "user", "content": "hi"}]}
    assert spark_call_estimate(body) == spark_call_estimate({**body, "messages": body["messages"]})


def test_brand_entry_returns_none_for_an_inn():
    assert CAT.brand_entry("paracetamol") is None
    assert CAT.brand_entry("Gelocatil").brand == "Gelocatil"


def test_overlap_orders_ingredient_before_class():
    claims = [claim("c1", "Gelocatil"), claim("c2", "Panadol"),
              claim("c3", "Concor"), claim("c4", "Beloc-Zok")]
    found = [(o.kind, o.key) for o in cross_medication(claims, CAT)]
    assert found == [(OverlapKind.SAME_INGREDIENT, "paracetamol"),
                     (OverlapKind.SAME_CLASS, "beta-blockers")]


def test_overlap_sorts_ids_and_turns():
    claims = [claim("c2", "Gelocatil", ["turn-1", "turn-0"]), claim("c1", "Panadol", ["turn-0"])]
    [found] = cross_medication(claims, CAT)
    assert found.claim_ids == ("c1", "c2")
    assert found.audio_evidence == ("turn-0", "turn-1")


def test_photo_with_no_segment_step_is_not_examined():
    photo = png()
    images = [(photo, "image/png")]
    rep = valid_report(images, (b"wav", "audio/wav"),
                       steps=[step(AgentAction.TRANSCRIBE, "audio", "1 turns")])
    lines = coverage_lines(rep, images, (b"wav", "audio/wav"))
    assert lines[1] == "Photo 1: not examined; the call budget ran out first."


def test_partial_counts_as_not_fully_readable():
    photo = png()
    images = [(photo, "image/png")]
    region = region_on(photo, (10, 10, 99, 60))
    obs = PackObservation(
        observation_id="o0", label_text="Concor 5 mg", readability="partial",
        strength=Strength(ingredients=[mg("bisoprolol", 5)], per="tablet"),
        visual_evidence=[region.region_id],
    )
    sha = hashlib.sha256(photo).hexdigest()
    rep = valid_report(images, None, regions=[region], observations=[obs],
                       steps=[step(AgentAction.SEGMENT, f"{sha[:12]}:label", "1 regions")])
    assert coverage_lines(rep, images, None)[1] == (
        "Photo 1: packs found 1, labels read 1, not fully readable 1."
    )


def test_brief_escapes_hostile_source_text():
    photo = png()
    images = [(photo, "image/png")]
    turn = AudioTurn(turn_id="t0", start_ms=0, end_ms=500, transcript="<b>Concor</b>")
    rep = valid_report(images, (b"wav", "audio/wav"), turns=[turn], claims=[claim("c1", "<i>x</i>", ["t0"])])
    html = render_brief(rep, images, (b"wav", "audio/wav"), CAT)
    assert "<b>Concor</b>" not in html and "&lt;b&gt;Concor&lt;/b&gt;" in html
    assert html.count("<script>") == 1


def test_brief_amounts_print_as_plain_decimals():
    images = []
    audio = (b"wav", "audio/wav")
    turn = AudioTurn(turn_id="t0", start_ms=0, end_ms=500, transcript="Concor")
    said = PatientClaim(
        claim_id="c1", name_text="Concor",
        intake_amount=IngredientAmount(inn="bisoprolol", amount=Decimal("100.0"), unit="mg"),
        regimen=DoseRegimen(units_per_intake=Decimal("0.50")), status="active",
        audio_evidence=["t0"],
    )
    findings = reconcile_all([said], [], CAT)
    rep = valid_report(images, audio, turns=[turn], claims=[said], findings=findings,
                       steps=[step(AgentAction.EXTRACT_CLAIMS, "turns", "1 claims")])
    html = render_brief(rep, images, audio, CAT)
    assert "100 mg" in html and "0.5" in html
    assert "100.0" not in html and "0.50" not in html


def test_boxes_are_transparent_outlines():
    rep = valid_report([], None)
    html = render_brief(rep, [], None, CAT)
    style = html.split("<style>")[1].split("</style>")[0]
    assert "fill:transparent" in style
    assert "#d9480f" in style and "stroke-width:3" in style
    assert "vector-effect:non-scaling-stroke" in style


def test_round2_page_marks():
    photo = png()
    images = [(photo, "image/png")]
    audio = (b"wav", "audio/wav")
    turn = AudioTurn(turn_id="t0", start_ms=0, end_ms=12000, transcript="Concor 5 mg")
    said = claim("c1", "Concor", ["t0"])
    region = region_on(photo, (10, 10, 99, 60))
    obs = PackObservation(
        observation_id="o0", label_text="Concor 5 mg", readability="readable",
        strength=Strength(ingredients=[mg("bisoprolol", 5)], per="tablet"),
        visual_evidence=[region.region_id],
    )
    sha = hashlib.sha256(photo).hexdigest()
    findings = reconcile_all([said], [obs], CAT)
    rep = valid_report(images, audio, turns=[turn], claims=[said], regions=[region],
                       observations=[obs], findings=findings,
                       steps=[step(AgentAction.SEGMENT, f"{sha[:12]}:label", "1 regions"),
                              step(AgentAction.EXTRACT_CLAIMS, "turns", "1 claims")])
    html = render_brief(rep, images, audio, CAT)
    assert "<h1>Medication intake brief</h1>" in html
    assert '<button type="button">▶ 0:00–0:12</button>' in html
    assert "Heard in:" in html and "Seen in:" in html
    assert "t0 (0:00–0:12)" in html
    assert f"region {region.region_id}" in html
    assert "<figcaption>" in html and "Photo 1" in html and region.region_id in html
    assert 'dir="auto"' in html
    assert "img{max-width:100%;height:auto}" in html
    assert "#disagree article{border-inline-start:4px solid #d9480f}" in html


def test_across_links_use_claim_names():
    images = []
    audio = (b"wav", "audio/wav")
    turns = [AudioTurn(turn_id="t0", start_ms=0, end_ms=1000, transcript="Concor"),
             AudioTurn(turn_id="t1", start_ms=1000, end_ms=2000, transcript="Beloc-Zok")]
    claims = [claim("c1", "Concor", ["t0"]), claim("c2", "Beloc-Zok", ["t1"])]
    findings = reconcile_all(claims, [], CAT)
    rep = valid_report(images, audio, turns=turns, claims=claims, findings=findings,
                       steps=[step(AgentAction.EXTRACT_CLAIMS, "turns", "2 claims")])
    html = render_brief(rep, images, audio, CAT)
    assert '<a href="#turn:t0" dir="auto">Concor</a>' in html
    assert '<a href="#turn:t1" dir="auto">Beloc-Zok</a>' in html
