"""Assemble a slideshow-style video from a script + narration audio.

Design choice: instead of moviepy's TextClip (which requires ImageMagick to
be installed and configured, a common source of setup pain), captions are
rendered to PNG frames with Pillow and then used as moviepy ImageClips. This
keeps the only external binary dependency to ffmpeg (which moviepy already
needs for video/audio encoding).
"""
from __future__ import annotations

import hashlib
import io
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import settings
from .script_generator import VideoScript
from .tts import NarrationClip

FRAME_SIZE = (1080, 1920)  # vertical video, matches Shorts/Reels/TikTok
FONT_CANDIDATES = [
    settings.output_dir.parent / "assets" / "fonts" / "cjk.ttf",
    settings.output_dir.parent / "assets" / "fonts" / "cjk.ttc",
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf"),
    Path("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"),
    Path("C:/Windows/Fonts/msjh.ttc"),
    Path("/System/Library/Fonts/PingFang.ttc"),
]


class MissingFontError(RuntimeError):
    pass


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    raise MissingFontError(
        "找不到可顯示中文的字型檔。請下載一個免費的中文字型(例如 Noto Sans TC),"
        "放到 ai-content-tool/assets/fonts/cjk.ttf 再重跑一次。"
    )


def _background_color_for(keyword: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(keyword.encode("utf-8")).digest()
    # Keep colors mid-tone so white caption text stays readable.
    r, g, b = digest[0] % 120 + 40, digest[1] % 120 + 40, digest[2] % 120 + 40
    return (r, g, b)


def _cover_resize(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Resize+crop to fill ``size`` without distorting the aspect ratio
    (like CSS `object-fit: cover`), instead of a naive stretch-to-fit.
    """
    target_w, target_h = size
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = round(src_w * scale), round(src_h * scale)
    img = img.resize((new_w, new_h))
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _fetch_pexels_background(keyword: str, size: tuple[int, int]) -> Image.Image | None:
    if not settings.pexels_api_key:
        return None
    try:
        import requests

        width, height = size
        if width > height:
            orientation, src_key = "landscape", "landscape"
        elif width < height:
            orientation, src_key = "portrait", "portrait"
        else:
            orientation, src_key = "square", "medium"

        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": settings.pexels_api_key},
            params={"query": keyword, "orientation": orientation, "per_page": 1},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("photos", [])
        if not results:
            return None
        image_url = results[0]["src"][src_key]
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()
        img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
        return _cover_resize(img, size)
    except Exception:
        return None


def _build_background(keyword: str) -> Image.Image:
    fetched = _fetch_pexels_background(keyword, FRAME_SIZE)
    if fetched is not None:
        # Darken slightly so white captions stay legible over any photo.
        overlay = Image.new("RGB", FRAME_SIZE, (0, 0, 0))
        return Image.blend(fetched, overlay, alpha=0.35)

    top = _background_color_for(keyword)
    bottom = tuple(max(c - 40, 0) for c in top)
    img = Image.new("RGB", FRAME_SIZE)
    draw = ImageDraw.Draw(img)
    for y in range(FRAME_SIZE[1]):
        t = y / FRAME_SIZE[1]
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        draw.line([(0, y), (FRAME_SIZE[0], y)], fill=color)
    return img


def render_scene_frame(narration: str, visual_keyword: str) -> Image.Image:
    img = _build_background(visual_keyword)
    draw = ImageDraw.Draw(img)
    font = _load_font(64)

    wrapped = textwrap.fill(narration, width=16)
    lines = wrapped.split("\n")
    line_height = 80
    block_height = line_height * len(lines) + 60
    box_top = FRAME_SIZE[1] - block_height - 160
    draw.rectangle(
        [(0, box_top), (FRAME_SIZE[0], box_top + block_height)],
        fill=(0, 0, 0, 160),
    )

    y = box_top + 30
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (FRAME_SIZE[0] - text_width) / 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
        y += line_height

    return img


def build_video(
    script: VideoScript,
    narrations: list[NarrationClip],
    out_path: Path,
    bgm_path: Path | None = None,
) -> tuple[Path, list[dict]]:
    """Returns (video_path, attributions) - attributions lists any
    Attribution-licensed Freesound SFX credits the caller should surface
    (e.g. write to an ATTRIBUTION.txt alongside the video)."""
    from moviepy import (
        AudioFileClip,
        CompositeAudioClip,
        ImageClip,
        concatenate_videoclips,
    )

    if len(narrations) != len(script.scenes):
        raise ValueError("narrations 數量必須與 scenes 數量相同")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    frames_dir = out_path.parent / "frames"
    frames_dir.mkdir(exist_ok=True)

    from . import sfx as sfx_module

    sfx_dir = out_path.parent / "sfx"
    attributions: list[dict] = []

    clips = []
    for i, (scene, narration) in enumerate(zip(script.scenes, narrations)):
        frame = render_scene_frame(scene.narration, scene.visual_keyword)
        frame_path = frames_dir / f"scene_{i:02d}.png"
        frame.save(frame_path)

        audio_clip = AudioFileClip(str(narration.path))
        combined_audio = audio_clip
        sfx_clips = []
        for name in scene.sfx:
            result = sfx_module.build_sfx(name, sfx_dir / f"scene_{i:02d}_{name}.wav", sfx_dir)
            if result is not None:
                sfx_path, attribution = result
                sfx_clips.append(AudioFileClip(str(sfx_path)))
                if attribution:
                    attributions.append(attribution)
        if sfx_clips:
            combined_audio = CompositeAudioClip([audio_clip, *sfx_clips])

        image_clip = (
            ImageClip(str(frame_path))
            .with_duration(combined_audio.duration)
            .with_audio(combined_audio)
        )
        clips.append(image_clip)

    video = concatenate_videoclips(clips, method="compose")

    if bgm_path and bgm_path.exists():
        bgm = AudioFileClip(str(bgm_path)).with_volume_scaled(settings.bgm_volume)
        if bgm.duration < video.duration:
            loops = int(video.duration // bgm.duration) + 1
            from moviepy import concatenate_audioclips

            bgm = concatenate_audioclips([bgm] * loops)
        bgm = bgm.subclipped(0, video.duration)
        video = video.with_audio(CompositeAudioClip([video.audio, bgm]))

    video.write_videofile(
        str(out_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        logger=None,
    )

    for clip in clips:
        clip.close()

    return out_path, attributions
