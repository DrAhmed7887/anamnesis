"""Batch 6 contract: formats seen in the first live calls (27 Oct 2026). Written by the reviewer; do not edit."""

from pathlib import Path

from anamnesis.providers import parse_sam_output, top_regions

LIVE = Path(__file__).parents[1] / "fixtures" / "sam31_label_packs_live.txt"


def test_real_sam31_output_parses():
    # Captured from sam-3.1, concept "label", on the synthetic two-pack photo (scripts/make_synthetic_media.sh).
    # It differs from the documented format: the mask carries its own c=…, and the text ends with a newline.
    regions = parse_sam_output(LIVE.read_text(encoding="utf-8"), image_sha256="1" * 64)
    boxes = {(r.x1, r.y1, r.x2, r.y2) for r in regions}
    assert boxes == {(700, 211, 1170, 539), (110, 171, 580, 499)}
    assert all(r.frame_w == 1280 and r.frame_h == 720 for r in regions)
    assert all(r.confidence is not None and 0.5 < r.confidence < 0.6 for r in regions)
    assert len(top_regions(regions)) == 2
