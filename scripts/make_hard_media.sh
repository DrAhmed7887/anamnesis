#!/bin/zsh
# Staged hard photos for the crop-zoom check (batch 15.5). Phone-sized 12 MP frames with small print, a blister
# foil and a far-away pack, plus the portrait variants a phone really writes: landscape pixels with EXIF
# Orientation 6, and camera tags (make, model, a fake GPS fix at 0°N 0°E) on every JPEG.
# Everything is invented and drawn with Pillow. Output: evidence/raw/media/hard/ (git-ignored), with
# manifest.json holding the expected reading of every pack, written before any model sees the images.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
out=evidence/raw/media/hard
mkdir -p "$out"

uv run -q --no-project --with pillow python - "$out" <<'PY'
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

out = Path(sys.argv[1])
REG = "/System/Library/Fonts/Supplemental/Arial.ttf"
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
W, H = 4032, 3024  # a 12 MP phone frame, stored landscape


def table():
    return Image.blend(Image.new("RGB", (W, H), (150, 118, 86)),
                       Image.effect_noise((W, H), 40).convert("RGB"), 0.22)


def box_face(w, h, band, title, title_rgb, lines, title_px, line_px):
    face = Image.new("RGBA", (w, h), (250, 250, 247, 255))
    d = ImageDraw.Draw(face)
    d.rectangle([0, 0, w, int(h * 0.16)], fill=band)
    y = int(h * 0.26)
    d.text((int(w * 0.06), y), title, font=ImageFont.truetype(BOLD, title_px), fill=title_rgb)
    for i, text in enumerate(lines):
        d.text((int(w * 0.06), y + int(title_px * 1.5) + i * int(line_px * 1.6)), text,
               font=ImageFont.truetype(REG, line_px), fill=(45, 45, 45))
    return face


def foil_face(w, h, name, inn, name_px, inn_px):
    face = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(face)
    for y in range(h):  # brushed-aluminium gradient
        g = 196 + int(18 * abs((y / h) - 0.5))
        d.line([(0, y), (w, y)], fill=(g, g + 3, g + 8, 255))
    for row in (0.30, 0.72):
        for col in range(5):
            cx, cy = int(w * (0.12 + col * 0.19)), int(h * row)
            d.ellipse([cx - 60, cy - 46, cx + 60, cy + 46], fill=(176, 181, 190, 255), outline=(150, 155, 165, 255),
                      width=4)
            d.ellipse([cx - 30, cy - 30, cx - 6, cy - 14], fill=(236, 238, 242, 255))
    ink = (122, 130, 144, 255)  # low-contrast print on foil
    for band_y in (0.02, 0.48, 0.90):
        x = 10
        while x < w:
            d.text((x, int(h * band_y)), name, font=ImageFont.truetype(BOLD, name_px), fill=ink)
            d.text((x, int(h * band_y) + name_px + 2), inn, font=ImageFont.truetype(REG, inn_px), fill=ink)
            x += int(name_px * len(name) * 0.62) + 40
    return face.filter(ImageFilter.GaussianBlur(1.3))


def place(scene, face, cx, cy, angle):
    turned = face.rotate(angle, expand=True, resample=Image.BICUBIC)
    x, y = cx - turned.width // 2, cy - turned.height // 2
    scene.paste(turned, (x, y), turned)
    return [x, y, x + turned.width - 1, y + turned.height - 1]


def drawer():
    scene, packs = table(), []
    for args, pos, label, strength in [
        (((760, 500), (31, 111, 178), "Concor 5 mg", (31, 58, 95), ["Bisoprolol fumarate", "30 film-coated tablets"]),
         (900, 1000, 3), "Concor 5 mg", "bisoprolol 5 mg"),
        (((800, 520), (192, 57, 43), "Beloc-Zok 100 mg", (123, 31, 31),
          ["Metoprolol succinate", "Prolonged-release tablets"]), (2350, 1150, -4), "Beloc-Zok 100 mg",
         "metoprolol 100 mg"),
        (((720, 480), (46, 139, 87), "Norvasc 10 mg", (20, 80, 45), ["Amlodipine", "28 tablets"]),
         (1650, 2250, 2), "Norvasc 10 mg", "amlodipine 10 mg"),
    ]:
        (size, band, title, rgb, lines) = args
        box = place(scene, box_face(*size, band, title, rgb, lines, 44, 28), *pos)
        packs.append({"label": label, "strength": strength, "box_stored": box})
    return scene, packs


def foil():
    scene, packs = table(), []
    box = place(scene, foil_face(900, 420, "Glucophage 850 mg", "metformin hydrochloride", 20, 15), 1900, 1600, -6)
    packs.append({"label": "Glucophage 850 mg", "strength": "metformin 850 mg", "box_stored": box})
    box = place(scene, box_face(420, 280, (230, 120, 20), "Panadol 500 mg", (120, 60, 10), ["Paracetamol",
                                                                                          "24 tablets"], 24, 16),
                3350, 650, 5)
    packs.append({"label": "Panadol 500 mg", "strength": "paracetamol 500 mg", "box_stored": box})
    return scene, packs


def displayed(box, orientation):
    """Stored-pixel box -> the box a viewer sees (Orientation 6 = turn 90° clockwise to display)."""
    x1, y1, x2, y2 = box
    return box if orientation == 1 else [H - 1 - y2, x1, H - 1 - y1, x2]


def save(scene, name, orientation):
    exif = Image.Exif()
    exif[0x0112] = orientation  # Orientation
    exif[0x010F] = "Staged"  # Make
    exif[0x0110] = "Synthetic phone"  # Model
    gps = exif.get_ifd(0x8825)
    gps.update({1: "N", 2: (0.0, 0.0, 0.0), 3: "E", 4: (0.0, 0.0, 0.0)})  # a fake fix at 0°N 0°E
    scene.filter(ImageFilter.GaussianBlur(0.8)).save(out / name, "JPEG", quality=82, exif=exif)


manifest = []
for scene_fn, stem in [(drawer, "drawer"), (foil, "foil")]:
    scene, packs = scene_fn()
    for orientation, suffix in [(1, "landscape"), (6, "portrait")]:
        name = f"{stem}_{suffix}.jpg"
        save(scene, name, orientation)
        frame = [W, H] if orientation == 1 else [H, W]
        manifest.append({"file": name, "orientation": orientation, "frame_displayed": frame,
                         "packs": [{**p, "box_displayed": displayed(p["box_stored"], orientation)} for p in packs]})
(out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
for item in manifest:
    path = out / item["file"]
    print(f"{path} {path.stat().st_size} bytes, orientation {item['orientation']}, {len(item['packs'])} packs")
PY
