"""Central configuration loaded from environment variables / .env file."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


@dataclass
class Settings:
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))

    elevenlabs_api_key: str = field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY", ""))
    elevenlabs_voice_id: str = field(default_factory=lambda: os.getenv("ELEVENLABS_VOICE_ID", ""))
    # Optional per-speaker voice override, e.g. "旁白:id1,病人:id2"; falls back
    # to elevenlabs_voice_id for any speaker not listed here.
    elevenlabs_voice_map: dict[str, str] = field(
        default_factory=lambda: dict(
            pair.split(":", 1)
            for pair in os.getenv("ELEVENLABS_VOICE_MAP", "").split(",")
            if ":" in pair
        )
    )
    tts_speed: float = field(default_factory=lambda: float(os.getenv("TTS_SPEED", "1.3")))

    youtube_client_secret_file: str = field(
        default_factory=lambda: os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")
    )
    youtube_default_privacy: str = field(
        default_factory=lambda: os.getenv("YOUTUBE_DEFAULT_PRIVACY", "private")
    )

    trends_region: str = field(default_factory=lambda: os.getenv("TRENDS_REGION", "TW"))

    # "shorts" (60-90s, vertical) or "long" (2-4min, deeper dive)
    script_length: str = field(default_factory=lambda: os.getenv("SCRIPT_LENGTH", "shorts"))
    # "explainer" (科普/開箱/比較) or "story" (第一人稱敘事/生活趣事,去識別化)
    script_style: str = field(default_factory=lambda: os.getenv("SCRIPT_STYLE", "explainer"))

    pexels_api_key: str = field(default_factory=lambda: os.getenv("PEXELS_API_KEY", ""))

    freesound_api_key: str = field(default_factory=lambda: os.getenv("FREESOUND_API_KEY", ""))
    # How loud the background music track is mixed relative to narration
    # (0.0-1.0). Narration audio itself is not scaled.
    bgm_volume: float = field(default_factory=lambda: float(os.getenv("BGM_VOLUME", "0.35")))

    output_dir: Path = ROOT_DIR / "output"

    def has_script_provider(self) -> bool:
        return bool(self.anthropic_api_key or self.openai_api_key)


settings = Settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)
