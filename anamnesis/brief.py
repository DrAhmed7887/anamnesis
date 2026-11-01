"""One self-contained clinician brief page per intake (SPEC §7)."""

from anamnesis.agent.loop import _checked_prepared
from anamnesis.brief_html import (
    _SCRIPT,
    _STYLE,
    _across_html,
    _codes_entry,
    _finding_html,
    _photos_html,
    _scope_html,
    _section_of,
    _timeline_html,
    _voice_html,
)
from anamnesis.schema.report import AgentAction, ReconciliationReport
from anamnesis.schema.review import FollowUpOutcome, RequestKind, RequestStatus
from anamnesis.schema.templates import (
    BRIEF_TITLE,
    CATALOGUE_CODES_REFERENCE,
    COVERAGE_BUDGET,
    COVERAGE_DETECTION_FAILED,
    COVERAGE_NO_PACK,
    COVERAGE_NOT_EXAMINED,
    COVERAGE_NOT_OPENED,
    COVERAGE_PACKS_FOUND,
    COVERAGE_PHOTOS_RECEIVED,
    COVERAGE_REQUESTS,
    COVERAGE_VOICE_NO_EXTRACT,
    COVERAGE_VOICE_NONE,
    COVERAGE_VOICE_NOT_TRANSCRIBED,
    COVERAGE_VOICE_OK,
    NONE_TEXT,
    SECTION_HEADINGS,
    SECTION_ORDER,
)

Image = tuple[bytes, str]


def coverage_lines(report: ReconciliationReport, images: list[Image], audio: Image | None) -> list[str]:
    """One coverage line per photo and for the voice note (SPEC §7)."""
    return _coverage_from_prepared(report, _checked_prepared(report, images, audio), audio)


def _coverage_from_prepared(report, prepared, audio) -> list[str]:
    lines = [COVERAGE_PHOTOS_RECEIVED.format(n=len(prepared))]
    for index, (_, size, sha) in enumerate(prepared, start=1):
        lines.append(_photo_line(report, index, sha if size is not None else None))
    lines.append(_voice_line(report, audio))
    if any(step.action is AgentAction.BUDGET_EXHAUSTED for step in report.steps):
        lines.append(COVERAGE_BUDGET)
    return lines


def _photo_line(report: ReconciliationReport, index: int, sha: str | None) -> str:
    if sha is None:
        return COVERAGE_NOT_OPENED.format(i=index)
    steps = [
        step for step in report.steps
        if step.action is AgentAction.SEGMENT and step.target.startswith(sha[:12] + ":")
    ]
    if not steps:
        return COVERAGE_NOT_EXAMINED.format(i=index)
    if all(step.outcome.startswith("error:") for step in steps):
        return COVERAGE_DETECTION_FAILED.format(i=index)
    regions = [region for region in report.regions if region.image_sha256 == sha]
    if not regions:
        return COVERAGE_NO_PACK.format(i=index)
    ids = {region.region_id for region in regions}
    found = [obs for obs in report.observations if any(v in ids for v in obs.visual_evidence)]
    unread = sum(1 for obs in found if obs.readability.value in ("unreadable", "partial"))
    return COVERAGE_PACKS_FOUND.format(i=index, r=len(regions), o=len(found), u=unread)


def _voice_line(report: ReconciliationReport, audio: Image | None) -> str:
    if audio is None:
        return COVERAGE_VOICE_NONE
    if not report.turns:
        return COVERAGE_VOICE_NOT_TRANSCRIBED
    extract = [step for step in report.steps if step.action is AgentAction.EXTRACT_CLAIMS]
    if not extract or any(step.outcome.startswith("error:") for step in extract):
        return COVERAGE_VOICE_NO_EXTRACT.format(t=len(report.turns))
    return COVERAGE_VOICE_OK.format(t=len(report.turns), c=len(report.claims))


def _check_follow_up_log(review, follow_up) -> None:
    """Refuse a follow-up log that does not belong to its review (SPEC §8)."""
    if not follow_up:
        return
    if review is None:
        raise ValueError("a follow-up log needs its review")
    known = {item.request_id: item for item in review.requests}
    seen = set()
    for step in follow_up:
        item = known.get(step.request_id)
        if item is None:
            raise ValueError("a follow-up step names no request of the review")
        if step.request_id in seen:
            raise ValueError("a follow-up step repeats its request")
        seen.add(step.request_id)
        if step.target_id != item.target_id or step.kind != item.kind:
            raise ValueError("a follow-up step differs from its request")
        if step.kind is not RequestKind.NOT_PHOTOGRAPHED:
            raise ValueError("a follow-up step names another kind of request")
        if step.outcome is FollowUpOutcome.ANSWERED and item.status is not RequestStatus.ANSWERED:
            raise ValueError("an answered step names no answered request")


def render_brief(
    report: ReconciliationReport, images: list[Image], audio: Image | None, catalogue,
    review=None, follow_up=None,
) -> str:
    """Render one deterministic self-contained HTML page for a finished report."""
    if review is not None and review.intake_id != report.intake_id:
        raise ValueError("review is for another report")
    _check_follow_up_log(review, follow_up)
    prepared = _checked_prepared(report, images, audio)
    claims = {claim.claim_id: claim for claim in report.claims}
    observations = {obs.observation_id: obs for obs in report.observations}
    turns = {turn.turn_id: turn for turn in report.turns}
    sections = {name: [] for name in SECTION_ORDER}
    any_codes = False
    for finding in report.findings:
        html = _finding_html(finding, claims, observations, turns, review, catalogue)
        sections[_section_of(finding, claims)].append(html)
        if _codes_entry(finding, claims, observations, catalogue) is not None:
            any_codes = True
    sections["across"].append(_across_html(report, catalogue))
    sections["coverage"].append(_coverage_html(report, prepared, audio, review))
    sections["photos"].append(_photos_html(report, prepared))
    sections["voice"].append(_voice_html(report, audio))
    parts = [
        "<!DOCTYPE html>", '<html lang="en">',
        '<head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{BRIEF_TITLE}</title><style>{_STYLE}</style></head>",
        "<body>", _scope_html(review, follow_up),
    ]
    for name in SECTION_ORDER:
        body = "".join(sections[name]) or f"<p>{NONE_TEXT}</p>"
        parts.append(f'<section id="{name}"><h2>{SECTION_HEADINGS[name]}</h2>{body}</section>')
    if any_codes:
        parts.append(f"<p>{CATALOGUE_CODES_REFERENCE}</p>")
    parts.append(_timeline_html(report))
    parts.append(f"<script>{_SCRIPT}</script></body></html>")
    return "".join(parts)


def _coverage_html(report, prepared, audio, review=None) -> str:
    lines = _coverage_from_prepared(report, prepared, audio)
    if review is not None:
        live = [item for item in review.requests if item.status is not RequestStatus.WITHDRAWN]
        if live:
            done = sum(1 for item in live if item.status is RequestStatus.ANSWERED)
            lines.append(COVERAGE_REQUESTS.format(n=len(live), m=done))
    return "<ul>" + "".join(f"<li>{line}</li>" for line in lines) + "</ul>"


__all__ = ["coverage_lines", "render_brief"]
