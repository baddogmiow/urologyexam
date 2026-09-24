"""Turn a topic into a structured, scene-by-scene video script using an LLM."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict

from .config import settings

SYSTEM_PROMPT = """你是短影音腳本編劇。收到一個主題後,產出一支 60-120 秒說明/科普類影片的腳本。
只能輸出一個 JSON 物件,格式如下,不要有任何 JSON 以外的文字:

{
  "title": "吸引點擊但不誇大不實的標題(繁體中文,30字以內)",
  "description": "影片描述,含2-3個重點與一句免責聲明(內容由AI輔助生成僅供參考)",
  "tags": ["關鍵字1", "關鍵字2", "..."],
  "thumbnail_text": "縮圖上要放的短文字(8字以內,吸睛但不腥羶色)",
  "scenes": [
    {"narration": "這一幕的旁白逐字稿(繁體中文,一兩句話)", "visual_keyword": "用來找背景圖/影片素材的英文關鍵字"}
  ]
}

規則:
- scenes 陣列要有 5 到 9 個場景,合起來旁白總長度抓 60-120 秒口語速度。
- narration 禁止使用任何無法查證的誇大醫療/財務/法律承諾。
- 不得包含色情、暴力、仇恨、詐騙、抄襲他人受版權保護的原文字句。
- 若主題涉及專業領域(醫療、法律、財務等),於 description 附上「僅供參考,非專業建議」字樣。
"""


@dataclass
class Scene:
    narration: str
    visual_keyword: str


@dataclass
class VideoScript:
    title: str
    description: str
    tags: list[str]
    thumbnail_text: str
    scenes: list[Scene]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "VideoScript":
        scenes = [Scene(**s) for s in data["scenes"]]
        return cls(
            title=data["title"],
            description=data["description"],
            tags=list(data.get("tags", [])),
            thumbnail_text=data.get("thumbnail_text", data["title"][:8]),
            scenes=scenes,
        )


class ScriptGenerationError(RuntimeError):
    pass


def generate_script(topic: str) -> VideoScript:
    """Generate a VideoScript for the given topic using whichever provider is configured."""
    if settings.anthropic_api_key:
        raw = _generate_with_anthropic(topic)
    elif settings.openai_api_key:
        raw = _generate_with_openai(topic)
    else:
        raise ScriptGenerationError(
            "未設定 ANTHROPIC_API_KEY 或 OPENAI_API_KEY,請於 .env 中至少填寫一個"
        )

    data = _extract_json(raw)
    try:
        return VideoScript.from_dict(data)
    except (KeyError, TypeError) as exc:
        raise ScriptGenerationError(f"LLM 回傳的 JSON 格式不符預期: {exc}\n原始內容: {raw}") from exc


def _generate_with_anthropic(topic: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"主題:{topic}"}],
    )
    return "".join(block.text for block in message.content if block.type == "text")


def _generate_with_openai(topic: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"主題:{topic}"},
        ],
    )
    return completion.choices[0].message.content


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ScriptGenerationError(f"LLM 回傳內容中找不到 JSON: {raw}")
    return json.loads(raw[start : end + 1])
