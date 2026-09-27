"""A small library of sound-effect stingers.

With FREESOUND_API_KEY configured, each named effect first tries to fetch
a real matching sound from Freesound.org (cached locally so it's only
downloaded once); otherwise (or if that fails) it falls back to a
synthesized tone built from scratch with ffmpeg - not sampled from any
existing meme audio, since viral clips like "Vine Boom" are copyrighted/
trademarked and not something a script may legally redistribute.
"""
from __future__ import annotations

from pathlib import Path

from . import freesound_client
from .audio_synth import concat, silence, tone
from .config import settings


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

# Search queries tried on Freesound before falling back to synthesis.
SFX_QUERY_MAP = {
    "boom": "impact boom bass hit",
    "ding": "notification ding bell",
    "guitar": "comedic electric guitar sting",
    "phone": "telephone ring",
    "heartbeat": "heartbeat thump",
    "trombone": "sad trombone fail",
    "chime": "cheerful chime bell",
}

_CACHE_DIR = Path(__file__).resolve().parent.parent / "assets" / "sfx_cache"


def build_sfx(name: str, out_path: Path, tmp_dir: Path) -> tuple[Path, dict | None] | None:
    """Build/fetch the named effect to ``out_path``.

    Returns (path, attribution) where attribution is None for the
    synthesized fallback or a CC0 Freesound result (no credit required),
    and a dict for an Attribution-licensed Freesound result. Returns None
    if ``name`` isn't a recognized effect at all.
    """
    if name not in SFX_LIBRARY:
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    if settings.freesound_api_key:
        cached = _CACHE_DIR / f"{name}.mp3"
        if cached.exists():
            return cached, _cached_attribution(name)
        result = freesound_client.search_and_download(
            SFX_QUERY_MAP[name], cached, max_duration=4.0
        )
        if result is not None:
            _save_cached_attribution(name, result)
            attribution = None if freesound_client.is_cc0(result["license"]) else result
            return cached, attribution

    SFX_LIBRARY[name](out_path, tmp_dir)
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
