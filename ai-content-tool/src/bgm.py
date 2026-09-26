"""Built-in, fully-synthesized looping background music beds.

Same reasoning as sfx.py: original sine-tone synthesis, not sampled or
licensed music, so there's no copyright/licensing question to sort out.
Each preset renders a short melodic loop; video_builder's existing bgm
handling already loops whatever track is shorter than the video.
"""
from __future__ import annotations

from pathlib import Path

from .audio_synth import concat, silence, tone

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
    "upbeat": _build_upbeat,   # 歡快知識節目 / CTA 收尾
    "tense": _build_tense,     # 緊張懸疑段落
    "quirky": _build_quirky,   # 輕鬆搞笑日常
}


def build_bgm_preset(name: str, out_path: Path, tmp_dir: Path) -> Path | None:
    """Build the named background loop to ``out_path``, or None if unknown."""
    builder = BGM_PRESETS.get(name)
    if builder is None:
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return builder(out_path, tmp_dir)
