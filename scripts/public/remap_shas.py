"""Remap the commit ids cited in the tree's Markdown files and batch log to the filtered history.

    remap_shas.py <.git/filter-repo/commit-map>

A token is remapped only when exactly one old commit starts with it. Ids of commits the filter dropped are
counted and left as they are.
"""

import re
import subprocess
import sys
from collections import Counter

pairs = [line.split() for line in open(sys.argv[1]) if line.strip() and not line.startswith("old")]
old_to_new = {old: new for old, new in pairs}
olds = sorted(old_to_new)
tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.split()
files = [f for f in tracked if f.endswith(".md") or f == "evidence/batch_log.jsonl"]
TOKEN = re.compile(r"(?<![0-9a-zA-Z_-])[0-9a-f]{7,40}(?![0-9a-zA-Z_-])")
done, dropped = Counter(), Counter()


def swap(match: re.Match) -> str:
    token = match.group(0)
    hits = [o for o in olds if o.startswith(token)]
    if len(hits) != 1:
        return token
    new = old_to_new[hits[0]]
    if set(new) == {"0"}:
        dropped[token] += 1
        return token
    done[token] += 1
    return new[:len(token)]


changed = 0
for name in files:
    text = open(name, encoding="utf-8").read()
    new_text = TOKEN.sub(swap, text)
    if new_text != text:
        open(name, "w", encoding="utf-8").write(new_text)
        changed += 1
print(f"remapped {sum(done.values())} citations of {len(done)} commits in {changed} files; "
      f"{sum(dropped.values())} citations of {len(dropped)} dropped commits left as they were")
