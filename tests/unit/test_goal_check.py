"""scripts/goal_check.py flags reads of held-out files (29 Oct): expected results the builder must not see."""

import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "goal_check", Path(__file__).resolve().parents[2] / "scripts" / "goal_check.py")
goal_check = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(goal_check)


def export(*calls, text=None):
    events = [{"envelope": {"payload": {"event": {"tool_calls": list(calls)}}}}]
    if text is not None:
        events.append({"envelope": {"payload": {"event": {"content": text}}}})
    return {"events": events}


def call(name, **args):
    return {"name": name, "args": json.dumps(args)}


def test_a_read_of_the_manifest_is_flagged():
    found = goal_check.held_out_reads(export(call("read_file", path="evidence/batches/24/manifest.md")))
    assert found == ["`evidence/batches/24/manifest.md` (read_file)"]


def test_the_exports_own_read_line_is_flagged():
    found = goal_check.held_out_reads(export(text="Read text file `evidence/batches/24/manifest.md`"))
    assert found == ["`evidence/batches/24/manifest.md` (Read text file)"]


def test_a_bash_read_of_a_test_split_and_an_absolute_path_are_flagged():
    found = goal_check.held_out_reads(export(
        call("bash", command="head finetune/data_v2/test_spain.answers.jsonl"),
        call("read_file", path="/Users/x/Projects/anamnesis/evidence/live/report.json")))
    assert found == ["`finetune/data_v2/test_spain.answers.jsonl` (bash)",
                     "`evidence/live/report.json` (read_file)"]


def test_a_path_quoted_in_an_edit_is_not_a_read():
    edit = call("edit_file", path="tests/unit/test_b24_extra.py", find="x",
                replace='"""See evidence/batches/24/manifest.md."""')
    assert goal_check.held_out_reads(export(edit, call("read_file", path="SPEC.md"))) == []


def test_the_flag_is_a_report_line_and_never_the_exit_status():
    pinned, lines = goal_check.summarise(export(call("create_goal", objective="o"),
                                                call("read_file", path="evidence/x.md")))
    assert pinned
    assert lines[-1].startswith("- **FLAG, held-out files read:** `evidence/x.md` (read_file)")
