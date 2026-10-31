"""Did a headless Muse run pin its goal, close it, and do its work under it? Reads one `muse export`.

    uv run python scripts/goal_check.py evidence/raw/batch-<n>-muse_session.json

batch.sh prints this after every Muse run and keeps it as evidence/batches/<n>/goal.md. The export itself
stays in evidence/raw/ (git-ignored). Exit status 1 when no goal was pinned or the export can't be read.
It also flags every file the run read under evidence/ or the fine-tune data, which hold expected results the
builder must not see (briefs/_worker_preamble.md, 29 Oct). The flag never changes the exit status.
"""

import json
import re
import sys
from collections import Counter

_HELD_OUT = re.compile(r"(?:^|[\s\"'`(=/])((?:evidence|finetune/data\w*)/[^\s`'\"),;|]*)")
_READ_LINE = re.compile(r"Read text file `([^`]+)`")
_READ_TOOLS = ("read_file", "search", "bash")


def _events(export: dict):
    for record in export["events"]:
        payload = record.get("envelope", {}).get("payload", {})
        yield payload.get("event") or {}


def _args(call: dict) -> dict:
    raw = call.get("args", "")
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def held_out_reads(export: dict) -> list[str]:
    """Each held-out path the run read or searched, once, with the tool that touched it first.

    A read_file, search or bash call that names such a path counts, and so does the export's own
    "Read text file `...`" line. A path quoted inside a file the run edits doesn't. Flag only: a read the
    brief asked for is fine, so the CEO checks each one.
    """
    found: dict[str, str] = {}
    for event in _events(export):
        for call in event.get("tool_calls") or []:
            if call.get("name") in _READ_TOOLS:
                args = _args(call)
                text = " ".join(map(str, args.values())) if args else str(call.get("args", ""))
                for match in _HELD_OUT.finditer(text):
                    found.setdefault(match.group(1), str(call["name"]))
    for line in _READ_LINE.finditer(json.dumps(export, ensure_ascii=False)):
        for match in _HELD_OUT.finditer(" " + line.group(1)):
            found.setdefault(match.group(1), "Read text file")
    return [f"`{path}` ({how})" for path, how in found.items()]


def summarise(export: dict) -> tuple[bool, list[str]]:
    """The goal evidence as report lines, and whether a goal was pinned at all."""
    objectives, statuses, reasons = [], [], []
    main_calls = Counter()
    for event in _events(export):
        for call in event.get("tool_calls") or []:
            if call.get("name") == "create_goal":
                objectives.append(str(_args(call).get("objective", "")))
            elif call.get("name") == "update_goal":
                statuses.append(str(_args(call).get("status", "")))
        record = event.get("record") or {}
        owner = record.get("owner") or {}
        if record.get("usage_family") == "provider" and owner.get("requester_kind") == "main":
            mode = (record.get("goal_attribution") or {}).get("mode", "none")
            main_calls["goal" if mode != "none" else "none"] += 1
        if event.get("reminder_kind") == "goal" and event.get("decision_reason"):
            reasons.append(str(event["decision_reason"]))
    pinned = bool(objectives)
    closed = bool(statuses) and statuses[-1] == "complete"
    verdict = "pinned and closed complete" if pinned and closed else (
        f"pinned, last status {statuses[-1]!r}" if pinned and statuses else
        "pinned, never closed" if pinned else "NOT pinned")
    total = main_calls["goal"] + main_calls["none"]
    lines = [
        f"- **Goal:** {verdict}",
        f"- **Objective:** {objectives[0] if objectives else '(none)'}",
        f"- **Status updates:** {', '.join(statuses) or '(none)'}",
        f"- **Main-agent model calls:** {total}, of which {main_calls['goal']} were attributed to the goal "
        "(the call that creates the goal comes before it)",
    ]
    if reasons:
        lines.append(f"- **Goal reminder's last check:** {reasons[-1][:400]}")
    held = held_out_reads(export)
    if held:
        lines.append(f"- **FLAG, held-out files read:** {', '.join(held)}. "
                     "A read the brief asked for is fine; check any other as a leak")
    else:
        lines.append("- **Held-out files read:** none under `evidence/` or the fine-tune data")
    return pinned, lines


def main(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as stream:
            export = json.load(stream)
        pinned, lines = summarise(export)
    except (OSError, ValueError, KeyError) as exc:
        print(f"- **Goal:** no readable Muse export ({type(exc).__name__})")
        return 1
    print("\n".join(lines))
    return 0 if pinned else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
