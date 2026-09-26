"""End-to-end orchestration: topic -> script -> narration -> video -> thumbnail -> (optional) upload."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from . import bgm as bgm_module
from . import script_generator, thumbnail, tts, video_builder
from .config import settings
from .script_generator import VideoScript
from .topic_research import trending_topics


def slugify(text: str) -> str:
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"[^\w\-一-鿿]", "", text)
    return text[:60] or "untitled"


@dataclass
class PipelineResult:
    work_dir: Path
    script: VideoScript
    video_path: Path
    thumbnail_path: Path
    publish_url: str | None = None


def pick_topic(explicit_topic: str | None) -> str:
    if explicit_topic:
        return explicit_topic
    candidates = trending_topics(limit=5)
    if not candidates:
        raise SystemExit(
            "沒有指定 --topic,且自動選題也拿不到結果(可能是網路或 pytrends 問題)。"
            "請用 --topic \"你的主題\" 手動指定。"
        )
    return candidates[0].keyword


def run_pipeline(
    topic: str | None,
    publish: bool = False,
    bgm_path: Path | None = None,
    bgm_preset: str | None = None,
    script_file: Path | None = None,
    thumbnail_file: Path | None = None,
) -> PipelineResult:
    if script_file:
        print(f"[1/5] 使用手寫腳本: {script_file}")
        print("[2/5] 略過 AI 腳本生成")
        data = json.loads(script_file.read_text(encoding="utf-8"))
        script = VideoScript.from_dict(data)
    else:
        chosen_topic = pick_topic(topic)
        print(f"[1/5] 主題: {chosen_topic}")

        print("[2/5] 產生腳本...")
        script = script_generator.generate_script(chosen_topic)

    work_dir = settings.output_dir / slugify(script.title)
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "script.json").write_text(
        json.dumps(script.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[3/5] 產生 {len(script.scenes)} 段旁白語音...")
    narrations = []
    for i, scene in enumerate(script.scenes):
        clip = tts.synthesize_scene(
            scene.narration, work_dir / "audio" / f"scene_{i:02d}", speaker=scene.speaker
        )
        narrations.append(clip)

    if bgm_preset and not bgm_path:
        bgm_path = bgm_module.build_bgm_preset(
            bgm_preset, work_dir / "bgm" / f"{bgm_preset}.wav", work_dir / "bgm"
        )
        if bgm_path is None:
            available = ", ".join(bgm_module.BGM_PRESETS)
            raise SystemExit(f"找不到內建配樂 '{bgm_preset}',可用選項: {available}")

    print("[4/5] 剪輯影片...")
    video_path = video_builder.build_video(
        script, narrations, work_dir / "video.mp4", bgm_path=bgm_path
    )
    if thumbnail_file:
        thumb_path = thumbnail.use_custom_thumbnail(thumbnail_file, work_dir / "thumbnail.png")
    else:
        thumb_path = thumbnail.build_thumbnail(script, work_dir / "thumbnail.png")

    result = PipelineResult(
        work_dir=work_dir, script=script, video_path=video_path, thumbnail_path=thumb_path
    )

    if publish:
        print("[5/5] 上傳到 YouTube...")
        from .publishers.youtube import YouTubePublisher

        publisher = YouTubePublisher()
        publish_result = publisher.upload(
            video_path=video_path,
            title=script.title,
            description=script.description,
            tags=script.tags,
            thumbnail_path=thumb_path,
        )
        result.publish_url = publish_result.url
        print(f"已上傳: {publish_result.url}")
    else:
        print("[5/5] 略過上傳 (未加 --publish)")

    return result
