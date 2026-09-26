"""Generate a 1280x720 YouTube-style thumbnail: a real photo background
(via Pexels, when configured) with a bold outlined headline, a legibility
band, and a small accent badge - the common "creator thumbnail" look,
instead of a flat solid/gradient background.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

from .script_generator import VideoScript
from .video_builder import _background_color_for, _fetch_pexels_background, _load_font

THUMB_SIZE = (1280, 720)


def _accent_color_for(seed: str) -> tuple[int, int, int]:
    # A punchier, more saturated palette than the background gradient uses,
    # since this is meant to pop as a small badge, not fill the frame.
    palette = [
        (230, 57, 70),
        (255, 140, 0),
        (0, 150, 199),
        (76, 175, 80),
        (156, 39, 176),
    ]
    return palette[hash(seed) % len(palette)]


def use_custom_thumbnail(source_path: Path, out_path: Path) -> Path:
    """Use a user-supplied image as the thumbnail as-is (format-converted
    only), instead of generating one from the script.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(source_path).convert("RGB")
    img.save(out_path)
    return out_path


def build_thumbnail(script: VideoScript, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    keyword = script.thumbnail_visual_keyword or script.thumbnail_text or script.title
    img = _fetch_pexels_background(keyword, THUMB_SIZE)
    if img is None:
        top = _background_color_for(keyword)
        bottom = tuple(min(c + 60, 255) for c in top)
        img = Image.new("RGB", THUMB_SIZE)
        grad = ImageDraw.Draw(img)
        for y in range(THUMB_SIZE[1]):
            t = y / THUMB_SIZE[1]
            color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
            grad.line([(0, y), (THUMB_SIZE[0], y)], fill=color)

    img = img.convert("RGBA")

    text = script.thumbnail_text or script.title
    font = _load_font(110)
    draw = ImageDraw.Draw(img)
    wrapped = textwrap.fill(text, width=10)
    lines = wrapped.split("\n")[:2]

    line_height = 128
    band_height = line_height * len(lines) + 70
    band_top = THUMB_SIZE[1] - band_height

    # Dark gradient band behind the text only, so the photo above it stays
    # visible instead of the whole thumbnail being dimmed.
    band = Image.new("RGBA", THUMB_SIZE, (0, 0, 0, 0))
    band_draw = ImageDraw.Draw(band)
    for y in range(band_top, THUMB_SIZE[1]):
        t = (y - band_top) / band_height
        alpha = int(190 * min(1.0, t * 1.8))
        band_draw.line([(0, y), (THUMB_SIZE[0], y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, band)
    draw = ImageDraw.Draw(img)

    y = band_top + 35
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (THUMB_SIZE[0] - text_w) / 2
        for dx in (-5, 0, 5):
            for dy in (-5, 0, 5):
                draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_height

    # Small accent badge in the top-left corner (first tag, or the topic).
    badge_text = (script.tags[0] if script.tags else script.title)[:10]
    badge_font = _load_font(44)
    badge_color = _accent_color_for(script.title)
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_w, badge_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 28, 18
    badge_box = (40, 40, 40 + badge_w + pad_x * 2, 40 + badge_h + pad_y * 2)
    draw.rounded_rectangle(badge_box, radius=16, fill=(*badge_color, 235))
    draw.text(
        (badge_box[0] + pad_x, badge_box[1] + pad_y - 4),
        badge_text,
        font=badge_font,
        fill=(255, 255, 255, 255),
    )

    # Thick accent-colored frame around the whole thumbnail for a
    # "designed" rather than "raw photo" look.
    border = 14
    draw.rectangle(
        [(0, 0), (THUMB_SIZE[0] - 1, THUMB_SIZE[1] - 1)],
        outline=(*badge_color, 255),
        width=border,
    )

    img.convert("RGB").save(out_path)
    return out_path
