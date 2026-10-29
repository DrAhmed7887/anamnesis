"""Batch 24.1 extras: ATC-only codes, pack-only findings, one reference line."""

import hashlib
import io
from decimal import Decimal

from PIL import Image

from anamnesis.agent.loop import _intake_id, _prepare
from anamnesis.brief import render_brief
from anamnesis.core.catalogue import Catalogue, CatalogueEntry, load_catalogue
from anamnesis.core.reconcile import reconcile_all
from anamnesis.schema import AudioTurn, ImageRegion, PackObservation, PatientClaim, Release
from anamnesis.schema.report import AgentAction, AgentStep, ReconciliationReport
from anamnesis.schema.templates import CATALOGUE_CODES_REFERENCE

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


def valid_report(images, audio, **over):
    prepared = _prepare(images)
    audio_bytes = audio[0] if audio is not None else None
    intake_id = _intake_id(audio_bytes, [photo for photo, _, _ in prepared])
    base = {
        "intake_id": intake_id, "turns": [], "claims": [], "regions": [],
        "observations": [], "findings": [], "steps": [], "calls": 0,
        "spend_usd": Decimal(0),
    }
    return ReconciliationReport(**{**base, **over})


def step(action, target="t", outcome="ok"):
    return AgentStep(n=0, action=action, target=target, outcome=outcome)


def test_entry_with_atc_and_no_rxcui_shows_only_atc():
    entry = CatalogueEntry(
        brand="Testonly", inns=frozenset({"testinn"}), countries=("ES",),
        synthetic=True, release=Release.IMMEDIATE, splittable=None,
        atc="A01AA01", rxcui=(),
    )
    cat = Catalogue((entry,))
    audio = (b"wav", "audio/wav")
    turn = AudioTurn(turn_id="t0", start_ms=0, end_ms=1000, transcript="Testonly")
    said = PatientClaim(claim_id="c1", name_text="Testonly", status="active", audio_evidence=["t0"])
    findings = reconcile_all([said], [], cat)
    rep = valid_report(images=[], audio=audio, turns=[turn], claims=[said], findings=findings,
                       steps=[step(AgentAction.EXTRACT_CLAIMS, "turns", "1 claims")])
    html = render_brief(rep, [], audio, cat)
    assert html.count("Catalogue codes:") == 1
    assert "Catalogue codes: ATC A01AA01</p>" in html
    assert CATALOGUE_CODES_REFERENCE in html


def test_pack_only_finding_shows_its_pack_codes():
    photo = png()
    images = [(photo, "image/png")]
    region = region_on(photo, (10, 10, 99, 60))
    obs = PackObservation(
        observation_id="o0", label_text="Concor 5 mg", readability="readable",
        visual_evidence=[region.region_id],
    )
    findings = reconcile_all([], [obs], CAT)
    assert len(findings) == 1 and findings[0].claim_id is None
    sha = hashlib.sha256(photo).hexdigest()
    rep = valid_report(images, None, regions=[region], observations=[obs], findings=findings,
                       steps=[step(AgentAction.SEGMENT, f"{sha[:12]}:label", "1 regions")])
    html = render_brief(rep, images, None, CAT)
    assert "Catalogue codes: ATC C07AB07" in html and "RxNorm 19484" in html
    assert CATALOGUE_CODES_REFERENCE in html


def test_reference_line_appears_once_with_three_coded_findings():
    audio = (b"wav", "audio/wav")
    names = ["Concor", "Norvasc", "Lipitor"]
    turns = [
        AudioTurn(turn_id=f"t{i}", start_ms=i * 1000, end_ms=(i + 1) * 1000, transcript=name)
        for i, name in enumerate(names)
    ]
    claims = [
        PatientClaim(claim_id=f"c{i + 1}", name_text=name, status="active", audio_evidence=[f"t{i}"])
        for i, name in enumerate(names)
    ]
    findings = reconcile_all(claims, [], CAT)
    assert len(findings) == 3
    rep = valid_report([], audio, turns=turns, claims=claims, findings=findings,
                       steps=[step(AgentAction.EXTRACT_CLAIMS, "turns", "3 claims")])
    html = render_brief(rep, [], audio, CAT)
    assert html.count("Catalogue codes:") == 3
    assert html.count(CATALOGUE_CODES_REFERENCE) == 1
    assert html.index(CATALOGUE_CODES_REFERENCE) > html.index('id="voice"')
