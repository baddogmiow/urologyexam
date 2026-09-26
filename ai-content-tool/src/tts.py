"""Text-to-speech narration generation, one audio file per scene.

Provider priority: ElevenLabs (best quality, needs paid API key) -> gTTS
(free, needs internet) -> pyttsx3 (fully offline, robotic but always works).
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import requests

from .config import settings


@dataclass
class NarrationClip:
    path: Path
    duration_sec: float


def synthesize_scene(text: str, out_path: Path, lang: str = "zh-TW") -> NarrationClip:
    """Synthesize ``text`` to speech. ``out_path`` should have no suffix or
    an .mp3 suffix; the actual file written may end in .wav instead when the
    offline pyttsx3 fallback is used, and the real path is returned.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stem_path = out_path.with_suffix("")

    if settings.elevenlabs_api_key and settings.elevenlabs_voice_id:
        # ElevenLabs supports native speed control (sounds far more natural
        # than post-hoc time-stretching), so skip the ffmpeg atempo pass.
        final_path = stem_path.with_suffix(".mp3")
        _synthesize_elevenlabs(text, final_path)
    else:
        try:
            final_path = stem_path.with_suffix(".mp3")
            _synthesize_gtts(text, final_path, lang=lang)
        except Exception:
            final_path = stem_path.with_suffix(".wav")
            _synthesize_pyttsx3(text, final_path)

        if settings.tts_speed != 1.0:
            final_path = _apply_speed(final_path, settings.tts_speed)

    return NarrationClip(path=final_path, duration_sec=_audio_duration(final_path))


def _synthesize_elevenlabs(text: str, out_path: Path) -> None:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    # ElevenLabs' own "speed" control accepts 0.7-1.2; clamp our (wider)
    # TTS_SPEED range into it rather than rejecting an out-of-range value.
    elevenlabs_speed = max(0.7, min(1.2, settings.tts_speed))
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "speed": elevenlabs_speed,
        },
    }
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    out_path.write_bytes(response.content)


def _synthesize_gtts(text: str, out_path: Path, lang: str) -> None:
    from gtts import gTTS

    # gTTS uses ISO 639-1 codes; zh-TW maps to zh-TW in its supported set,
    # but fall back to plain "zh" if that ever stops being accepted.
    try:
        gTTS(text=text, lang=lang).save(str(out_path))
    except ValueError:
        gTTS(text=text, lang="zh").save(str(out_path))


def _synthesize_pyttsx3(text: str, out_path: Path) -> None:
    import pyttsx3

    engine = pyttsx3.init()
    engine.save_to_file(text, str(out_path))
    engine.runAndWait()


def _apply_speed(path: Path, speed: float) -> Path:
    """Speed up (or slow down) narration audio without shifting its pitch,
    via ffmpeg's atempo filter. Valid single-filter range is 0.5-2.0, which
    comfortably covers normal narration speed-up use cases.
    """
    sped_path = path.with_name(f"{path.stem}_sped{path.suffix}")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(path), "-filter:a", f"atempo={speed}", str(sped_path)],
        check=True,
        capture_output=True,
    )
    path.unlink()
    sped_path.rename(path)
    return path


def _audio_duration(path: Path) -> float:
    from moviepy import AudioFileClip

    clip = AudioFileClip(str(path))
    try:
        return float(clip.duration)
    finally:
        clip.close()
