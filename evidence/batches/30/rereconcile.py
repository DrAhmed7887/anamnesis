"""Batch 30's check: every saved live report's findings, reconciled again from its own claims and readings
with whatever reconciler is on PYTHONPATH, compared with the findings it stored. $0, offline.

    PYTHONPATH=. uv run python evidence/batches/30/rereconcile.py
"""
import glob

from anamnesis.core.catalogue import load_catalogue
from anamnesis.core.reconcile import reconcile_all
from anamnesis.schema import ReconciliationReport

CAT = load_catalogue()
files = changed = skipped = 0
for path in sorted(set(glob.glob("evidence/**/report_*.json", recursive=True))):
    try:
        report = ReconciliationReport.model_validate_json(open(path, encoding="utf-8").read())
    except ValueError:  # an early report whose stored note predates today's templates
        skipped += 1
        continue
    kept = [o for o in report.observations if o.observation_id not in report.superseded]
    again = reconcile_all(list(report.claims), kept, CAT)
    before = sorted((f.type.value, f.claim_id or "", f.observation_id or "") for f in report.findings)
    after = sorted((f.type.value, f.claim_id or "", f.observation_id or "") for f in again)
    files += 1
    if before != after:
        changed += 1
        print(path.split("/")[-1], "|", before, "->", after)
print(f"{files} reports, {changed} with changed findings, {skipped} skipped (no longer validate)")
