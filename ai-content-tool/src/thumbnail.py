"""Generate a 1280x720 YouTube-style thumbnail from the script's headline text."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .script_generator import VideoScript
from .video_builder import _background_color_for, _load_font

THUMB_SIZE = (1280, 720)


def build_thumbnail(script: VideoScript, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    top = _background_color_for(script.thumbnail_text or script.title)
    bottom = tuple(min(c + 60, 255) for c in top)
    img = Image.new("RGB", THUMB_SIZE)
    draw = ImageDraw.Draw(img)
    for y in range(THUMB_SIZE[1]):
        t = y / THUMB_SIZE[1]
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        draw.line([(0, y), (THUMB_SIZE[0], y)], fill=color)

    font = _load_font(120)
    text = script.thumbnail_text or script.title
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (THUMB_SIZE[0] - text_w) / 2
    y = (THUMB_SIZE[1] - text_h) / 2

    # Outline for legibility over any background color.
    for dx in (-4, 0, 4):
        for dy in (-4, 0, 4):
            draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0))
    draw.text((x, y), text, font=font, fill=(255, 255, 255))

    img.save(out_path)
    return out_path
