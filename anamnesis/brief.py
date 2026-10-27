"""One self-contained clinician brief page per intake (SPEC §7)."""

from anamnesis.agent.loop import _intake_id, _prepare
from anamnesis.brief_html import (
    _SCRIPT,
    _STYLE,
    _across_html,
    _finding_html,
    _photos_html,
    _scope_html,
    _section_of,
    _voice_html,
)
from anamnesis.schema.report import AgentAction, ReconciliationReport
from anamnesis.schema.templates import (
    BRIEF_TITLE,
    COVERAGE_BUDGET,
    COVERAGE_DETECTION_FAILED,
    COVERAGE_NO_PACK,
    COVERAGE_NOT_EXAMINED,
    COVERAGE_NOT_OPENED,
    COVERAGE_PACKS_FOUND,
    COVERAGE_PHOTOS_RECEIVED,
    COVERAGE_VOICE_NO_EXTRACT,
    COVERAGE_VOICE_NONE,
    COVERAGE_VOICE_NOT_TRANSCRIBED,
    COVERAGE_VOICE_OK,
    NONE_TEXT,
    SECTION_HEADINGS,
    SECTION_ORDER,
)

Image = tuple[bytes, str]


def _checked_prepared(report: ReconciliationReport, images: list[Image], audio: Image | None):
    """The loop's own prepared photos, refusing media the report wasn't made from."""
    prepared = _prepare(images)
    audio_bytes = audio[0] if audio is not None else None
    want = _intake_id(audio_bytes, [photo for photo, _, _ in prepared])
    if want != report.intake_id:
        raise ValueError("media do not match the report")
    return prepared


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


def render_brief(
    report: ReconciliationReport, images: list[Image], audio: Image | None, catalogue,
) -> str:
    """Render one deterministic self-contained HTML page for a finished report."""
    prepared = _checked_prepared(report, images, audio)
    claims = {claim.claim_id: claim for claim in report.claims}
    observations = {obs.observation_id: obs for obs in report.observations}
    turns = {turn.turn_id: turn for turn in report.turns}
    sections = {name: [] for name in SECTION_ORDER}
    for finding in report.findings:
        html = _finding_html(finding, claims, observations, turns)
        sections[_section_of(finding, claims)].append(html)
    sections["across"].append(_across_html(report, catalogue))
    sections["coverage"].append(_coverage_html(report, prepared, audio))
    sections["photos"].append(_photos_html(report, prepared))
    sections["voice"].append(_voice_html(report, audio))
    parts = [
        "<!DOCTYPE html>", '<html lang="en">',
        f"<head><meta charset=\"utf-8\"><title>{BRIEF_TITLE}</title><style>{_STYLE}</style></head>",
        "<body>", _scope_html(),
    ]
    for name in SECTION_ORDER:
        body = "".join(sections[name]) or f"<p>{NONE_TEXT}</p>"
        parts.append(f'<section id="{name}"><h2>{SECTION_HEADINGS[name]}</h2>{body}</section>')
    parts.append(f"<script>{_SCRIPT}</script></body></html>")
    return "".join(parts)


def _coverage_html(report, prepared, audio) -> str:
    lines = _coverage_from_prepared(report, prepared, audio)
    return "<ul>" + "".join(f"<li>{line}</li>" for line in lines) + "</ul>"


__all__ = ["coverage_lines", "render_brief"]
