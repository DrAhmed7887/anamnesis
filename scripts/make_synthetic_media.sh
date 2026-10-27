#!/bin/zsh
# Synthetic demo media: two voice notes (macOS `say`) and one mock photo of two medicine packs (ffmpeg).
# Everything is invented. Output goes to evidence/raw/media/ (git-ignored); rerun this script to rebuild it.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
out=evidence/raw/media
mkdir -p "$out"
font=/System/Library/Fonts/Supplemental/Arial.ttf
bold="/System/Library/Fonts/Supplemental/Arial Bold.ttf"

to_wav() {  # Voice Transcribe takes WAV only: mono, 16-bit PCM, 16 kHz
  ffmpeg -loglevel error -y -i "$1" -ac 1 -ar 16000 -sample_fmt s16 "$2"
}

say -v Samantha -o "$out/en.aiff" \
  "I take Concor five milligrams once a day. I also take metoprolol, fifty milligrams twice a day. I stopped taking Panadol last month."
to_wav "$out/en.aiff" "$out/voice_en.wav"

say -v Majed -o "$out/ar.aiff" \
  "أنا باخد كونكور خمسة مليجرام مرة في اليوم. وباخد بيلوك زوك خمسين مليجرام مرتين في اليوم. وقفت البنادول من شهر."
to_wav "$out/ar.aiff" "$out/voice_ar.wav"
rm -f "$out"/*.aiff

# Mock photo: two packs on a table. Box 1 immediate release, box 2 prolonged release.
# Drawn with Pillow in a throwaway uv environment, so the project gains no dependency.
uv run -q --no-project --with pillow python - "$out/packs.png" "$font" "$bold" <<'PY'
import sys
from PIL import Image, ImageDraw, ImageFont
path, regular, bold = sys.argv[1:4]
img = Image.new("RGB", (1280, 720), (184, 166, 142))
d = ImageDraw.Draw(img)
def pack(x, y, band, title, colour, lines):
    d.rectangle([x, y, x + 470, y + 330], fill="white")
    d.rectangle([x, y, x + 470, y + 60], fill=band)
    d.text((x + 28, y + 85), title, font=ImageFont.truetype(bold, 46), fill=colour)
    for i, (text, size) in enumerate(lines):
        d.text((x + 28, y + 170 + i * 58), text, font=ImageFont.truetype(regular, size), fill=(30, 30, 30))
pack(110, 170, (31, 111, 178), "Concor 5 mg", (31, 58, 95),
     [("Bisoprolol fumarate", 34), ("30 film-coated tablets", 30)])
pack(700, 210, (192, 57, 43), "Beloc-Zok 100 mg", (123, 31, 31),
     [("Metoprolol succinate", 34), ("Prolonged-release tablets", 30)])
img.save(path)
PY

for f in "$out"/voice_en.wav "$out"/voice_ar.wav "$out"/packs.png; do
  print "$f $(shasum -a 256 "$f" | cut -c1-12) $(wc -c < "$f" | tr -d ' ') bytes"
done
