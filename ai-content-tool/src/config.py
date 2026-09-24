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

    youtube_client_secret_file: str = field(
        default_factory=lambda: os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")
    )
    youtube_default_privacy: str = field(
        default_factory=lambda: os.getenv("YOUTUBE_DEFAULT_PRIVACY", "private")
    )

    trends_region: str = field(default_factory=lambda: os.getenv("TRENDS_REGION", "TW"))

    pexels_api_key: str = field(default_factory=lambda: os.getenv("PEXELS_API_KEY", ""))

    output_dir: Path = ROOT_DIR / "output"

    def has_script_provider(self) -> bool:
        return bool(self.anthropic_api_key or self.openai_api_key)


settings = Settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)
