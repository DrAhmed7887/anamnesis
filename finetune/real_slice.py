"""Build test_real (plan.md, "The real-transcript slice"): the transcripts Muse Voice Transcribe actually
returned on 27-28 Oct for the U cases and the two synthetic notes, one example per distinct transcript.

    .venv/bin/python finetune/real_slice.py [--out DIR]

Reads only evidence/live/2026-10-27/report_*.json and evidence/live/2026-10-28/report_*.json, never anything
under evidence/raw/. Writes test_real.jsonl and test_real.answers.jsonl, in the generator's formats.
The answers come from each note's script, in the table below, written by hand before any model saw the slice:
U1-U12 from evidence/batches/21/manifest.md (the voice-note column, and the U11 and U12 rows), en and ar from
scripts/make_synthetic_media.sh. The answer is what the patient meant, read by the product's prompt.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from anamnesis.core.catalogue import normalise  # noqa: E402
from anamnesis.schema import AudioTurn  # noqa: E402
from finetune.common import (  # noqa: E402
    DATA_DIR,
    Amount,
    ClaimSpec,
    answer_text,
    chat_row,
    check_example,
    format_turns,
    write_jsonl,
)

LIVE_DAYS = (ROOT / "evidence" / "live" / "2026-10-27", ROOT / "evidence" / "live" / "2026-10-28")
REPORT_NAME = re.compile(r"report_(U\d+|en|ar)(?:[-_].*)?\.json")
EXPECTED_TRANSCRIPTS, EXPECTED_NOTES = 33, 14


@dataclass(frozen=True)
class Said:
    """One medicine as the note's script says it. `forms` are the ways a transcript may spell the name, the
    script's own first; the answer copies the first that occurs in the transcript. Amounts are in mg."""

    forms: tuple[str, ...]
    intake: str | None = None
    per_day: int | None = None
    units: int | None = None
    as_needed: bool | None = None
    inn_said: bool = False
    status: str = "active"


BELOC_ZOK = ("Beloc-Zok", "BelocZok", "Beloc Zok")  # Voice Transcribe wrote "BelocZok"
PANADOL_U9 = (Said(("Panadol",), intake="500"),)  # "I take Panadol five hundred milligrams."
SCRIPTS: dict[str, tuple[Said, ...]] = {
    # "I take Concor five milligrams once a day."
    "U1": (Said(("Concor",), intake="5", per_day=1),),
    # "I take Augmentin, eight hundred seventy-five and one hundred twenty-five milligrams, twice a day."
    # Two ingredients' amounts fit no field without naming the ingredients, which the patient didn't say and
    # the prompt forbids inferring from a brand; nor is it "the 875 mg tablets". So both amounts are null.
    "U2": (Said(("Augmentin",), per_day=2),),
    # "I take Panadol five hundred milligrams when I need it."
    "U3": (Said(("Panadol",), intake="500", as_needed=True),),
    # "I take Panadol five hundred milligrams, two tablets at a time." No tablet is described ("the 500 mg
    # tablets"), so by the prompt the amount is an intake, with two units per intake.
    "U4": (Said(("Panadol",), intake="500", units=2),),
    # "I take Norvasc five milligrams in the evening." One time of day: once a day.
    "U5": (Said(("Norvasc",), intake="5", per_day=1),),
    # "I take Glucophage five hundred milligrams twice a day."
    "U6": (Said(("Glucophage",), intake="500", per_day=2),),
    # "I take Lipitor twenty milligrams at night." Once a day, as U5.
    "U7": (Said(("Lipitor",), intake="20", per_day=1),),
    # "I take Beloc-Zok one hundred milligrams once a day."
    "U8": (Said(BELOC_ZOK, intake="100", per_day=1),),
    "U9": PANADOL_U9,
    "U10": PANADOL_U9,  # "U9's note"
    # "I take ibuprofen four hundred milligrams when I have pain."
    "U11": (Said(("ibuprofen",), intake="400", as_needed=True, inn_said=True),),
    # "I take Concor ten milligrams every morning, and Beloc-Zok fifty milligrams twice a day." An intake of
    # 10 mg once a day, not a strength (u11-u12.md).
    "U12": (Said(("Concor",), intake="10", per_day=1), Said(BELOC_ZOK, intake="50", per_day=2)),
    # "I take Concor five milligrams once a day. I also take metoprolol, fifty milligrams twice a day.
    # I stopped taking Panadol last month."
    "en": (
        Said(("Concor",), intake="5", per_day=1),
        Said(("metoprolol",), intake="50", per_day=2, inn_said=True),
        Said(("Panadol",), status="discontinued"),
    ),
    # «أنا باخد كونكور خمسة مليجرام مرة في اليوم. وباخد بيلوك زوك خمسين مليجرام مرتين في اليوم. وقفت البنادول
    # من شهر.» The name is copied as spoken, article included: «البنادول».
    "ar": (
        Said(("كونكور",), intake="5", per_day=1),
        Said(("بيلوك زوك",), intake="50", per_day=2),
        Said(("البنادول",), status="discontinued"),
    ),
}


def note_of(path: Path) -> str:
    match = REPORT_NAME.fullmatch(path.name)
    if match is None or match.group(1) not in SCRIPTS:
        raise ValueError(f"no script for {path.name}")
    return match.group(1)


def _spec(said: Said, turns: list[AudioTurn]) -> ClaimSpec:
    for form in said.forms:
        cited = tuple(turn.turn_id for turn in turns if normalise(form) in normalise(turn.transcript))
        if cited:
            break
    else:
        raise ValueError(f"none of {said.forms} occurs in {[turn.transcript for turn in turns]}")
    return ClaimSpec(
        name_text=form,
        turn_ids=cited,
        status=said.status,
        inn=form if said.inn_said else None,
        intake=Amount(Decimal(said.intake), "mg", form) if said.intake else None,
        units=None if said.units is None else Decimal(said.units),
        per_day=None if said.per_day is None else Decimal(said.per_day),
        as_needed=said.as_needed,
    )


def distinct_transcripts() -> list[dict]:
    """One entry per distinct transcript, in report order: its turns (from the first report), notes and
    reports."""
    found: dict[tuple[str, ...], dict] = {}
    for day in LIVE_DAYS:
        for path in sorted(day.glob("report_*.json")):
            report = json.loads(path.read_text(encoding="utf-8"))
            turns = [AudioTurn.model_validate(turn) for turn in report["turns"]]
            entry = found.setdefault(tuple(turn.transcript for turn in turns),
                                     {"turns": turns, "notes": [], "reports": []})
            entry["reports"].append(str(path.relative_to(ROOT)))
            if note_of(path) not in entry["notes"]:
                entry["notes"].append(note_of(path))
    return list(found.values())


def build(out: Path = DATA_DIR) -> list[dict]:
    """Write test_real.jsonl and its answers; return the answer lines."""
    entries = distinct_transcripts()
    notes = {note for entry in entries for note in entry["notes"]}
    if len(entries) != EXPECTED_TRANSCRIPTS or len(notes) != EXPECTED_NOTES:
        raise ValueError(f"{len(entries)} distinct transcripts from {len(notes)} notes; the plan says "
                         f"{EXPECTED_TRANSCRIPTS} from {EXPECTED_NOTES}")
    rows, sidecars = [], []
    for index, entry in enumerate(entries):
        scripts = {SCRIPTS[note] for note in entry["notes"]}
        if len(scripts) != 1:
            raise ValueError(f"notes {entry['notes']} share a transcript but not a script")
        turns = entry["turns"]
        specs = [_spec(said, turns) for said in scripts.pop()]
        answer = answer_text(specs)
        parsed = check_example(turns, specs, answer)
        rows.append(chat_row(format_turns(turns), answer))
        sidecars.append({
            "index": index,
            "id": f"test_real-{index:04d}",
            "split": "test_real",
            "notes": entry["notes"],
            "reports": entry["reports"],
            "templates": [f"note:{note}" for note in entry["notes"]],
            "drugs": [spec.name_text for spec in specs],
            "turns": [turn.model_dump() for turn in turns],
            "claims": [claim.model_dump(mode="json") for claim in parsed],
        })
    write_jsonl(out / "test_real.jsonl", rows)
    write_jsonl(out / "test_real.answers.jsonl", sidecars)
    return sidecars


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=DATA_DIR)
    args = parser.parse_args()
    sidecars = build(args.out)
    reports = sum(len(sidecar["reports"]) for sidecar in sidecars)
    notes = sorted({note for sidecar in sidecars for note in sidecar["notes"]}, key=lambda n: (len(n), n))
    print(f"test_real: {len(sidecars)} distinct transcripts from {len(notes)} notes ({', '.join(notes)}), "
          f"{reports} reports; files in {args.out}")


if __name__ == "__main__":
    main()
