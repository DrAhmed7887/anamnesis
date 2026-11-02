"""A second reading of the Spanish hero's sets, written after set 5 ran (2 Nov): `score.py` unchanged, except that
when it can't find the bisoprolol claim by "concor" in the name or by its `inn` as written, it looks the claim's
name up in the catalogue, as `plan-set5.md` said the claim would be found ("through the catalogue, as the product
now resolves it"). The registered counts stay those of `score.py`; this reading is reported beside them.

    PYTHONPATH=. uv run python evidence/diagnostics/hero-es-2026-11-01/score_catalogue_view.py \
        evidence/live/2026-11-02 U13e
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score  # noqa: E402

_find = score.find


def find(report, names, inn):
    claim = _find(report, names, inn)
    if claim is not None:
        return claim
    for candidate in report.claims:
        entry = score.CATALOGUE.resolve(candidate.name_text)
        if entry is not None and entry.inns == frozenset({inn}):
            return candidate
    return None


score.find = find

if __name__ == "__main__":
    score.main()
