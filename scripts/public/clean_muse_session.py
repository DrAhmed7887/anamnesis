"""Clean one `muse export --redacted` session for the public repo, keeping everything Muse did.

    python clean_muse_session.py <rules.txt> <in.json> <out.json[.gz]>

Removes two things and rewrites text, nothing else:
- `encrypted_content`: opaque encrypted reasoning, no use to a reader;
- `run_context_messages[].text`: the session owner's own context (their skill list), not the repo's;
- every string: the rules file's literal and `regex:` lines (`old==>new`, as git filter-repo reads them).
Every tool call, file read, edit, command, message and billing record stays.
"""

import gzip
import json
import re
import sys
from pathlib import Path

ENCRYPTED = "[removed for the public copy: encrypted reasoning]"
CONTEXT = "[removed for the public copy: the session owner's personal context]"


def load_rules(path: Path) -> list[tuple[re.Pattern, str]]:
    rules = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        old, _, new = line.partition("==>")
        if old.startswith("regex:"):
            rules.append((re.compile(old[len("regex:"):]), new))
        else:
            rules.append((re.compile(re.escape(old)), new.replace("\\", "\\\\")))
    return rules


def clean(value, rules, key=None):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k == "encrypted_content" and isinstance(v, str):
                out[k] = ENCRYPTED
            elif k == "run_context_messages" and isinstance(v, list):
                out[k] = [{**m, "text": CONTEXT} if isinstance(m, dict) and "text" in m else CONTEXT
                          for m in v]
            else:
                out[k] = clean(v, rules, k)
        return out
    if isinstance(value, list):
        return [clean(v, rules, key) for v in value]
    if isinstance(value, str):
        for pattern, new in rules:
            value = pattern.sub(new, value)
        return value
    return value


def main() -> None:
    rules_path, src, dst = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    data = clean(json.loads(src.read_text(encoding="utf-8")), load_rules(rules_path))
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if dst.suffix == ".gz":
        with gzip.open(dst, "wt", encoding="utf-8", compresslevel=9) as out:
            out.write(text)
    else:
        dst.write_text(text, encoding="utf-8")
    print(f"{src.name}: {src.stat().st_size / 1e6:.1f} MB -> {dst.name}: {dst.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
