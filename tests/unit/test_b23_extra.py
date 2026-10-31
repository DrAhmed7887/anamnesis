"""Batch 23 extra unit checks: timeline fields, digits, concepts, per-volume rule."""

import inspect
import json
from decimal import Decimal

import pytest

from anamnesis.agent.loop import SAM_CONCEPTS, run_intake
from anamnesis.agent.session import IntakeSession
from anamnesis.brief_html import _timeline_html
from anamnesis.core.catalogue import load_catalogue, normalise
from anamnesis.providers.base import ProviderError, ProviderTrace
from anamnesis.providers.spark import parse_label_json
from anamnesis.review import add_photo, new_review, request_photo
from anamnesis.schema import AudioTurn, PatientClaim
from anamnesis.schema.report import AgentAction, AgentStep, ReconciliationReport
from anamnesis.schema.templates import TIMELINE_COLUMNS


def _label(text, amount="250", unit="mg", per="ml"):
    return json.dumps({"label_text": text, "inn": "paracetamol", "country": None,
                       "readability": "readable",
                       "strength": {"ingredients": [{"inn": "paracetamol", "amount": amount,
                                                    "unit": unit}],
                                    "per": per, "release": "unknown"}})


def test_step_defaults_and_contributor_refused():
    step = AgentStep(n=0, action="read", target="r0", outcome="ok")
    assert (step.model_id, step.input_tokens, step.output_tokens, step.latency_ms,
            step.cost_usd) == (None, 0, 0, 0, Decimal(0))
    with pytest.raises(ValueError):
        AgentStep(n=0, action="read", target="r0", outcome="ok", model_id=" x-CONTRIBUTOR-y ")


def test_failed_call_without_attempt_trace_has_no_model():
    session = IntakeSession(2)
    error = ProviderError("spark", "bad", retryable=True, charged_call_ids=["c1"],
                          charged_usd=Decimal("0.002"))

    def fail():
        raise error

    assert session.call(AgentAction.READ, "r0", fail, str) is None
    [step] = session.steps
    assert (step.model_id, step.input_tokens, step.latency_ms) == (None, 0, 0)
    assert step.cost_usd == Decimal("0.002") == session.spend_usd


def test_normalise_maps_extended_arabic_indic_digits():
    assert normalise("۰۱۲۳۴۵۶۷۸۹") == "0123456789"
    assert normalise("کونکور ۵") == normalise("کونکور 5")


def test_default_concepts_end_with_package():
    params = inspect.signature(run_intake).parameters
    assert params["concepts"].default == ("medicine box", "label", "package")


@pytest.mark.parametrize("text", [
    "Syrup 250 mg/5 ml",
    "Syrup 1 g per 5 ml",
    "شراب ٢٥٠ ملجم in ٥ مل",
    "Drops 500 \u00b5g / 2 ml",
])
def test_per_volume_drops_strength_but_keeps_reading(text):
    amount = "1" if "1 g" in text else ("500" if "500" in text else "250")
    unit = "g" if "1 g" in text else ("mcg" if "500" in text else "mg")
    reading = parse_label_json(_label(text, amount=amount, unit=unit), "r1")
    assert reading.strength is None
    assert reading.label_text == text and reading.inn == "paracetamol"


@pytest.mark.parametrize(("text", "amount"), [
    ("Syrup 250 mg / 1 ml", "250"),
    ("Syrup 250 mg / 1.0 ML", "250"),
    # Round 5: "Tablets 500 mg, bottle 100 ml" moved to the drops (the tablet word comes
    # before the amount, so it is not a per-tablet print).
])
def test_per_one_ml_or_distant_volume_keeps_strength(text, amount):
    reading = parse_label_json(_label(text, amount=amount, per="tablet"), "r1")
    assert reading.strength is not None


def test_timeline_html_shows_none_and_total():
    steps = [
        AgentStep(n=0, action="read", target="r0", outcome="readable", call_ids=["c1"],
                  model_id="m", input_tokens=10, output_tokens=2, latency_ms=6500,
                  cost_usd=Decimal("0.001")),
        AgentStep(n=1, action="reconcile", target="all", outcome="1 findings"),
    ]
    report = ReconciliationReport(intake_id="0" * 64, turns=[], claims=[], regions=[],
                                  observations=[], findings=[], steps=steps, calls=1,
                                  spend_usd=Decimal("0.001"))
    html = _timeline_html(report)
    assert 'id="timeline"' in html and "<summary>How it got here</summary>" in html
    assert "6.5 s" in html and "$0.00100" in html and "—" in html
    assert "Total: 1 calls, $0.00100" in html


def test_value_error_attempt_trace_reaches_the_step():
    session = IntakeSession(2)
    trace = ProviderTrace(call_id="c9", model_id="m", latency_ms=9, input_tokens=3,
                          output_tokens=1, cost_usd=Decimal("0.004"))

    def fail():
        exc = ValueError("boom")
        exc.charged_call_ids = ["c9"]
        exc.charged_usd = Decimal("0.004")
        exc.attempt_trace = trace
        raise exc

    assert session.call(AgentAction.READ, "r0", fail, str) is None
    [step] = session.steps
    assert (step.model_id, step.input_tokens, step.output_tokens, step.latency_ms) == ("m", 3, 1, 9)
    assert step.cost_usd == Decimal("0.004")


# --- round 2: the volume rule in full (brief item 1) ---


@pytest.mark.parametrize(("text", "amount", "unit"), [
    ("شراب ۲٫۵ مجم/۵ مل", "2.5", "mg"),  # extended Arabic-Indic digits + ٫
    ("Syrup 500 ملغ/5 مل", "500", "mg"),
    ("Tonic 1000 units/5 ml", "1000", "iu"),
    ("Drops 500 وحدة/5 مل", "500", "mg"),
    ("شراب 250 مجم في 5 مل", "250", "mg"),
    ("Syrup 250 mg per each teaspoon 5 ml", "250", "mg"),
    # Round 5 counts a bare "spoon" too; "spoonful" still matches first.
    ("Syrup 250 mg per spoonful (5 ml)", "250", "mg"),
    ("250 مجم لكل ملعقة صغيرة (5 مل)", "250", "mg"),
    ("SYRUP 250 MG PER 5 ML", "250", "mg"),
    ("Every 5 cc has ibuprofen 100 mg", "100", "mg"),
    ("eAcH 5 ML contains 250 mg", "250", "mg"),
])
def test_round2_volume_forms_drop_the_strength(text, amount, unit):
    reading = parse_label_json(_label(text, amount=amount, unit=unit), "r1")
    assert reading.strength is None
    assert reading.label_text == text


@pytest.mark.parametrize(("text", "amount", "unit"), [
    ("Each 1 ml contains 250 mg", "250", "mg"),
    ("Syrup 250 mg/1.00 ml", "250", "mg"),
    ("Drops 10 mg/1 cc", "10", "mg"),
])
def test_round2_kept_volumes_keep_the_strength(text, amount, unit):
    reading = parse_label_json(_label(text, amount=amount, unit=unit), "r1")
    assert reading.strength is not None


# --- round 2: budgets and the shared concepts default (brief items 2-4) ---

CAT = load_catalogue()


def _budgets(monkeypatch, target):
    seen = []

    def spy(budget):
        seen.append(budget)
        return IntakeSession(budget)

    monkeypatch.setattr(target, spy)
    return seen


def test_run_intake_default_budget_follows_the_formula(monkeypatch):
    seen = _budgets(monkeypatch, "anamnesis.agent.loop.IntakeSession")
    run_intake(None, [], transcriber=None, extractor=None, segmenter=None, reader=None,
               catalogue=CAT)
    assert seen == [2]
    junk = [(b"not an image", "image/png"), (b"still not an image", "image/png")]
    run_intake(None, junk, transcriber=None, extractor=None, segmenter=None, reader=None,
               catalogue=CAT, concepts=("a", "b"), top_k=2)
    assert seen == [2, 2 + (2 + 2 * 2) * 2]


def test_run_intake_explicit_budget_is_used_as_given(monkeypatch):
    seen = _budgets(monkeypatch, "anamnesis.agent.loop.IntakeSession")
    run_intake(None, [], transcriber=None, extractor=None, segmenter=None, reader=None,
               catalogue=CAT, max_provider_calls=7)
    assert seen == [7]


def test_both_paths_share_sam_concepts():
    assert SAM_CONCEPTS == ("medicine box", "label", "package")
    assert inspect.signature(run_intake).parameters["concepts"].default is SAM_CONCEPTS
    assert inspect.signature(add_photo).parameters["concepts"].default is SAM_CONCEPTS


def test_budgets_default_to_none():
    assert inspect.signature(run_intake).parameters["max_provider_calls"].default is None
    assert inspect.signature(add_photo).parameters["max_provider_calls"].default is None


class _OneClaim:
    def __init__(self):
        self.turn = AudioTurn(turn_id="t1", start_ms=0, end_ms=100, transcript="Concor")
        self.claim = PatientClaim(claim_id="c1", name_text="Concor", status="active",
                                  audio_evidence=["t1"])

    def transcribe(self, audio, *, language_bias=None, keywords=None, lang_hint=None):
        return [self.turn], ProviderTrace(call_id="t", model_id="fixture:t", latency_ms=1,
                                          input_tokens=1, output_tokens=1,
                                          cost_usd=Decimal("0.001"))

    def extract(self, turns):
        assert [turn.turn_id for turn in turns] == ["t1"]
        return [self.claim], ProviderTrace(call_id="e", model_id="fixture:e", latency_ms=1,
                                           input_tokens=1, output_tokens=1,
                                           cost_usd=Decimal("0.001"))


def _photo_request():
    provider = _OneClaim()
    report = run_intake(b"fake-audio", [], transcriber=provider, extractor=provider,
                        segmenter=None, reader=None, catalogue=CAT)
    return report, request_photo(new_review(report), report, "c1")


def test_add_photo_default_budget_is_one_photos_worth(monkeypatch):
    seen = _budgets(monkeypatch, "anamnesis.review.IntakeSession")
    report, review = _photo_request()
    add_photo(report, review, "r1", (b"not an image either", "image/png"), [],
              (b"fake-audio", "audio/mpeg"), segmenter=None, reader=None, catalogue=CAT)
    assert seen == [3 + 2 * 3]


def test_add_photo_budget_follows_its_own_concepts_or_an_explicit_value(monkeypatch):
    seen = _budgets(monkeypatch, "anamnesis.review.IntakeSession")
    report, review = _photo_request()
    photo, audio = (b"not an image either", "image/png"), (b"fake-audio", "audio/mpeg")
    add_photo(report, review, "r1", photo, [], audio, segmenter=None, reader=None,
              catalogue=CAT, concepts=("x",), top_k=1)
    add_photo(report, review, "r1", photo, [], audio, segmenter=None, reader=None,
              catalogue=CAT, max_provider_calls=4)
    assert seen == [1 + 2 * 1, 4]


# --- round 3: the volume rule's last forms, and the timeline total ---


@pytest.mark.parametrize(("text", "amount", "unit"), [
    ("Syrup 250 mg por 5 ml", "250", "mg"),
    ("Syrup 250 mg par 5 ml", "250", "mg"),
    ("SYRUP 250 MG POR 5 ML", "250", "mg"),
    ("Syrup 250 mg per (5 ml)", "250", "mg"),
    ("Syrup 250 mg/(5 ml)", "250", "mg"),
    ("Syrup 250 mg per 5-mL teaspoon", "250", "mg"),
    ("Syrup 250 mg per 5 - ml", "250", "mg"),
    ("Syrup 250 mg in 5 millilitres", "250", "mg"),
    ("Syrup 250 mg per 5 milliliters", "250", "mg"),
    ("Syrup 250 mg per 5 millilitre", "250", "mg"),
    ("Syrup 250 mg / 2,5 ml", "250", "mg"),
    ("Syrup 250 mg per spoonful of 5 ml", "250", "mg"),
    ("Syrup 250 mg per tablespoon (5 ml)", "250", "mg"),
    ("Jarabe 250 mg por cucharada de 5 ml", "250", "mg"),
    ("Sirop 250 mg par cuillère de 5 ml", "250", "mg"),
    ("Syrup 250 mg/5 ملي", "250", "mg"),
    ("Each tablespoon (5 ml) contains 250 mg", "250", "mg"),
    ("Cada cucharada (5 ml) contiene 250 mg", "250", "mg"),
    ("Chaque cuillère de 5 ml contient 250 mg", "250", "mg"),
    ("Each 5 ml = 250 mg", "250", "mg"),
    ("Each 5 ml of suspension contains 250 mg", "250", "mg"),
    ("Every 5 ml has 250 mg", "250", "mg"),
    ("Each 5 ml contain 250 mg", "250", "mg"),
])
def test_round3_volume_forms_drop_the_strength(text, amount, unit):
    reading = parse_label_json(_label(text, amount=amount, unit=unit), "r1")
    assert reading.strength is None
    assert reading.label_text == text


@pytest.mark.parametrize(("text", "amount"), [
    # Round 5: the six "in 5 ml of water" lines moved to the drops (water never exempts
    # a reading per ml).
    ("Syrup 250 mg por 1 ml", "250"),
    ("Cada 1 ml contiene 250 mg", "250"),
    ("Augmentin 875 ملجم/125 ملجم", "875"),
])
def test_round3_kept_volumes_keep_the_strength(text, amount):
    reading = parse_label_json(_label(text, amount=amount), "r1")
    assert reading.strength is not None


def test_round3_timeline_total_spans_the_table():
    report = ReconciliationReport(intake_id="0" * 64, turns=[], claims=[], regions=[],
                                  observations=[], findings=[], steps=[], calls=0,
                                  spend_usd=Decimal("0"))
    html = _timeline_html(report)
    assert f'colspan="{len(TIMELINE_COLUMNS)}"' in html


# --- round 4: one clause rule ---


@pytest.mark.parametrize(("text", "amount"), [
    ("Syrup 250 mg within 5 ml", "250"),
    ("Syrup 250 mg import 5 ml", "250"),
    ("Syrup 250 mg apart 5 ml", "250"),
    ("peach 5 ml contains 250 mg", "250"),
    ("cascada 5 ml contiene 250 mg", "250"),
    ("Syrup 250 mg per spoon (5 ml)", "250"),
    ("Each 5 ml bottle contains 250 mg", "250"),
    ("Each 5 ml cup contains 250 mg", "250"),
    ("كل 5 مل عبوة تحتوي على 250 مجم", "250"),
    ("Each 5 ml twice daily, 250 mg tablets", "250"),
    ("Cada 5 ml twice daily 250 mg", "250"),
    ("Every 5 ml in the morning, Concor 5 mg", "5"),
])
def test_round4_wording_does_not_matter_for_ml(text, amount):
    reading = parse_label_json(_label(text, amount=amount, per="ml"), "r1")
    assert reading.strength is None
    assert reading.label_text == text


@pytest.mark.parametrize(("text", "amount", "per", "kept"), [
    ("Each 5 ml contains 250 mg tablets", "250", "tablet", False),
    ("Every 5 ml: shake well. Concor 5 mg", "5", "tablet", False),
    ("Take 5 ml daily; Panadol 500 mg tablets", "500", "tablet", True),
    # Round 5: "5 ml syrup\n500 mg capsules" now drops (the amount is later in the
    # volume's sentence) and "500 mg capsules in 5 ml syrup" is now kept (the capsule
    # print is right after the amount); both moved to the round 5 tests below.
])
def test_round4_tablet_print_cases(text, amount, per, kept):
    reading = parse_label_json(_label(text, amount=amount, per=per), "r1")
    assert (reading.strength is not None) is kept


@pytest.mark.parametrize(("text", "amount", "per"), [
    ("Disolver 500 mg en 200 ml de agua", "500", "tablet"),
    ("Dissoudre 500 mg dans 200 ml d'eau", "500", "tablet"),
    ("قرص 500 مجم في 200 مل ماء", "500", "tablet"),
    ("250 mg / 1.0 ml, 5 ml bottle", "250", "ml"),
    ("5 mg per ml, 5 ml syrup", "5", "ml"),
])
def test_round4_water_clause_or_per_1ml_keeps(text, amount, per):
    reading = parse_label_json(_label(text, amount=amount, per=per), "r1")
    assert reading.strength is not None


@pytest.mark.parametrize(("text", "amount", "per"), [
    ("120 mg in 5 ml sterile water", "120", "ml"),
    ("120 mg in 5 ml distilled water", "120", "ml"),
    ("Mezclar 500 mg en 5 ml agua purificada", "500", "ml"),
    ("Mélanger 500 mg dans 5 ml eau distillée", "500", "ml"),
    ("250 mg / 5 ml, 5 ml bottle", "250", "ml"),
    ("شراب 250 مجم / 2٫5 مل", "250", "ml"),
])
def test_round4_composition_water_or_per_5ml_drops(text, amount, per):
    reading = parse_label_json(_label(text, amount=amount, per=per), "r1")
    assert reading.strength is None


# --- round 5: a strength beside a dose volume needs a print in its own unit ---


@pytest.mark.parametrize(("text", "amount", "per"), [
    # rewritten round 3-4 keeps: the tablet word comes before the amount
    ("Tablets 500 mg, bottle 100 ml", "500", "tablet"),
    # rewritten: water never exempts a reading per ml
    ("Syrup 250 mg in 5 ml of water", "250", "ml"),
    ("Syrup 250 mg in 5 ml agua", "250", "ml"),
    ("Syrup 250 mg in 5 ml eau", "250", "ml"),
    ("شراب 250 مجم في 5 مل ماء", "250", "ml"),
    ("Syrup 250 mg in 5 ml of agua", "250", "ml"),
    ("Syrup 250 mg in 5 ml of syrup with water", "250", "ml"),
    # rewritten: the amount is later in the volume's sentence
    ("5 ml syrup\n500 mg capsules", "500", "capsule"),
])
def test_round5_rewritten_drops(text, amount, per):
    reading = parse_label_json(_label(text, amount=amount, per=per), "r1")
    assert reading.strength is None
    assert reading.label_text == text


def test_round5_capsule_print_right_after_the_amount_is_kept():
    # Round 9: kept again (a tablet or capsule word in the before-form gap means
    # the volume is for dissolving).
    reading = parse_label_json(
        _label("500 mg capsules in 5 ml syrup", amount="500", per="capsule"), "r1")
    assert reading.strength is not None
    assert reading.label_text == "500 mg capsules in 5 ml syrup"


@pytest.mark.parametrize(("text", "amount", "per"), [
    ("Each teaspoonful contains 125 mg", "125", "ml"),
    ("125 mg per tablespoon", "125", "dose"),
    ("125 mg per tsp", "125", "ml"),
    ("Cada cucharada contiene 125 mg", "125", "ml"),
    ("Chaque cuillère contient 125 mg", "125", "tablet"),
    ("125 mg per measure", "125", "ml"),
    ("Take one measure daily, Concor 5 mg", "5", "tablet"),
])
def test_round5_spoons_count_as_volumes(text, amount, per):
    reading = parse_label_json(_label(text, amount=amount, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text", [
    "Measure the dose: Concor 5 mg tablets",
    "Use the measuring cup. Concor 5 mg tablets",
])
def test_round5_measure_without_its_lead_in_is_not_a_spoon(text):
    reading = parse_label_json(_label(text, amount="5", per="tablet"), "r1")
    assert reading.strength is not None


@pytest.mark.parametrize("text", [
    # the same amount printed over a volume refuses the per-1-ml print ...
    "250 mg in 5 ml syrup. 250 mg/ml drops",
    "250 mg per 5 ml syrup. 250 mg/ml drops",
    # ... and so does the amount later in the volume's sentence ...
    "5 ml syrup has 250 mg. 250 mg/ml drops",
    "250 mg/ml drops\nPer 5 ml\n250 mg syrup",
    # ... but not one past a sentence end
    "250 mg/ml drops. 15 ml bottle",
])
def test_round5_refusal_both_ways(text):
    reading = parse_label_json(_label(text, amount="250"), "r1")
    assert (reading.strength is None) is ("15 ml bottle" not in text)


@pytest.mark.parametrize("text", [
    "Dissolve 500 mg tablets in 200 ml of cold water",
    "Dissolve 500 mg in 200 ml of tap water",
    "Disolver 500 mg en 200 ml de agua",
    "Dissoudre 500 mg dans 200 ml d'eau",
    "يذاب 500 مجم في 200 مل من الماء",
    "Dissolve 500 mg in 200 ml (one glass) of water",
    "Dissolve 500 mg in a glass of water (200 ml)",
])
def test_round5_water_to_dissolve_in_keeps_a_tablet_reading(text):
    reading = parse_label_json(_label(text, amount="500", per="tablet"), "r1")
    assert reading.strength is not None


@pytest.mark.parametrize("text", [
    "Dissolve 500 mg in 200 ml purified water",
    "Dissolve 500 mg in 200 ml water-based syrup",
    "Dissolve 500 mg in 200 ml water for injection",
    "Mezclar 500 mg en 200 ml agua destilada",
    "يذاب 500 مجم في 200 مل ماء مقطر",
    "500 mg per 200 ml of water",
])
def test_round5_composition_water_or_per_still_drops(text):
    reading = parse_label_json(_label(text, amount="500", per="tablet"), "r1")
    assert reading.strength is None


def test_round5_tablet_print_may_not_cross_a_line_break():
    reading = parse_label_json(
        _label("Panadol 500 mg\ntablets, 100 ml bottle", amount="500", per="tablet"), "r1")
    assert reading.strength is None


@pytest.mark.parametrize(("text", "amount", "unit", "per", "kept"), [
    ("Inhaler 100 mcg per dose, 10 ml canister", "100", "mcg", "dose", True),
    ("Spray 50 mcg/dose, 18 ml bottle", "50", "mcg", "dose", True),
    ("100 mcg per metered dose, 10 ml", "100", "mcg", "dose", True),
    ("Syrup 250 mg/ml, 5 ml bottle", "250", "mg", "dose", True),
    ("Insulin 100 UI/ml, 3 ml pen", "100", "iu", "ml", True),
    ("200 unités/ml, 5 ml", "200", "iu", "ml", True),
    ("100 وحدة دولية/مل, 5 مل", "100", "iu", "ml", True),
    ("Panadol 500 مجم 24 قرصاً, 100 مل", "500", "mg", "tablet", True),
    ("5 ml شراب؛ 500 مجم أقراص", "500", "mg", "tablet", True),
    ("5 mg film coated scored tablets, 10 ml", "5", "mg", "tablet", True),
    ("5 mg film coated scored white tablets, 10 ml", "5", "mg", "tablet", False),
])
def test_round5_own_unit_prints(text, amount, unit, per, kept):
    reading = parse_label_json(_label(text, amount=amount, unit=unit, per=per), "r1")
    assert (reading.strength is not None) is kept


# --- round 6: close the gaps in the own-unit rule ---


@pytest.mark.parametrize(("text", "amount", "per"), [
    # 1a: an abbreviation's dot stays in the sentence, so the amount still refuses
    ("Each 5 ml contains e.g. 250 mg. 250 mg/ml drops", "250", "ml"),
    ("Each 5 ml contains vit. 250 mg. 250 mg/ml drops", "250", "ml"),
    # a dot before lowercase or a digit doesn't end it either
    ("Each 5 ml contains 250 mg. also as 250 mg/ml drops", "250", "ml"),
    # but ; ! ? and a dot before a capital still end it
    ("Each 5 ml contains 250 mg! 250 mg tablets", "250", "tablet"),
    ("Each 5 ml contains 250 mg? 250 mg tablets", "250", "tablet"),
])
def test_round6_sentence_ends(text, amount, per):
    reading = parse_label_json(_label(text, amount=amount, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize(("text", "amount", "per"), [
    # 1b: up to three words between the amount and the connector ...
    ("Amoxicillin 250 mg sodium salt/5 ml. 250 mg/ml drops", "250", "ml"),
    ("Syrup 1 g powder per 5 ml. 1 g/ml drops", "1", "ml"),
    # ... an each-word after it ...
    ("Syrup 250 mg per every 5 ml. 250 mg/ml drops", "250", "ml"),
    ("Sirop 250 mg par chaque 5 ml. 250 mg/ml", "250", "ml"),
    # ... and every number before the volume counts, not only the nearest
    ("250 mg, 100 mg/5 ml. 250 mg/ml drops", "250", "ml"),
])
def test_round6_before_form(text, amount, per):
    reading = parse_label_json(_label(text, amount=amount, per=per), "r1")
    assert reading.strength is None
    assert reading.label_text == text


@pytest.mark.parametrize(("text", "amount", "unit", "per", "kept"), [
    # 1c: the reading's own per-ml or per-dose print later in the sentence is excused ...
    ("10 ml vial, 50 mg/ml", "50", "mg", "ml", True),
    ("5 ml bottle, 25 mg/ml drops", "25", "mg", "ml", True),
    ("10 ml canister, 100 mcg per dose", "100", "mcg", "dose", True),
    # ... but a tablet or capsule print never is
    ("5 ml bottle, 500 mg capsules", "500", "mg", "capsule", False),
    ("Each 5 ml contains 250 mg. 250 mg tablets", "250", "mg", "tablet", False),
])
def test_round6_own_print_excused_only_for_ml_and_dose(text, amount, unit, per, kept):
    reading = parse_label_json(_label(text, amount=amount, unit=unit, per=per), "r1")
    assert (reading.strength is not None) is kept


@pytest.mark.parametrize(("text", "amount", "per"), [
    # 2: a per-volume strength on the pack nulls a tablet/capsule/dose reading outright
    ("Ibuprofen 100 mg/5 ml. Take 200 mg per dose", "200", "dose"),
    ("Syrup 100 mg/5 ml. 400 mg tablets", "400", "tablet"),
    ("Syrup 100 mg per 5 ml. 400 mg capsules", "400", "capsule"),
])
def test_round6_per_volume_strength_nulls_tablet_capsule_dose(text, amount, per):
    reading = parse_label_json(_label(text, amount=amount, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize(("text", "amount", "per", "kept"), [
    # 3: a comma between the amount and the tablet word blocks the print ...
    ("Paracetamol 250 mg, tablets. Dose: 5 ml", "250", "tablet", False),
    ("باراسيتامول ٢٥٠ مجم، أقراص. الجرعة ٥ مل", "250", "tablet", False),
    # ... without it the print holds beside a pack volume
    ("Paracetamol 250 mg tablets. Dose: 5 ml", "250", "tablet", True),
])
def test_round6_tablet_print_comma_blocks(text, amount, per, kept):
    reading = parse_label_json(_label(text, amount=amount, per=per), "r1")
    assert (reading.strength is not None) is kept


@pytest.mark.parametrize(("text", "amount", "per", "kept"), [
    # 4a: a bracket closing after the volume may come before the water lead-in
    ("Dissolve in a cup (150 ml) of water. 500 mg tablets", "500", "tablet", True),
    # 4b: brackets after a water word hold only a lone volume, optionally after approx
    ("Dissolve 500 mg in water (about 200 ml)", "500", "tablet", True),
    ("Dissolve 500 mg in water (ca. 200 ml)", "500", "tablet", True),
    ("Dissolve 500 mg in water (5 ml and 250 mg)", "500", "tablet", False),
    ("Dissolve 500 mg in water (the 200 ml glass)", "500", "tablet", False),
    # 4c: a dash with spaces isn't water-based ...
    ("Dissolve 500 mg in 200 ml water - shake well", "500", "tablet", True),
    # ... a joined hyphen still is
    ("Dissolve 500 mg in 200 ml water-based syrup", "500", "tablet", False),
])
def test_round6_water(text, amount, per, kept):
    reading = parse_label_json(_label(text, amount=amount, per=per), "r1")
    assert (reading.strength is not None) is kept


@pytest.mark.parametrize(("text", "amount", "unit", "per", "kept"), [
    # 5: new volume spellings and unit word forms
    ("Each 5 mililitro contains 250 mg", "250", "mg", "ml", False),
    ("Syrup 250 mg/5 cm3", "250", "mg", "ml", False),
    ("Syrup 250 mg per 5 cm³", "250", "mg", "ml", False),
    ("Syrup 250 milligram per 5 ml", "250", "mg", "ml", False),
    ("Syrup 250 miligramos per 5 ml", "250", "mg", "ml", False),
    ("Syrup 250 milligrammes per 5 ml", "250", "mg", "ml", False),
    ("50 milligrams/ml, 5 ml bottle", "50", "mg", "ml", True),
    # مل starts ملجم/ملغ/ملعقة nowhere counts, in a volume or a per-1-ml print ...
    ("250 مجم لكل ملعقة, 5 مل", "250", "mg", "ml", False),
    # ... while ملي still does
    ("250 مجم/ملي, 5 مل", "250", "mg", "ml", True),
    ("Syrup 250 mg/5 ملي", "250", "mg", "ml", False),
])
def test_round6_volumes_and_units(text, amount, unit, per, kept):
    reading = parse_label_json(_label(text, amount=amount, unit=unit, per=per), "r1")
    assert (reading.strength is not None) is kept


# --- round 7: tighten the SPEC's loose wording ---


@pytest.mark.parametrize("text", [
    # 1: a dot after 1-3 Latin letters never ends the sentence
    "Each 5 ml contains Ph. Paracetamol 250 mg. Also 250 mg/ml drops",
    "Each 5 ml contains Eur. Paracetamol 250 mg. Also 250 mg/ml drops",
    "Each 5 ml contains B. Paracetamol 250 mg. Also 250 mg/ml drops",
    "Each 5 ml contains P. Paracetamol 250 mg. Also 250 mg/ml drops",
    "Each 5 ml contains Paracetamol Ph. Eur. 250 mg. Also 250 mg/ml drops",
    "Each 5 ml contains 100 mg. Paracetamol 250 mg. Also 250 mg/ml drops",
    # ... and a line break after the dot doesn't end it either
    "Each 5 ml of suspension.\nParacetamol 250 mg. 250 mg/ml drops",
])
def test_round7_abbrev_dot_stays_in_the_sentence(text):
    reading = parse_label_json(_label(text, amount="250", per="ml"), "r1")
    assert reading.strength is None


def test_round7_long_word_dot_still_ends_the_sentence():
    reading = parse_label_json(
        _label("Each 5 ml contains Syrup. Paracetamol 250 mg. Also 250 mg/ml drops",
               amount="250", per="ml"),
        "r1",
    )
    assert reading.strength is not None


@pytest.mark.parametrize(("text", "amount"), [
    # 2a: the before-form skips bracketed text
    ("Paracetamol 250 mg (sodium salt) per 5 ml. 250 mg/ml drops", "250"),
    ("Paracetamol 250 mg (as amoxicillin trihydrate)/5 ml. 250 mg/ml drops", "250"),
    ("Paracetamol 250 mg [as trihydrate] in each 5 ml. 250 mg/ml drops", "250"),
    ("Syrup 125 mg (as trihydrate) per 5 ml. 125 mg/ml drops", "125"),
])
def test_round7_brackets_dont_count_in_the_before_form(text, amount):
    reading = parse_label_json(_label(text, amount=amount, per="ml"), "r1")
    assert reading.strength is None


@pytest.mark.parametrize(("text", "amount", "per"), [
    # 2b: the always-counts form allows bracketed text before the connector
    ("Syrup 125 mg (as trihydrate) per 5 ml. Take 200 mg per dose", "200", "dose"),
    ("Syrup 100 mg (as base) per 5 ml. 400 mg tablets", "400", "tablet"),
    ("Syrup 125 mg (as trihydrate) per 5 ml. 250 mg capsules", "250", "capsule"),
])
def test_round7_brackets_in_the_always_counts_form(text, amount, per):
    reading = parse_label_json(_label(text, amount=amount, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text", [
    # 3a: the spoon stem covers the dual, with or without the article
    "شراب 250 مجم لكل ملعقتين",
    "كل ملعقتين بها 250 مجم",
    "باراسيتامول 250 مجم لكل الملعقتين",
    "كل ملعقة تحتوي على 125 مجم",
])
def test_round7_arabic_spoon_dual_counts(text):
    amount = "125" if "125" in text else "250"
    reading = parse_label_json(_label(text, amount=amount, per="ml"), "r1")
    assert reading.strength is None


@pytest.mark.parametrize(("text", "amount", "unit"), [
    # 3b: spelled-out milligrams are units, and مل inside them is not a volume
    ("كونكور 5 مليجرام 30 قرص", "5", "mg"),
    ("كونكور 5 مللي جرام 30 قرص", "5", "mg"),
    ("أملور 10 ملي جرام أقراص", "10", "mg"),
    ("فيتامين سي 1 جرام أقراص، 100 مل", "1", "g"),
    ("Ventolin 100 ميكروجرام أقراص، 10 مل", "100", "mcg"),
])
def test_round7_spelled_out_milligrams_keep_a_tablet_reading(text, amount, unit):
    reading = parse_label_json(_label(text, amount=amount, unit=unit, per="tablet"), "r1")
    assert reading.strength is not None


@pytest.mark.parametrize("text", [
    # 3c: ملي alone still counts as a volume ...
    "Syrup 250 mg per 5 ملي. 250 mg/ml drops",
    "شراب 250 مجم لكل 5 ملي",
])
def test_round7_milli_alone_still_counts(text):
    reading = parse_label_json(_label(text, amount="250", per="ml"), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text", [
    # 3d: ... but مل starting a milligram or a spoon is no per-1-ml print
    "5 ml bottle. 250 mg/مللي جرام",
    "5 ml bottle. 250 mg/ملي جرام",
    "5 ml bottle. 250 mg/ملعقة",
])
def test_round7_no_per_1ml_print_inside_a_unit_or_spoon(text):
    reading = parse_label_json(_label(text, amount="250", per="ml"), "r1")
    assert reading.strength is None


@pytest.mark.parametrize(("text", "amount", "unit"), [
    # 4: drops are doses
    ("Vitamin D3 1000 IU per drop, 10 ml", "1000", "iu"),
    ("Vitamina D3 1000 UI por gota, 10 ml", "1000", "iu"),
    ("Vitamine D3 1000 UI par goutte, 10 ml", "1000", "iu"),
    ("فيتامين د 1000 وحدة لكل نقطة، 10 مل", "1000", "iu"),
])
def test_round7_dose_words_keep_a_dose_reading(text, amount, unit):
    reading = parse_label_json(_label(text, amount=amount, unit=unit, per="dose"), "r1")
    assert reading.strength is not None


# --- round 8: five-word before-form and the colloquial spoon ---


@pytest.mark.parametrize(("text", "amount", "per"), [
    # 1a: four or five words between the amount and the connector still refuse ...
    ("Amoxicillin 250 mg as amoxicillin trihydrate per 5 ml. Amoxil 250 mg tablets",
     "250", "tablet"),
    ("Amoxicillin 250 mg as amoxicillin trihydrate BP per 5 ml. 250 mg tablets",
     "250", "tablet"),
    ("أموكسيسيلين ٢٥٠ مجم على هيئة أموكسيسيلين ترايهيدرات لكل ٥ مل. ٢٥٠ مجم أقراص",
     "250", "tablet"),
    # ... and an abbreviation dot inside the gap doesn't stop it
    ("Paracetamol 250 mg B.P. per 5 ml. 250 mg/ml drops", "250", "ml"),
])
def test_round8_long_before_form_drops(text, amount, per):
    reading = parse_label_json(_label(text, amount=amount, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize(("text", "amount", "unit", "per"), [
    # 1b: a sentence end among the words stops the before-form
    ("Euthyrox 50 µg tablets; crush and suspend in 10 ml of liquid", "50", "mcg", "tablet"),
    ("Panadol 500 mg tablets! Take in 10 ml of juice", "500", "mg", "tablet"),
    ("Amoxicillin 250 mg capsules. Suspend in 10 ml", "250", "mg", "capsule"),
    ("أموكسيسيلين ٢٥٠ مجم كبسولات؛ يعلق في ١٠ مل", "250", "mg", "capsule"),
])
def test_round8_sentence_end_stops_the_before_form(text, amount, unit, per):
    reading = parse_label_json(_label(text, amount=amount, unit=unit, per=per), "r1")
    assert reading.strength is not None


@pytest.mark.parametrize("text", [
    # 2a: the colloquial spoon counts, with or without the article
    "باراسيتامول ٢٥٠ مجم لكل المعلقة",
    "باراسيتامول ٢٥٠ مجم لكل المعلقه",
    "الجرعة ٢٥٠ مجم لكل معالق",
    "كل المعالق تحتوي على ٢٥٠ مجم",
])
def test_round8_colloquial_spoon_counts(text):
    reading = parse_label_json(_label(text, amount="250", per="ml"), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text", [
    # 2b: the suspension stem alone is not a spoon
    "مسحوق لتحضير معلق ٢٥٠ مجم",
    "مسحوق لتحضير المعلق ٢٥٠ مجم",
])
def test_round8_suspension_stem_is_not_a_spoon(text):
    reading = parse_label_json(_label(text, amount="250", per="ml"), "r1")
    assert reading.strength is not None


# --- round 9: a tablet word in the before-form gap, and the colloquial dual ---


@pytest.mark.parametrize(("text", "amount", "unit", "per"), [
    # 1a: a tablet or capsule word between the amount and the connector keeps
    ("Vitamin C 1000 mg tablet dissolve in 200 ml", "1000", "mg", "tablet"),
    ("500 mg dispersible tablet in 30 ml liquid", "500", "mg", "tablet"),
    ("20 mg capsules mix in 10 ml juice", "20", "mg", "capsule"),
    ("فيتامين 1000 مجم قرص يذاب في 200 مل", "1000", "mg", "tablet"),
    ("أوميبرازول 20 مجم كبسولة تذاب في 200 مل عصير", "20", "mg", "capsule"),
])
def test_round9_tablet_word_in_the_gap_keeps(text, amount, unit, per):
    reading = parse_label_json(_label(text, amount=amount, unit=unit, per=per), "r1")
    assert reading.strength is not None


@pytest.mark.parametrize(("text", "amount", "per"), [
    # 1b: a tablet word inside brackets is stripped first, so it still refuses ...
    ("250 mg (as one tablet) per 5 ml. 250 mg/ml drops", "250", "ml"),
    ("250 mg [equivalent to a tablet] per 5 ml. 250 mg/ml drops", "250", "ml"),
    # ... and a salt phrase with no tablet word still refuses
    ("250 mg base per 5 ml. 250 mg/ml drops", "250", "ml"),
    # ... as does the same dissolving line read per ml (no own-unit print)
    ("1000 mg effervescent tablet dissolve in 200 ml", "1000", "ml"),
])
def test_round9_bracketed_tablet_word_or_salt_still_drops(text, amount, per):
    reading = parse_label_json(_label(text, amount=amount, per=per), "r1")
    assert reading.strength is None


@pytest.mark.parametrize("text", [
    # 2: the colloquial dual counts, with or without the article
    "باراسيتامول ٢٥٠ مجم لكل معلقتين",
    "باراسيتامول ٢٥٠ مجم لكل معلقتان",
    "باراسيتامول ٢٥٠ مجم لكل المعلقتين",
    "باراسيتامول ٢٥٠ مجم لكل المعلقتان",
    "كل معلقتان تحتوي على ٢٥٠ مجم",
    "كل المعلقتين تحتوي على ٢٥٠ مجم",
])
def test_round9_colloquial_dual_counts_as_a_spoon(text):
    reading = parse_label_json(_label(text, amount="250", per="ml"), "r1")
    assert reading.strength is None
