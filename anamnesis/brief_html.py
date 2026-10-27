"""HTML pieces of the clinician brief page (SPEC §7)."""

import base64
import html

from anamnesis.agent.crop import crop_region
from anamnesis.core.overlap import cross_medication
from anamnesis.schema import DiscrepancyType as D
from anamnesis.schema.review import RequestKind, RequestStatus, ReviewStatus
from anamnesis.schema.templates import (
    BRIEF_TITLE,
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
    TURN_BUTTON,
    UNNAMED_PACK,
    YES,
)

_DISAGREE = frozenset({
    D.STRENGTH_MISMATCH, D.INTAKE_DIFFERS_FROM_UNIT_STRENGTH, D.INGREDIENT_MISMATCH,
    D.RATIO_MISMATCH, D.FORMULATION_MISMATCH, D.DISCONTINUED_BUT_PRESENT,
})

_STYLE = (
    "body{font-family:system-ui,sans-serif;margin:2rem auto;max-width:60rem;padding:0 1rem;color:#111}"
    "img{max-width:100%;height:auto}"
    ".sides{display:grid;grid-template-columns:1fr 1fr;gap:1rem}"
    "@media (max-width:640px){.sides{grid-template-columns:1fr}}"
    "#disagree{border-left:4px solid #d9480f;padding-left:1rem}"
    ".photo{position:relative;max-width:100%}"
    ".photo img{display:block;width:100%;height:auto}"
    ".photo svg{position:absolute;left:0;top:0;width:100%;height:100%}"
    ".photo svg rect{fill:transparent;stroke:#d9480f;stroke-width:3;vector-effect:non-scaling-stroke}"
    ".pre{white-space:pre-wrap}"
    "@media print{.sides{grid-template-columns:1fr 1fr}}"
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
    return f"{_esc(part.inn)}{salt} {_plain(part.amount)} {_esc(part.unit.value)}"


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


def _finding_html(finding, claims, observations, turns, review=None) -> str:
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
    return (
        f'<article id="finding:{_esc(finding.finding_id)}" '
        f'data-type="{finding.type.value}"><h3 dir="auto">{_heading(finding, claims, observations)}</h3>'
        f"<p>{TEMPLATES[finding.type]}</p>{extra}"
        '<div class="sides">'
        f'<div data-side="patient"><h4>{PATIENT_SIDE_HEADING}</h4>{_patient_html(claim)}</div>'
        f'<div data-side="pack"><h4>{PACK_SIDE_HEADING}</h4>{_pack_html(pack)}</div>'
        "</div>"
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


def _scope_html(review=None) -> str:
    lines = "".join(f"<p>{line}</p>" for line in SCOPE_LINES)
    lines += f'<p id="review-status">{_review_status(review)}</p>'
    return f'<header id="scope"><h1>{BRIEF_TITLE}</h1>{lines}</header>'
