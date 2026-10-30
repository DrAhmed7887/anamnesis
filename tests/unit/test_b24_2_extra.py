"""Batch 24.2 extras: no codes beside a side that contradicts its own name."""

from decimal import Decimal

from anamnesis.agent.loop import _intake_id, _prepare
from anamnesis.brief import render_brief
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all
from anamnesis.schema import AudioTurn, IngredientAmount, PatientClaim, Strength
from anamnesis.schema.report import AgentAction, AgentStep, ReconciliationReport
from anamnesis.schema.templates import CATALOGUE_CODES_REFERENCE

CAT = load_catalogue()
WHO = "WHO Collaborating Centre for Drug Statistics Methodology"


def _report(audio, turns, claims, findings):
    prepared = _prepare([])
    intake_id = _intake_id(audio[0], [photo for photo, _, _ in prepared])
    step = AgentStep(n=0, action=AgentAction.EXTRACT_CLAIMS, target="turns", outcome="1 claims")
    return ReconciliationReport(
        intake_id=intake_id,
        turns=turns,
        claims=claims,
        regions=[],
        observations=[],
        findings=findings,
        steps=[step],
        calls=0,
        spend_usd=Decimal(0),
    )


def test_panadol_extra_with_single_ingredient_strength_shows_no_codes_line():
    audio = (b"wav", "audio/wav")
    turn = AudioTurn(turn_id="t0", start_ms=0, end_ms=1000, transcript="Panadol Extra paracetamol 500 mg")
    strength = Strength(
        ingredients=[IngredientAmount(inn="paracetamol", amount=Decimal(500), unit="mg")],
        per="tablet",
        release="unknown",
    )
    said = PatientClaim(
        claim_id="c1", name_text="Panadol Extra", strength=strength, status="active",
        audio_evidence=["t0"],
    )
    findings = reconcile_all([said], [], CAT)
    report = _report(audio, [turn], [said], findings)
    html = render_brief(report, [], audio, CAT)
    assert "Catalogue codes:" not in html
    assert WHO not in html
    assert CATALOGUE_CODES_REFERENCE not in html
