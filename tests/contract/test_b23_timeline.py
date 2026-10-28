"""Batch 23 contract, part 1: the "How it got here" timeline (SPEC §4 Report, §7). Written by the CEO; Muse must not
edit it.

Each step records its call: the model, tokens, latency, and everything the step was charged, retries and failed
attempts included. So the steps add up to the report's spend_usd. The brief shows them in a collapsed block after its
sections. The labels are fixed templates and every value comes from the report: no model prose is shown here.
"""

from decimal import Decimal

import pytest

from anamnesis.agent import run_intake
from anamnesis.agent.session import IntakeSession
from anamnesis.brief import render_brief
from anamnesis.providers.base import ProviderError, ProviderTrace
from anamnesis.providers.spend import SpendCapExceeded
from anamnesis.schema.report import AgentAction, AgentStep
from anamnesis.schema.templates import TIMELINE_COLUMNS, TIMELINE_HEADING, TIMELINE_NONE, TIMELINE_TOTAL
from tests.contract import test_b19_brief as b19
from tests.contract.test_b19_brief import (
    AUDIO,
    CAT,
    CLAIMS,
    PHOTO,
    RB,
    RC,
    RN,
    RU,
    SECTIONS,
    TURNS,
    Page,
    section_ids,
)

MODELS = {"voice": "muse-voice-transcribe", "claims": "muse-spark-1.3", "sam": "sam-3.1", "read": "muse-spark-1.3"}


@pytest.fixture
def priced(monkeypatch):
    """The batch 19 fakes, each call with its own trace: a model per provider, and its own tokens, time and cost."""
    count = iter(range(1, 1000))

    def trace(kind):
        n = next(count)
        return ProviderTrace(call_id=f"{kind}-{n}", model_id=MODELS[kind], latency_ms=1000 * n + 250,
                             input_tokens=100 * n, output_tokens=10 * n, cost_usd=Decimal(n) / 1000)

    monkeypatch.setattr(b19, "trace", trace)


def run():
    report = run_intake(AUDIO[0], [(PHOTO, "image/png")], transcriber=b19.Transcriber(TURNS),
                        extractor=b19.Extractor(CLAIMS), segmenter=b19.Segmenter({RC.image_sha256: [RC, RB, RN, RU]}),
                        reader=b19.Reader(b19.reads()), catalogue=CAT, top_k=4)
    return report, render_brief(report, [(PHOTO, "image/png")], AUDIO, CAT)


def traced(cid, prior=(), prior_usd="0"):
    return ProviderTrace(call_id=cid, model_id="muse-spark-1.3", latency_ms=6473, input_tokens=1200,
                         output_tokens=300, cost_usd=Decimal("0.00811"), prior_call_ids=list(prior),
                         prior_cost_usd=Decimal(prior_usd))


def _raise(exc):
    raise exc


# --- each step records its call ------------------------------------------------------------------------------

def test_each_call_step_records_its_model_tokens_time_and_cost(priced):
    report, _ = run()
    called = [step for step in report.steps if step.call_ids]
    assert len(called) >= 5
    for step in called:
        kind, n = step.call_ids[0].rsplit("-", 1)
        n = int(n)
        assert step.model_id == MODELS[kind]
        assert (step.input_tokens, step.output_tokens, step.latency_ms) == (100 * n, 10 * n, 1000 * n + 250)
        assert step.cost_usd == Decimal(n) / 1000


def test_the_steps_add_up_to_the_report_spend(priced):
    report, _ = run()
    assert sum((step.cost_usd for step in report.steps), Decimal(0)) == report.spend_usd > 0


def test_a_step_without_a_call_costs_nothing(priced):
    report, _ = run()
    [reconcile] = [step for step in report.steps if step.action is AgentAction.RECONCILE]
    assert (reconcile.model_id, reconcile.input_tokens, reconcile.output_tokens, reconcile.latency_ms,
            reconcile.cost_usd) == (None, 0, 0, 0, Decimal(0))


def test_a_retried_call_records_both_attempts_cost():
    session = IntakeSession(5)
    session.call(AgentAction.READ, "r0", lambda: ("ok", traced("c-2", ["c-1"], "0.00500")), describe=str)
    [step] = session.steps
    assert step.call_ids == ["c-2", "c-1"]
    assert (step.model_id, step.input_tokens, step.output_tokens, step.latency_ms) == ("muse-spark-1.3", 1200, 300,
                                                                                       6473)
    assert step.cost_usd == Decimal("0.01311") == session.spend_usd


@pytest.mark.parametrize("attempt", [None, traced("c-9")], ids=["no attempt trace", "with an attempt trace"])
def test_a_failed_call_records_what_it_was_charged(attempt):
    session = IntakeSession(5)
    error = ProviderError("spark", "malformed", retryable=True, attempt_trace=attempt,
                          charged_call_ids=["c-8", "c-9"], charged_usd=Decimal("0.01622"))
    session.call(AgentAction.READ, "r0", lambda: _raise(error), describe=str)
    [step] = session.steps
    assert step.cost_usd == Decimal("0.01622") == session.spend_usd
    assert step.model_id == (None if attempt is None else "muse-spark-1.3")
    assert step.latency_ms == (0 if attempt is None else 6473)


def test_a_spend_cap_stop_records_its_charge():
    session = IntakeSession(5)
    stop = SpendCapExceeded("cap", charged_call_ids=["c-1"], charged_usd=Decimal("0.00811"))
    session.call(AgentAction.READ, "r0", lambda: _raise(stop), describe=str)
    [step] = session.steps
    assert step.action is AgentAction.BUDGET_EXHAUSTED
    assert step.cost_usd == Decimal("0.00811") == session.spend_usd


def test_a_step_from_before_batch_23_still_loads():
    step = AgentStep(n=0, action="read", target="r0", outcome="readable")
    assert (step.model_id, step.input_tokens, step.output_tokens, step.latency_ms, step.cost_usd) == (
        None, 0, 0, 0, Decimal(0))


@pytest.mark.parametrize("model", ["muse-spark-1.3-contributor", "Muse-Spark-1.3-Contributor-v2", " x-contributor "])
def test_a_step_refuses_a_contributor_model(model):
    with pytest.raises(ValueError):
        AgentStep(n=0, action="read", target="r0", outcome="ok", model_id=model)


@pytest.mark.parametrize("field", ["input_tokens", "output_tokens", "latency_ms", "cost_usd"])
def test_call_fields_are_never_negative(field):
    with pytest.raises(ValueError):
        AgentStep(n=0, action="read", target="r0", outcome="ok", **{field: -1})


# --- the brief shows them ------------------------------------------------------------------------------------

def test_the_templates_are_fixed():
    assert TIMELINE_HEADING == "How it got here"
    assert TIMELINE_COLUMNS == ("#", "Step", "Target", "Outcome", "Model", "Tokens in", "Tokens out", "Time", "Cost")
    assert TIMELINE_NONE == "—"
    assert TIMELINE_TOTAL == "Total: {calls} calls, ${usd}"


def test_the_brief_ends_with_a_collapsed_timeline(priced):
    _, html = run()
    page = Page(html).root
    assert section_ids(page) == SECTIONS
    timeline = page.by_id("timeline")
    assert timeline.tag == "details" and "open" not in timeline.attrs
    [summary] = timeline.find_all("summary")
    assert summary.text() == TIMELINE_HEADING
    assert html.index('<section id="voice"') < html.index('id="timeline"') < html.index("<script>")


def test_the_timeline_has_one_row_per_step_in_order(priced):
    report, html = run()
    timeline = Page(html).root.by_id("timeline")
    [head] = timeline.find_all("thead")
    assert [cell.text() for cell in head.find_all("th")] == list(TIMELINE_COLUMNS)
    [body] = timeline.find_all("tbody")
    rows = body.find_all("tr")
    assert len(rows) == len(report.steps)
    for row, step in zip(rows, report.steps, strict=True):
        called = step.model_id is not None
        none = TIMELINE_NONE
        assert [cell.text() for cell in row.find_all("td")] == [
            str(step.n), step.action.value, step.target, step.outcome,
            step.model_id if called else none,
            str(step.input_tokens) if called else none,
            str(step.output_tokens) if called else none,
            f"{step.latency_ms / 1000:.1f} s" if called else none,
            f"${step.cost_usd:.5f}",
        ]
    [foot] = timeline.find_all("tfoot")
    assert foot.text() == TIMELINE_TOTAL.format(calls=report.calls, usd=f"{report.spend_usd:.5f}")


def test_timeline_values_are_escaped(priced):
    report, _ = run()
    hostile = report.steps[0].model_copy(update={"target": "<script>alert(1)</script>",
                                                  "outcome": '<b onmouseover="go()">x</b>'})
    report = report.model_copy(update={"steps": [hostile, *report.steps[1:]]})
    timeline = Page(render_brief(report, [(PHOTO, "image/png")], AUDIO, CAT)).root.by_id("timeline")
    assert timeline.find_all("script") == [] and timeline.find_all("b") == []
    first = timeline.find_all("tbody")[0].find_all("tr")[0]
    assert "<script>alert(1)</script>" in first.text()


def test_an_intake_with_nothing_still_has_a_timeline():
    report = run_intake(None, [], transcriber=b19.Transcriber(), extractor=b19.Extractor(),
                        segmenter=b19.Segmenter(), reader=b19.Reader({}), catalogue=CAT)
    timeline = Page(render_brief(report, [], None, CAT)).root.by_id("timeline")
    assert len(timeline.find_all("tbody")[0].find_all("tr")) == len(report.steps)
    assert timeline.find_all("tfoot")[0].text() == "Total: 0 calls, $0.00000"
