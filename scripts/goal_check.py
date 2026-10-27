"""Did a headless Muse run pin its goal, close it, and do its work under it? Reads one `muse export`.

    uv run python scripts/goal_check.py evidence/raw/batch-<n>-muse_session.json

batch.sh prints this after every Muse run and keeps it as evidence/batches/<n>/goal.md. The export itself
stays in evidence/raw/ (git-ignored). Exit status 1 when no goal was pinned or the export can't be read.
"""

import json
import sys
from collections import Counter


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
