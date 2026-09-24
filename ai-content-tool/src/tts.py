"""Text-to-speech narration generation, one audio file per scene.

Provider priority: ElevenLabs (best quality, needs paid API key) -> gTTS
(free, needs internet) -> pyttsx3 (fully offline, robotic but always works).
"""
from __future__ import annotations

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
        final_path = stem_path.with_suffix(".mp3")
        _synthesize_elevenlabs(text, final_path)
    else:
        try:
            final_path = stem_path.with_suffix(".mp3")
            _synthesize_gtts(text, final_path, lang=lang)
        except Exception:
            final_path = stem_path.with_suffix(".wav")
            _synthesize_pyttsx3(text, final_path)

    return NarrationClip(path=final_path, duration_sec=_audio_duration(final_path))


def _synthesize_elevenlabs(text: str, out_path: Path) -> None:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
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


def _audio_duration(path: Path) -> float:
    from moviepy.editor import AudioFileClip

    clip = AudioFileClip(str(path))
    try:
        return float(clip.duration)
    finally:
        clip.close()
