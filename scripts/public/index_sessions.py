"""Index the cleaned Muse build sessions: batch, round, model, tokens and cost, from each session's own
billing records (the same tally and prices as scripts/muse_usage.py).

    index_sessions.py <private repo> <sessions dir> > <sessions dir>/README.md
"""

import gzip
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from muse_usage import price, tally  # noqa: E402

INTRO = (
    "Each file is a `muse export --redacted` of one Muse Code session that built a batch round, gzipped. "
    "Every event Muse recorded is kept: its messages, tool calls, file reads, edits, commands, results and "
    "billing records. Two things were removed for the public copy (`scripts/public/clean_muse_session.py`): "
    "the encrypted reasoning blobs, and the session owner's personal context (their own skill list). "
    "Paths are relative to the repository (`<repo>`). The briefs Muse worked from are in `briefs/`, its "
    "reports in "
    "`evidence/batches/<n>/builder.md`, and each round's gate in `evidence/batches/<n>/gate.json`."
)

rows, total = [], Decimal(0)
for path in Path(sys.argv[2]).glob("*.json.gz"):
    m = re.match(r"batch-([\d.]+)-muse_session(?:-r(\d+))?\.json\.gz", path.name)
    usage = tally(json.load(gzip.open(path, "rt", encoding="utf-8")))
    cost = price(usage)
    total += cost
    rows.append((tuple(int(x) for x in m.group(1).split(".")), int(m.group(2) or 1), path.name, usage, cost))
rows.sort()
print("# Muse Code's build sessions, one per batch round\n")
print(INTRO + "\n")
print("Cost is priced from each session's own billing records at the documented Muse Spark prices "
      "(`scripts/muse_usage.py`); Meta's dashboard is the final word.\n")
print("| Batch | Round | File | Model | Input tokens (cached) | Output tokens | Cost, USD |")
print("|---|---|---|---|---|---|---|")
for batch, rnd, name, u, cost in rows:
    label = ".".join(str(x) for x in batch)
    print(f"| {label} | {rnd} | [`{name}`]({name}) | {', '.join(u['models'])} | {u['input_tokens']:,} "
          f"({u['cached_tokens']:,}) | {u['output_tokens']:,} | {cost:.4f} |")
print(f"\n{len(rows)} sessions, ${total:.2f} in all.")
