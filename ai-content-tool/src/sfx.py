"""A small library of synthesized sound-effect stingers.

These are generated from scratch with ffmpeg's audio synthesis (sine tones
with an exponential decay envelope), not sampled from any existing meme
audio - viral clips like "Vine Boom" are copyrighted/trademarked and not
something a script may legally redistribute, so this gives comparable
comedic stingers without that risk.
"""
from __future__ import annotations

from pathlib import Path

from .audio_synth import concat, silence, tone


def _build_boom(out_path: Path, tmp_dir: Path) -> Path:
    tone(out_path, freq=75, duration=0.5, decay=9, amp=0.95)
    return out_path


def _build_ding(out_path: Path, tmp_dir: Path) -> Path:
    tone(out_path, freq=1300, duration=0.45, decay=5, amp=0.6)
    return out_path


def _build_guitar(out_path: Path, tmp_dir: Path) -> Path:
    tone(out_path, freq=1400, duration=0.35, decay=6, amp=0.7)
    return out_path


def _build_phone(out_path: Path, tmp_dir: Path) -> Path:
    on1, off1, on2 = tmp_dir / "phone_on1.wav", tmp_dir / "phone_off1.wav", tmp_dir / "phone_on2.wav"
    tone(on1, freq=440, duration=0.35, decay=0.3, amp=0.5)
    silence(off1, 0.25)
    tone(on2, freq=440, duration=0.35, decay=0.3, amp=0.5)
    return concat([on1, off1, on2], out_path)


def _build_heartbeat(out_path: Path, tmp_dir: Path) -> Path:
    lub, gap1 = tmp_dir / "hb_lub.wav", tmp_dir / "hb_gap1.wav"
    dub, gap2 = tmp_dir / "hb_dub.wav", tmp_dir / "hb_gap2.wav"
    tone(lub, freq=60, duration=0.18, decay=14, amp=0.9)
    silence(gap1, 0.15)
    tone(dub, freq=55, duration=0.18, decay=14, amp=0.8)
    silence(gap2, 0.5)
    return concat([lub, gap1, dub, gap2], out_path)


def _build_trombone(out_path: Path, tmp_dir: Path) -> Path:
    parts = []
    for i, f in enumerate([300, 260, 220, 180]):
        p = tmp_dir / f"trom_{i}.wav"
        tone(p, freq=f, duration=0.22, decay=3, amp=0.55)
        parts.append(p)
    return concat(parts, out_path)


def _build_chime(out_path: Path, tmp_dir: Path) -> Path:
    a, b = tmp_dir / "chime_a.wav", tmp_dir / "chime_b.wav"
    tone(a, freq=880, duration=0.25, decay=5, amp=0.6)
    tone(b, freq=1320, duration=0.35, decay=4, amp=0.6)
    return concat([a, b], out_path)


SFX_LIBRARY = {
    "boom": _build_boom,          # 剎車/重擊/Vine Boom 類的替代
    "ding": _build_ding,          # 單一清脆提示音
    "guitar": _build_guitar,      # 電吉他尖叫 / "What?!" 類的替代
    "phone": _build_phone,        # 電話鈴聲
    "heartbeat": _build_heartbeat,  # 心跳聲
    "trombone": _build_trombone,  # 烏鴉叫/綜藝尷尬音效 類的替代 (下降音階)
    "chime": _build_chime,        # 叮!訂閱音效
}


def build_sfx(name: str, out_path: Path, tmp_dir: Path) -> Path | None:
    """Build the named effect to ``out_path``, or return None if unknown."""
    builder = SFX_LIBRARY.get(name)
    if builder is None:
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return builder(out_path, tmp_dir)
