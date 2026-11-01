"""HTML pieces of the clinician brief page (SPEC §7)."""

import base64
import html

from anamnesis.agent.crop import crop_region
from anamnesis.core.overlap import cross_medication
from anamnesis.core.reconcile import claim_identity_conflict, pack_identity_conflict
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.review import FollowUpOutcome, RequestKind, RequestStatus, ReviewStatus
from anamnesis.schema.templates import (
    BRIEF_TITLE,
    CATALOGUE_CODES_ATC,
    CATALOGUE_CODES_LINE,
    CATALOGUE_CODES_RX_SEPARATOR,
    CATALOGUE_CODES_RXNORM,
    CATALOGUE_CODES_SEPARATOR,
    FIELD_COUNTRY,
    FIELD_INN,
    FIELD_INTAKE,
    FIELD_LABEL,
    FIELD_NAME,
    FIELD_READABILITY,
    FIELD_REGIMEN,
    FIELD_STATUS,
    FIELD_STRENGTH,
    FOLLOW_UP_DONE,
    HEARD_IN,
    HEARD_TURN,
    MENTIONED_NOT_PHOTOGRAPHED,
    NO,
    NONE_TEXT,
    NOT_MENTIONED,
    NOT_PHOTOGRAPHED,
    NOT_READ,
    PACK_SIDE_HEADING,
    PATIENT_QUESTIONS,
    PATIENT_SIDE_HEADING,
    PHOTO_ALT,
    PHOTOGRAPHED_NOT_MENTIONED,
    QUESTION_FOR,
    REGIMEN_AS_NEEDED,
    REGIMEN_INTAKES_PER_DAY,
    REGIMEN_UNITS_PER_INTAKE,
    REGION_ALT,
    REGION_CAPTION,
    REPORTED_STOPPED_NOT_PHOTOGRAPHED,
    REVIEW_APPROVED,
    REVIEW_DRAFT,
    REVIEW_REPLACED,
    REVIEW_REQUESTED,
    REVIEW_WAITING,
    SCOPE_LINES,
    SEEN_IN,
    SEEN_REGION,
    STRENGTH_PER,
    TEMPLATES,
    TIMELINE_COLUMNS,
    TIMELINE_HEADING,
    TIMELINE_NONE,
    TIMELINE_TOTAL,
    TURN_BUTTON,
    UNNAMED_PACK,
    YES,
)

_DISAGREE = frozenset({
    D.STRENGTH_MISMATCH, D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH, D.INGREDIENT_MISMATCH,
    D.RATIO_MISMATCH, D.FORMULATION_MISMATCH, D.DISCONTINUED_BUT_PRESENT,
})

_STYLE = (
    "body{font-family:system-ui,sans-serif;font-size:16px;line-height:1.5;color:#111;background:#fff}"
    "body{margin:2rem auto;max-width:60rem;padding:0 1rem;overflow-wrap:anywhere}"
    "*{box-sizing:border-box}"
    "h1{font-size:1.75rem;line-height:1.2;margin:0 0 1rem}"
    "h2{font-size:1.375rem;line-height:1.25;margin:0 0 1rem}"
    "h3{font-size:1.125rem;line-height:1.3;margin:0 0 .5rem}"
    "h4{font-size:14px;font-weight:600;color:#595959;margin:0 0 .5rem}"
    "p{margin:0 0 .75rem}"
    "section{margin:0 0 2rem}"
    "section>h2{border-bottom:1px solid #767676;padding-bottom:.5rem;break-after:avoid}"
    "article{border:1px solid #767676;border-radius:8px;background:#fff}"
    "article{padding:1rem 1.25rem;margin:0 0 1rem;break-inside:avoid}"
    "#disagree article{border-inline-start:4px solid #d9480f}"
    ".sides{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin:0 0 1rem}"
    "div[data-side=pack]{border-inline-start:1px solid #767676;padding-inline-start:1rem}"
    "@media screen and (max-width:640px){.sides{grid-template-columns:1fr}"
    "div[data-side=pack]{border-inline-start:none;border-block-start:1px solid #767676}"
    "div[data-side=pack]{padding-inline-start:0;padding-block-start:1rem}}"
    "dl{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:.25rem .75rem;margin:0}"
    "dt{font-weight:600}"
    "dd{margin:0}"
    "bdi,#voice button,#timeline{font-variant-numeric:tabular-nums}"
    "#scope{margin:0 0 2rem}"
    "#scope p{color:#595959;margin:.25rem 0}"
    "#review-status{display:inline-block;border:1px solid #767676;border-radius:999px;background:#f1f1f1}"
    "#review-status{padding:.2rem .75rem;font-size:14px}"
    "a{color:#0b5cad;text-decoration:underline}"
    "article>p:last-child a{display:inline-block;border:1px solid #0b5cad;border-radius:999px}"
    "article>p:last-child a{padding:.1rem .5rem;font-size:14px}"
    "article>p:last-child a{text-decoration:none;margin:0 .25rem .25rem 0}"
    "#voice ul{list-style:none;padding:0;margin:0}"
    "#voice li{cursor:pointer;padding:.5rem;border-radius:6px}"
    "#voice li:hover{background:#f5f5f5}"
    "#voice button{font:inherit;font-size:14px;color:#595959}"
    "#voice button{background:#fff;border:1px solid #767676;border-radius:6px}"
    "#voice button{padding:.15rem .5rem;cursor:pointer}"
    "audio{max-width:100%}"
    "#timeline{overflow-x:auto;border:1px solid #767676;border-radius:8px;padding:1rem;background:#fff}"
    "#timeline table{border-collapse:collapse;width:100%}"
    "#timeline th,#timeline td{border:1px solid #767676;padding:.25rem .5rem;text-align:left}"
    "#timeline thead th{background:#f1f1f1}"
    "#timeline tbody tr:nth-child(even){background:#f8f8f8}"
    "#timeline tfoot td{font-weight:bold}"
    "#timeline td:nth-child(1),#timeline td:nth-child(6),#timeline td:nth-child(7),"
    "#timeline td:nth-child(8),#timeline td:nth-child(9){text-align:right;white-space:nowrap}"
    "@media screen{#timeline table{overflow-wrap:normal}}"
    "figure{margin:0 0 1rem}"
    "figure[id^=\"region:\"]{display:inline-block;vertical-align:top;margin:0 1rem 1rem 0}"
    "figcaption{color:#595959;font-size:14px}"
    "body>p{color:#595959;font-size:14px}"
    "summary{cursor:pointer;font-weight:600}"
    "img{max-width:100%;height:auto}"
    ".photo{position:relative;max-width:100%}"
    ".photo img{display:block;width:100%;height:auto}"
    ".photo svg{position:absolute;left:0;top:0;width:100%;height:100%}"
    ".photo svg rect{fill:transparent;stroke:#d9480f;stroke-width:3;vector-effect:non-scaling-stroke}"
    ".pre{white-space:pre-wrap}"
    "@media print{body{background:#fff;color:#111;margin:0;max-width:none}"
    ".sides{grid-template-columns:1fr 1fr}"
    "article{break-inside:avoid}}"
)

_SCRIPT = (
    "document.addEventListener(\"DOMContentLoaded\",function(){"
    "var audio=document.querySelector(\"audio\");"
    "if(!audio){return;}"
    "var end=null;"
    "audio.addEventListener(\"timeupdate\",function(){"
    "if(end!==null&&audio.currentTime>=end){audio.pause();end=null;}});"
    "function playTurn(item){"
    "end=Number(item.getAttribute(\"data-end-ms\"))/1000;"
    "audio.currentTime=Number(item.getAttribute(\"data-start-ms\"))/1000;"
    "audio.play();}"
    "document.querySelectorAll('li[id^=\"turn:\"]').forEach(function(item){"
    "item.addEventListener(\"click\",function(){playTurn(item);});});"
    "document.querySelectorAll('a[href^=\"#turn:\"]').forEach(function(link){"
    "link.addEventListener(\"click\",function(){"
    "var target=document.getElementById(link.getAttribute(\"href\").slice(1));"
    "if(target){playTurn(target);}});});});"
)


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _plain(value) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _clock(ms: int) -> str:
    return f"{ms // 60000}:{ms % 60000 // 1000:02d}"


def _first_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _ingredient_html(part) -> str:
    salt = f" {_esc(part.salt)}" if part.salt else ""
    dose = f"{_plain(part.amount)} {_esc(part.unit.value)}"
    return f'{_esc(part.inn)}{salt} <bdi dir="ltr">{dose}</bdi>'


def _strength_html(strength) -> str:
    parts = [_ingredient_html(p) for p in strength.ingredients]
    text = ", ".join(parts) + STRENGTH_PER + _esc(strength.per.value)
    if strength.release.value != "unknown":
        text += f" ({_esc(strength.release.value)})"
    return text


def _regimen_html(regimen) -> str | None:
    if regimen is None:
        return None
    parts = []
    if regimen.units_per_intake is not None:
        parts.append(f"{REGIMEN_UNITS_PER_INTAKE}: {_plain(regimen.units_per_intake)}")
    if regimen.intakes_per_day is not None:
        parts.append(f"{REGIMEN_INTAKES_PER_DAY}: {_plain(regimen.intakes_per_day)}")
    if regimen.as_needed is not None:
        parts.append(f"{REGIMEN_AS_NEEDED}: {YES if regimen.as_needed else NO}")
    return ", ".join(parts) if parts else None


def _field(label: str, value: str, auto: bool = False) -> str:
    if auto:
        return f"<dt>{label}</dt><dd dir=\"auto\">{value}</dd>"
    return f"<dt>{label}</dt><dd>{value}</dd>"


def _section_of(finding, claims) -> str:
    if finding.type is D.MATCH:
        return "agree"
    if finding.type in _DISAGREE:
        return "disagree"
    if finding.type is D.MISSING_MODALITY and finding.claim_id is not None:
        claim = claims.get(finding.claim_id)
        if claim is not None and claim.status.value == "discontinued":
            return "stopped"
    return "unconfirmed"


def _heading(finding, claims, observations) -> str:
    if finding.claim_id is not None:
        first = _first_line(claims[finding.claim_id].name_text)
        if first is not None:
            return _esc(first)
    if finding.observation_id is not None:
        label = observations[finding.observation_id].label_text
        if label:
            first = _first_line(label)
            if first is not None:
                return _esc(first)
    return UNNAMED_PACK


def _request_html(finding, review) -> str:
    if review is None:
        return ""
    lines = []
    for item in review.requests:
        if item.status is not RequestStatus.OPEN:
            continue
        if item.kind is RequestKind.UNREADABLE and finding.observation_id == item.target_id:
            lines.append(item.request_id)
        elif (
            item.kind is RequestKind.NOT_PHOTOGRAPHED
            and finding.claim_id == item.target_id
            and finding.observation_id is None
        ):
            lines.append(item.request_id)
    return "".join(f'<p data-request="{_esc(rid)}">{REVIEW_REQUESTED}</p>' for rid in lines)


def _codes_entry(finding, claims, observations, catalogue):
    if catalogue is None:
        return None
    if finding.claim_id is not None:
        claim = claims.get(finding.claim_id)
        if claim is None:
            return None
        if claim_identity_conflict(claim, catalogue):
            return None
        entry = catalogue.resolve(claim.name_text)
    else:
        pack = observations.get(finding.observation_id) if finding.observation_id else None
        if pack is None or not pack.label_text:
            return None
        if pack_identity_conflict(pack, catalogue):
            return None
        entry = catalogue.resolve(pack.label_text)
    if entry is None:
        return None
    if entry.atc is None and not entry.rxcui:
        return None
    return entry


def _codes_html(entry) -> str:
    parts = []
    if entry.atc is not None:
        parts.append(CATALOGUE_CODES_ATC.format(code=_esc(entry.atc)))
    if entry.rxcui:
        joined = CATALOGUE_CODES_RX_SEPARATOR.join(_esc(code) for code in entry.rxcui)
        parts.append(CATALOGUE_CODES_RXNORM.format(codes=joined))
    return f"<p>{CATALOGUE_CODES_LINE.format(codes=CATALOGUE_CODES_SEPARATOR.join(parts))}</p>"


def _finding_html(finding, claims, observations, turns, review=None, catalogue=None) -> str:
    claim = claims.get(finding.claim_id) if finding.claim_id else None
    pack = observations.get(finding.observation_id) if finding.observation_id else None
    question = QUESTION_FOR[finding.type]
    extra = f"<p>{PATIENT_QUESTIONS[question]}</p>" if question else ""
    extra += _a3_html(finding, claim, pack)
    extra += _request_html(finding, review)
    heard = []
    for tid in finding.audio_evidence:
        turn = turns.get(tid)
        if turn is None:
            label = _esc(tid)
        else:
            label = HEARD_TURN.format(
                turn_id=_esc(tid), start=_clock(turn.start_ms), end=_clock(turn.end_ms),
            )
        heard.append(f'<a href="#turn:{_esc(tid)}">{label}</a>')
    seen = [
        f'<a href="#region:{_esc(rid)}">{SEEN_REGION.format(region_id=_esc(rid))}</a>'
        for rid in finding.visual_evidence
    ]
    parts = []
    if heard:
        parts.append(f"{HEARD_IN}: {', '.join(heard)}")
    if seen:
        parts.append(f"{SEEN_IN}: {', '.join(seen)}")
    entry = _codes_entry(finding, claims, observations, catalogue)
    codes = _codes_html(entry) if entry is not None else ""
    return (
        f'<article id="finding:{_esc(finding.finding_id)}" '
        f'data-type="{finding.type.value}"><h3 dir="auto">{_heading(finding, claims, observations)}</h3>'
        f"<p>{TEMPLATES[finding.type]}</p>{extra}"
        '<div class="sides">'
        f'<div data-side="patient"><h4>{PATIENT_SIDE_HEADING}</h4>{_patient_html(claim)}</div>'
        f'<div data-side="pack"><h4>{PACK_SIDE_HEADING}</h4>{_pack_html(pack)}</div>'
        "</div>"
        f"{codes}"
        f"<p>{'; '.join(parts)}</p></article>"
    )


def _a3_html(finding, claim, pack) -> str:
    if finding.type is not D.MISSING_MODALITY:
        return ""
    if claim is not None and pack is None:
        if claim.status.value == "discontinued":
            return f"<p>{REPORTED_STOPPED_NOT_PHOTOGRAPHED}</p>"
        return f"<p>{MENTIONED_NOT_PHOTOGRAPHED}</p>"
    if claim is None and pack is not None:
        return f"<p>{PHOTOGRAPHED_NOT_MENTIONED}</p>"
    return ""


def _patient_html(claim) -> str:
    if claim is None:
        return f"<p>{NOT_MENTIONED}</p>"
    fields = _field(FIELD_NAME, _esc(claim.name_text), auto=True)
    if claim.inn is not None:
        fields += _field(FIELD_INN, _esc(claim.inn), auto=True)
    if claim.strength is not None:
        fields += _field(FIELD_STRENGTH, _strength_html(claim.strength), auto=True)
    if claim.intake_amount is not None:
        fields += _field(FIELD_INTAKE, _ingredient_html(claim.intake_amount), auto=True)
    regimen = _regimen_html(claim.regimen)
    if regimen is not None:
        fields += _field(FIELD_REGIMEN, regimen)
    fields += _field(FIELD_STATUS, _esc(claim.status.value))
    return f"<dl>{fields}</dl>"


def _pack_html(pack) -> str:
    if pack is None:
        return f"<p>{NOT_PHOTOGRAPHED}</p>"
    fields = ""
    if pack.label_text:
        fields += _field(FIELD_LABEL, f'<span class="pre">{_esc(pack.label_text)}</span>', auto=True)
    if pack.inn is not None:
        fields += _field(FIELD_INN, _esc(pack.inn), auto=True)
    if pack.strength is not None:
        fields += _field(FIELD_STRENGTH, _strength_html(pack.strength), auto=True)
    fields += _field(FIELD_READABILITY, _esc(pack.readability.value))
    if pack.country:
        fields += _field(FIELD_COUNTRY, _esc(pack.country))
    return f"<dl>{fields}</dl>"


def _across_html(report, catalogue) -> str:
    parts = []
    claims = {claim.claim_id: claim for claim in report.claims}
    for overlap in cross_medication(report.claims, catalogue):
        items = []
        for cid in overlap.claim_ids:
            claim = claims[cid]
            links = ", ".join(
                f'<a href="#turn:{_esc(t)}" dir="auto">{_esc(claim.name_text)}</a>'
                for t in claim.audio_evidence
            )
            items.append(f"<li>{links}</li>")
        parts.append(
            f'<article data-kind="{overlap.kind.value}" '
            f'id="overlap:{overlap.kind.value}:{_esc(overlap.key)}">'
            f"<p>{overlap.note}</p><p>{_esc(overlap.key)}</p>"
            f"<ul>{''.join(items)}</ul></article>"
        )
    return "".join(parts)


def _photos_html(report, prepared) -> str:
    parts = []
    for index, (photo, size, sha) in enumerate(prepared, start=1):
        if size is None:
            continue
        data, mime = photo
        rects = "".join(
            f'<a href="#region:{_esc(region.region_id)}">'
            f'<rect x="{region.x1}" y="{region.y1}" '
            f'width="{region.x2 - region.x1 + 1}" height="{region.y2 - region.y1 + 1}"/></a>'
            for region in report.regions if region.image_sha256 == sha
        )
        parts.append(
            f'<figure id="photo:{index}"><div class="photo">'
            f'<img src="data:{_esc(mime)};base64,{_b64(data)}" alt="{PHOTO_ALT.format(i=index)}">'
            f'<svg viewBox="0 0 {size[0]} {size[1]}">{rects}</svg>'
            "</div></figure>"
        )
    by_sha = {}
    index_by_sha = {}
    for index, (photo, size, sha) in enumerate(prepared, start=1):
        if size is not None:
            by_sha.setdefault(sha, photo[0])
            index_by_sha.setdefault(sha, index)
    readability = {}
    for obs in report.observations:
        for rid in obs.visual_evidence:
            readability.setdefault(rid, obs.readability.value)
    replaced = set()
    for obs in report.observations:
        if obs.observation_id in set(getattr(report, "superseded", [])):
            replaced.update(obs.visual_evidence)
    for region in report.regions:
        source = by_sha.get(region.image_sha256)
        if source is None:
            raise ValueError(f"region {region.region_id} has no photo among the given images")
        crop = crop_region(source, region)
        caption = REGION_CAPTION.format(
            i=index_by_sha[region.image_sha256], region_id=_esc(region.region_id),
            readability=readability.get(region.region_id, NOT_READ),
        )
        extra = f"<p>{REVIEW_REPLACED}</p>" if region.region_id in replaced else ""
        parts.append(
            f'<figure id="region:{_esc(region.region_id)}">'
            f'<img src="data:image/png;base64,{_b64(crop)}" '
            f'alt="{REGION_ALT.format(region_id=_esc(region.region_id))}">'
            f"<figcaption>{caption}</figcaption>{extra}"
            "</figure>"
        )
    return "".join(parts)


def _voice_html(report, audio) -> str:
    parts = ""
    if audio is not None:
        data, mime = audio
        parts += f'<audio controls src="data:{_esc(mime)};base64,{_b64(data)}"></audio>'
    if not report.turns:
        return parts + f"<p>{NONE_TEXT}</p>"
    items = "".join(
        f'<li id="turn:{_esc(turn.turn_id)}" data-start-ms="{turn.start_ms}" '
        f'data-end-ms="{turn.end_ms}">'
        f"<button type=\"button\">{TURN_BUTTON.format(start=_clock(turn.start_ms), end=_clock(turn.end_ms))}"
        "</button> "
        f'<span dir="auto">{_esc(turn.transcript)}</span></li>'
        for turn in report.turns
    )
    return parts + f"<ul>{items}</ul>"


def _review_status(review) -> str:
    if review is None or review.status is ReviewStatus.DRAFT:
        return REVIEW_DRAFT
    if review.status is ReviewStatus.APPROVED:
        return REVIEW_APPROVED
    open_count = sum(1 for item in review.requests if item.status is RequestStatus.OPEN)
    return REVIEW_WAITING.format(n=open_count)


def _scope_html(review=None, follow_up=None) -> str:
    lines = "".join(f"<p>{line}</p>" for line in SCOPE_LINES)
    lines += f'<p id="review-status">{_review_status(review)}</p>'
    if follow_up:
        asked = len(follow_up)
        received = sum(1 for step in follow_up if step.outcome is FollowUpOutcome.ANSWERED)
        lines += f'<p id="follow-up">{FOLLOW_UP_DONE.format(asked=asked, received=received)}</p>'
    return f'<header id="scope"><h1>{BRIEF_TITLE}</h1>{lines}</header>'


def _timeline_html(report) -> str:
    head = "".join(f"<th>{_esc(column)}</th>" for column in TIMELINE_COLUMNS)
    rows = []
    for step in report.steps:
        called = step.model_id is not None
        none = _esc(TIMELINE_NONE)
        cells = [
            _esc(str(step.n)),
            _esc(step.action.value),
            _esc(step.target),
            _esc(step.outcome),
            _esc(step.model_id) if called else none,
            _esc(str(step.input_tokens)) if called else none,
            _esc(str(step.output_tokens)) if called else none,
            _esc(f"{step.latency_ms / 1000:.1f} s") if called else none,
            _esc(f"${step.cost_usd:.5f}"),
        ]
        rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    total = _esc(TIMELINE_TOTAL.format(calls=report.calls, usd=f"{report.spend_usd:.5f}"))
    span = len(TIMELINE_COLUMNS)
    return (
        f'<details id="timeline"><summary>{_esc(TIMELINE_HEADING)}</summary><table>'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody>"
        f'<tfoot><tr><td colspan="{span}">{total}</td></tr></tfoot></table></details>'
    )
