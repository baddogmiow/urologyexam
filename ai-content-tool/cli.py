#!/usr/bin/env python3
"""CLI entry point for the AI content pipeline.

Examples:
    python cli.py run --topic "如何挑選一台筆電"
    python cli.py run --topic "..." --publish
    python cli.py research
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.bgm import BGM_PRESETS
from src.pipeline import run_pipeline
from src.topic_research import trending_topics


def main() -> None:
    parser = argparse.ArgumentParser(description="AI content generation & publishing pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run the full pipeline: topic -> video -> (optional) upload")
    run_p.add_argument("--topic", type=str, default=None, help="手動指定主題;不填則自動抓熱門關鍵字")
    run_p.add_argument("--publish", action="store_true", help="產出後自動上傳到 YouTube")
    run_p.add_argument("--bgm", type=str, default=None, help="自訂背景音樂檔路徑 (mp3/wav)")
    run_p.add_argument(
        "--bgm-preset", type=str, default=None, choices=list(BGM_PRESETS),
        help="使用內建合成配樂(免版權疑慮),與 --bgm 擇一即可",
    )
    run_p.add_argument(
        "--script-file", type=str, default=None,
        help="使用手寫腳本 JSON 檔,略過 AI 腳本生成(格式參考 output/*/script.json)",
    )
    run_p.add_argument(
        "--thumbnail-file", type=str, default=None,
        help="使用自訂縮圖圖檔(jpg/png/webp皆可),略過自動生成縮圖",
    )

    sub.add_parser("research", help="只列出目前熱門選題候選,不產生內容")

    args = parser.parse_args()

    if args.command == "research":
        candidates = trending_topics(limit=10)
        if not candidates:
            print("目前拿不到熱門選題(可能無網路或地區不支援)。請改用 run --topic 手動指定。")
            return
        for c in candidates:
            print(f"- {c.keyword}  (source={c.source}, score={c.score})")
        return

    if args.command == "run":
        bgm_path = Path(args.bgm) if args.bgm else None
        script_file = Path(args.script_file) if args.script_file else None
        thumbnail_file = Path(args.thumbnail_file) if args.thumbnail_file else None
        result = run_pipeline(
            topic=args.topic,
            publish=args.publish,
            bgm_path=bgm_path,
            bgm_preset=args.bgm_preset,
            script_file=script_file,
            thumbnail_file=thumbnail_file,
        )
        print("\n完成!輸出目錄:", result.work_dir)
        print("影片:", result.video_path)
        print("縮圖:", result.thumbnail_path)
        if result.publish_url:
            print("已發布網址:", result.publish_url)


if __name__ == "__main__":
    main()
