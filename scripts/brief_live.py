"""Render the clinician brief for the saved live intakes, offline: no model is called and nothing is spent.

    PYTHONPATH=. uv run python scripts/brief_live.py [--date 2026-10-27]

Reads evidence/live/<date>/report_<lang>.json and the synthetic media those intakes ran on
(evidence/raw/media), and writes evidence/raw/briefs/brief_<lang>.html, one self-contained page
each (SPEC §7). The output is git-ignored because each page embeds its voice note and photo.
Reports saved before batch 17 carry the old `match` wording, so the findings are recomputed with
today's reconciler from the saved claims and readings. render_brief still checks that the media
are the ones the intake ran on (intake_id).
"""

import argparse
import json
from pathlib import Path

from anamnesis.brief import render_brief
from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all
from anamnesis.schema import PackObservation, PatientClaim
from anamnesis.schema.report import ReconciliationReport

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "evidence/raw/media"
OUT = ROOT / "evidence/raw/briefs"


def replay(path: Path, catalogue) -> ReconciliationReport:
    """The saved report, with its findings recomputed from its own claims and readings."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    claims = [PatientClaim.model_validate(claim) for claim in raw["claims"]]
    packs = [PackObservation.model_validate(pack) for pack in raw["observations"]]
    raw["findings"] = [finding.model_dump(mode="json") for finding in reconcile_all(claims, packs, catalogue)]
    return ReconciliationReport.model_validate(raw)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-10-27")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    catalogue = load_catalogue()
    images = [((MEDIA / "packs.png").read_bytes(), "image/png")]
    for lang in ("en", "ar"):
        report = replay(ROOT / "evidence/live" / args.date / f"report_{lang}.json", catalogue)
        audio = ((MEDIA / f"voice_{lang}.wav").read_bytes(), "audio/wav")
        page = OUT / f"brief_{lang}.html"
        page.write_text(render_brief(report, images, audio, catalogue), encoding="utf-8")
        print(f"{page.relative_to(ROOT)}: {page.stat().st_size // 1024} KB, "
              f"findings {', '.join(f.type.value for f in report.findings)}")


if __name__ == "__main__":
    main()
