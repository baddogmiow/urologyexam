"""Text-to-speech narration generation, one audio file per scene.

Provider priority: ElevenLabs (best quality, needs paid API key) -> gTTS
(free, needs internet) -> pyttsx3 (fully offline, robotic but always works).
"""
from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

import requests

from .config import settings


@dataclass
class NarrationClip:
    path: Path
    duration_sec: float


def synthesize_scene(
    text: str,
    out_path: Path,
    lang: str = "zh-TW",
    speaker: str = "narrator",
    pitch_map: dict[str, int] | None = None,
) -> NarrationClip:
    """Synthesize ``text`` to speech. ``out_path`` should have no suffix or
    an .mp3 suffix; the actual file written may end in .wav instead when the
    offline pyttsx3 fallback is used, and the real path is returned.

    ``speaker`` lets a multi-role script (narrator/doctor/patient, ...) sound
    like different voices: with ElevenLabs configured via ELEVENLABS_VOICE_MAP,
    each speaker gets its own real voice; otherwise the single gTTS/pyttsx3
    voice is pitch-shifted per speaker as a free approximation. Pass
    ``pitch_map`` (from ``assign_speaker_pitches``) so distinct speakers in
    the same script never collide on the same pitch by hash coincidence.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stem_path = out_path.with_suffix("")

    if settings.elevenlabs_api_key and settings.elevenlabs_voice_id:
        # ElevenLabs supports native speed control (sounds far more natural
        # than post-hoc time-stretching), so skip the ffmpeg atempo pass.
        final_path = stem_path.with_suffix(".mp3")
        voice_id = settings.elevenlabs_voice_map.get(speaker, settings.elevenlabs_voice_id)
        _synthesize_elevenlabs(text, final_path, voice_id=voice_id)
    else:
        try:
            final_path = stem_path.with_suffix(".mp3")
            _synthesize_gtts(text, final_path, lang=lang)
        except Exception:
            final_path = stem_path.with_suffix(".wav")
            _synthesize_pyttsx3(text, final_path)

        if settings.tts_speed != 1.0:
            final_path = _apply_speed(final_path, settings.tts_speed)

        pitch = (
            pitch_map.get(speaker, 0)
            if pitch_map is not None
            else _pitch_semitones_for_speaker(speaker)
        )
        if pitch != 0:
            final_path = _apply_pitch_shift(final_path, pitch)

    return NarrationClip(path=final_path, duration_sec=_audio_duration(final_path))


_KNOWN_SPEAKER_PITCH = {
    "narrator": 0,
    "旁白": 0,
}
_PITCH_POOL = [-5, 4, -3, 6, -7, 2, 8, -9, 9, -2]  # semitones


def _pitch_semitones_for_speaker(speaker: str) -> int:
    """Legacy per-label lookup (kept for callers that don't pass a
    pitch_map). Two different speakers CAN collide on the same pitch here
    since each label is hashed independently - prefer assign_speaker_pitches
    when you have the full scene list up front.
    """
    if speaker in _KNOWN_SPEAKER_PITCH:
        return _KNOWN_SPEAKER_PITCH[speaker]
    digest = hashlib.md5(speaker.encode("utf-8")).hexdigest()
    return _PITCH_POOL[int(digest, 16) % len(_PITCH_POOL)]


def assign_speaker_pitches(speakers: list[str]) -> dict[str, int]:
    """Assign each distinct speaker (in first-appearance order) a unique
    pitch offset, so two different characters never sound identical by
    hash coincidence. narrator/旁白 always keep 0 (unshifted).
    """
    mapping: dict[str, int] = {}
    available = list(_PITCH_POOL)
    for s in speakers:
        if s in mapping:
            continue
        if s in _KNOWN_SPEAKER_PITCH:
            mapping[s] = _KNOWN_SPEAKER_PITCH[s]
            continue
        digest = hashlib.md5(s.encode("utf-8")).hexdigest()
        if available:
            idx = int(digest, 16) % len(available)
            mapping[s] = available.pop(idx)
        else:
            # More distinct characters than pool slots (unlikely for a short
            # skit) - fall back to a possible collision rather than erroring.
            mapping[s] = _PITCH_POOL[int(digest, 16) % len(_PITCH_POOL)]
    return mapping


def _synthesize_elevenlabs(text: str, out_path: Path, voice_id: str) -> None:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
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


def _get_sample_rate(path: Path) -> int:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=sample_rate",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip())


def _apply_pitch_shift(path: Path, semitones: int) -> Path:
    """Shift pitch by ``semitones`` while keeping duration the same, via the
    classic asetrate+atempo trick (works with any ffmpeg build, no extra
    filters required). Used as a free stand-in for distinct character voices
    when only a single TTS voice (gTTS/pyttsx3) is available.
    """
    ratio = 2 ** (semitones / 12)
    input_rate = _get_sample_rate(path)
    pitched_path = path.with_name(f"{path.stem}_pitched{path.suffix}")
    filter_str = f"asetrate={input_rate * ratio},aresample={input_rate},atempo={1 / ratio}"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(path), "-filter:a", filter_str, str(pitched_path)],
        check=True,
        capture_output=True,
    )
    path.unlink()
    pitched_path.rename(path)
    return path


def _audio_duration(path: Path) -> float:
    from moviepy import AudioFileClip

    clip = AudioFileClip(str(path))
    try:
        return float(clip.duration)
    finally:
        clip.close()
