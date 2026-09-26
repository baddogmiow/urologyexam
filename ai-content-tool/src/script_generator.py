"""Turn a topic into a structured, scene-by-scene video script using an LLM."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict

from .config import settings

_LENGTH_PROFILES = {
    "shorts": {
        "duration_desc": "60-90 秒",
        "scene_count": "6 到 9",
        "narration_desc": "一到兩句話,精簡但要有實際資訊,不是空話",
        "depth_rule": (
            "如果主題適合具體舉例(例如 3C 產品、軟體工具、地點、方法),"
            "至少挑 2 個具體款式/品牌/類別例子帶過並簡短比較差異,"
            "不用每個面向都展開,但不能只講抽象原則。"
        ),
        "structure_rule": "安排一個場景做簡短優缺點比較,結尾場景給一句明確的行動建議。",
    },
    "long": {
        "duration_desc": "2-4 分鐘",
        "scene_count": "8 到 14",
        "narration_desc": "三到五句話,資訊量要夠",
        "depth_rule": (
            "要點名 2-4 個具體款式/品牌/型號或方案作為例子並比較差異"
            "(例如列出不同預算/使用情境各推薦哪一款),而不是只講抽象的選購原則。"
        ),
        "structure_rule": (
            "至少安排一個場景比較不同選項的優缺點,一個場景給出依不同需求/預算的具體建議,"
            "結尾場景給出明確的行動建議(例如去哪裡比較、注意什麼)。"
        ),
    },
}


_JSON_SCHEMA_BLOCK = """只能輸出一個 JSON 物件,格式如下,不要有任何 JSON 以外的文字:

{{
  "title": "吸引點擊但不誇大不實的標題(繁體中文,30字以內)",
  "description": "影片描述,含2-3個重點{description_extra}",
  "tags": ["關鍵字1", "關鍵字2", "..."],
  "thumbnail_text": "縮圖上要放的短文字(8字以內,吸睛但不腥羶色)",
  "thumbnail_visual_keyword": "用來搜尋縮圖背景照片的英文關鍵字,要能代表整支影片主題",
  "scenes": [
    {{"narration": "這一幕的旁白逐字稿(繁體中文,{narration_desc})", "visual_keyword": "用來找背景圖/影片素材的英文關鍵字", "speaker": "說這句話的角色標籤,例如「旁白」「醫師」「病人」,同一支影片裡角色名稱要一致"}}
  ]
}}"""

_COMMON_SAFETY_RULES = """- title 和 description 不要出現具體的分鐘數宣稱(例如「3分鐘搞懂」),因為實際影片長度會因配音語速設定而變動,寫死的分鐘數容易跟實際不符。
- narration 禁止使用任何無法查證的誇大醫療/財務/法律承諾。
- 不得包含色情、暴力、仇恨、詐騙、抄襲他人受版權保護的原文字句。"""


def _build_explainer_prompt(profile: dict) -> str:
    schema = _JSON_SCHEMA_BLOCK.format(
        description_extra="與一句免責聲明(內容由AI輔助生成僅供參考)",
        narration_desc=profile["narration_desc"],
    )
    return f"""你是資深短影音腳本編劇與該主題的領域研究員。收到一個主題後,產出一支 {profile["duration_desc"]}、內容有實質深度的說明/科普/開箱比較類影片腳本(不是空泛的懶人包)。
{schema}

內容深度規則(重要):
- scenes 陣列要有 {profile["scene_count"]} 個場景,合起來旁白總長度抓 {profile["duration_desc"]} 口語速度。
- {profile["depth_rule"]}
- 具體型號、規格、價格帶用「類別代表例子」的方式呈現(例如「像 XX 系列、YY 系列這類主打輕薄的機型」),並提醒「實際規格與價格請以官網公告與購買當下為準」,避免給出可能已過期的精確報價或型號規格當作保證。
- {profile["structure_rule"]}

其他規則:
{_COMMON_SAFETY_RULES}
- 若主題涉及專業領域(醫療、法律、財務等),於 description 附上「僅供參考,非專業建議」字樣。
"""


def _build_story_prompt(profile: dict) -> str:
    schema = _JSON_SCHEMA_BLOCK.format(
        description_extra="",
        narration_desc=profile["narration_desc"] + ",第一人稱、口語、有畫面感",
    )
    return f"""你是短影音喜劇/生活觀察系編劇,專門寫醫療從業人員生活的輕鬆敘事短片(像 vlog 說故事,不是知識類影片)。收到一個主題後,產出一支 {profile["duration_desc"]} 的第一人稱敘事短片腳本。
{schema}

病人隱私與去識別化規則(最高優先,不可違反):
- 絕對不能描述任何可能被辨識出的真實病人、真實同事、真實醫院/科別名稱,或任何具體病歷/病情細節組合;所有情境一律要「複合虛構化」,設計成很多住院醫師/醫療從業人員都可能遇到的通用共通經驗,不能是某一次特定事件的紀實描述。
- 不得透露任何可能構成病人隱私的資訊(姓名、病歷號、可辨識的病情細節、日期地點等)。如果原始主題描述中暗示了具體真人真事,一律改寫成通用化、去識別化的情境,絕不照實還原細節。
- 情節中如果涉及其他醫護人員或主治,一律用去識別化的通稱(例如「值班主治」「學長姐」),不得使用任何可能對應到真實特定人物的稱呼或描述。

敘事風格規則:
- scenes 陣列要有 {profile["scene_count"]} 個場景,合起來旁白總長度抓 {profile["duration_desc"]} 口語速度。
- 結構採「鋪陳 -> 事情發展/反差 -> 高潮或抖包袱 -> 收尾感想/金句」,語氣輕鬆自嘲、有畫面感,靠反差或意外製造笑點與同行共鳴,不需要說教或給建議。
- 如果劇情有對白(例如兩人對話),每個場景的 speaker 要標成說話的那個角色(例如「旁白」「醫師」「病人」),同一部影片裡同一個角色的 speaker 名稱要完全一致,才能讓配音套用一致的音調。
- visual_keyword 用能配合情境氛圍的通用英文關鍵字(例如 hospital hallway night, tired doctor coffee, nurses station busy),不要包含任何可能對應到真實醫院招牌、真實人物的關鍵字。

其他規則:
{_COMMON_SAFETY_RULES}
"""


def _build_system_prompt() -> str:
    profile = _LENGTH_PROFILES.get(settings.script_length, _LENGTH_PROFILES["shorts"])
    if settings.script_style == "story":
        return _build_story_prompt(profile)
    return _build_explainer_prompt(profile)


@dataclass
class Scene:
    narration: str
    visual_keyword: str
    speaker: str = "narrator"


def _parse_scene(s: dict) -> Scene:
    """Build a Scene from one LLM-generated scene dict.

    The LLM occasionally typos the "narration" key itself (e.g. "narician"),
    not just adds an extra one, so a plain s["narration"] lookup isn't
    reliable. Fall back to whatever other string field is present.
    """
    visual_keyword = s.get("visual_keyword", "")
    speaker = s.get("speaker") or "narrator"
    narration = s.get("narration")
    if narration is None:
        candidates = [
            v for k, v in s.items() if k not in ("visual_keyword", "speaker") and isinstance(v, str)
        ]
        if not candidates:
            raise ScriptGenerationError(f"場景資料缺少旁白文字: {s}")
        narration = candidates[0]
    return Scene(narration=narration, visual_keyword=visual_keyword, speaker=speaker)


@dataclass
class VideoScript:
    title: str
    description: str
    tags: list[str]
    thumbnail_text: str
    thumbnail_visual_keyword: str
    scenes: list[Scene]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "VideoScript":
        scenes = [_parse_scene(s) for s in data["scenes"]]
        thumbnail_keyword = data.get("thumbnail_visual_keyword") or (
            scenes[0].visual_keyword if scenes else ""
        )
        return cls(
            title=data["title"],
            description=data["description"],
            tags=list(data.get("tags", [])),
            thumbnail_text=data.get("thumbnail_text", data["title"][:8]),
            thumbnail_visual_keyword=thumbnail_keyword,
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
        max_tokens=4000,
        system=_build_system_prompt(),
        messages=[{"role": "user", "content": f"主題:{topic}"}],
    )
    return "".join(block.text for block in message.content if block.type == "text")


def _generate_with_openai(topic: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=4000,
        messages=[
            {"role": "system", "content": _build_system_prompt()},
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
