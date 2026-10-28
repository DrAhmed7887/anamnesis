"""Video stills: render a record or a page to a 1920×1080 PNG with headless Chrome, for the final video.

    uv run python scripts/still.py <name> --text <file|-> [--title TEXT] [--tail N | --head N]
    uv run python scripts/still.py <name> --html <page.html> [--height PX]

Writes evidence/raw/video/stills/<date>/<HHMM>_<name>.png, which is git-ignored. Only the given record or page
is rendered, never the desktop. Local paths are shortened ("~", "anamnesis", "scratch") before rendering.
"""

import argparse
import html
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/raw/video/stills"
PROFILE = ROOT / "evidence/raw/video/.chrome"  # a throwaway Chrome profile, never the user's own
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCRATCH = re.compile(r"/private/tmp/claude-\d+/\S*?/scratchpad")
PAGE = """<!doctype html><meta charset="utf-8"><style>
body {{margin: 0; background: #0d1117; color: #e6edf3; font: 26px/1.45 "SF Mono", Menlo, monospace}}
.bar {{background: #161b22; color: #8b949e; padding: 18px 28px; font: 22px -apple-system, sans-serif;
       border-bottom: 1px solid #30363d}}
.dot {{display: inline-block; width: 14px; height: 14px; border-radius: 50%; margin-right: 9px}}
pre {{margin: 0; padding: 28px 36px; white-space: pre-wrap; overflow-wrap: anywhere}}
</style>
<div class="bar"><span class="dot" style="background: #ff5f57"></span><span class="dot"
style="background: #febc2e"></span><span class="dot" style="background: #28c840"></span>&nbsp; {title}</div>
<pre dir="auto">{text}</pre>"""


def scrub(text: str) -> str:
    return SCRATCH.sub("scratch", text).replace(str(ROOT), "anamnesis").replace(str(Path.home()), "~")


def shoot(url: str, out: Path, height: int) -> None:
    PROFILE.mkdir(parents=True, exist_ok=True)
    subprocess.run([CHROME, "--headless=new", "--hide-scrollbars", "--no-first-run", "--disable-gpu",
                    f"--user-data-dir={PROFILE}", f"--window-size=1920,{height}", f"--screenshot={out}", url],
                   check=True, capture_output=True, timeout=90)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="a text record to render, or - for stdin")
    source.add_argument("--html", help="an HTML page to capture as it is")
    parser.add_argument("--title", default="")
    parser.add_argument("--tail", type=int, help="keep only the last N lines")
    parser.add_argument("--head", type=int, help="keep only the first N lines")
    parser.add_argument("--height", type=int, default=1080)
    args = parser.parse_args()
    now = datetime.now()
    folder = OUT / now.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"{now:%H%M}_{args.name}.png"
    if args.html:
        shoot(Path(args.html).resolve().as_uri(), out, args.height)
    else:
        text = sys.stdin.read() if args.text == "-" else Path(args.text).read_text(encoding="utf-8")
        lines = scrub(text).rstrip("\n").splitlines()
        lines = lines[-args.tail:] if args.tail else lines[: args.head] if args.head else lines
        page = out.with_suffix(".html")
        page.write_text(PAGE.format(title=html.escape(args.title or args.name),
                                    text=html.escape("\n".join(lines))), encoding="utf-8")
        shoot(page.as_uri(), out, args.height)
    print(out.relative_to(ROOT))


if __name__ == "__main__":
    main()
