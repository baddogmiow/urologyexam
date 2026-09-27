"""Built-in looping background music presets.

With FREESOUND_API_KEY configured, each preset first tries to fetch a
real, loopable CC-licensed track from Freesound.org (cached locally);
otherwise it falls back to a short synthesized melodic loop built from
scratch with ffmpeg - not licensed/sampled music, so there's nothing to
clear rights on. video_builder's existing bgm handling already loops
whatever track is shorter than the video.
"""
from __future__ import annotations

from pathlib import Path

from . import freesound_client
from .audio_synth import concat, silence, tone
from .config import settings

# Note -> frequency (Hz), standard equal temperament.
_NOTE_FREQ = {
    "A2": 110.00, "Bb2": 116.54, "C3": 130.81, "D3": 146.83,
    "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.00,
    "A4": 440.00, "Bb4": 466.16, "C4": 261.63, "C5": 523.25,
}


def _build_upbeat(out_path: Path, tmp_dir: Path) -> Path:
    # Bright ascending/descending major arpeggio - fits the CTA / knowledge-card beat.
    notes = ["C4", "E4", "G4", "C5", "G4", "E4", "C4", "G4"]
    parts = []
    for i, n in enumerate(notes):
        p = tmp_dir / f"upbeat_{i}.wav"
        tone(p, freq=_NOTE_FREQ[n], duration=0.22, decay=2.5, amp=0.4)
        parts.append(p)
    return concat(parts, out_path)


def _build_tense(out_path: Path, tmp_dir: Path) -> Path:
    # Slow low pulsing pair of adjacent notes for a dramatic/suspense feel.
    parts = []
    for i, n in enumerate(["A2", "Bb2", "A2", "C3"]):
        p = tmp_dir / f"tense_{i}.wav"
        tone(p, freq=_NOTE_FREQ[n], duration=0.6, decay=1.2, amp=0.5)
        parts.append(p)
    return concat(parts, out_path)


def _build_quirky(out_path: Path, tmp_dir: Path) -> Path:
    # Playful staccato comedic underscore, with small gaps between notes.
    sequence = ["D4", None, "F4", None, "A4", None, "D4", "F4", None]
    parts = []
    for i, n in enumerate(sequence):
        p = tmp_dir / f"quirky_{i}.wav"
        if n is None:
            silence(p, 0.15)
        else:
            tone(p, freq=_NOTE_FREQ[n], duration=0.15, decay=4, amp=0.45)
        parts.append(p)
    return concat(parts, out_path)


BGM_PRESETS = {
    "upbeat": _build_upbeat,   # 輕快/歡快知識節目 / CTA 收尾
    "tense": _build_tense,     # 緊張懸疑段落
    "quirky": _build_quirky,   # 輕鬆搞笑日常
}

# Search queries tried on Freesound before falling back to synthesis.
BGM_QUERY_MAP = {
    "upbeat": "upbeat happy ukulele loop",
    "tense": "tense suspense drone loop",
    "quirky": "quirky comedy loop",
}

_CACHE_DIR = Path(__file__).resolve().parent.parent / "assets" / "bgm_cache"


def build_bgm_preset(name: str, out_path: Path, tmp_dir: Path) -> tuple[Path, dict | None] | None:
    """Build/fetch the named background loop to ``out_path``.

    Returns (path, attribution), where attribution is None for the
    synthesized fallback or a CC0 Freesound result (no credit required),
    and a dict for an Attribution-licensed Freesound result. Returns None
    if ``name`` isn't a recognized preset at all.
    """
    if name not in BGM_PRESETS:
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    if settings.freesound_api_key:
        cached = _CACHE_DIR / f"{name}.mp3"
        if cached.exists():
            return cached, _cached_attribution(name)
        result = freesound_client.search_and_download(
            BGM_QUERY_MAP[name], cached, min_duration=8.0, max_duration=60.0
        )
        if result is not None:
            _save_cached_attribution(name, result)
            attribution = None if freesound_client.is_cc0(result["license"]) else result
            return cached, attribution

    BGM_PRESETS[name](out_path, tmp_dir)
    return out_path, None


def _attribution_cache_file(name: str) -> Path:
    return _CACHE_DIR / f"{name}.attribution.json"


def _cached_attribution(name: str) -> dict | None:
    import json

    f = _attribution_cache_file(name)
    if not f.exists():
        return None
    data = json.loads(f.read_text(encoding="utf-8"))
    return None if freesound_client.is_cc0(data["license"]) else data


def _save_cached_attribution(name: str, result: dict) -> None:
    import json

    _attribution_cache_file(name).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
