"""Shared low-level audio synthesis primitives, used by both sfx.py
(short stingers) and bgm.py (looping background music beds). Everything
is generated from scratch via ffmpeg's sine-tone synthesis - no sampled
or copyrighted audio.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

SR = 44100

# moviepy's AudioFileClip reader errors when reading right at the boundary
# of a very short clip (observed failing around 0.08s); floor every
# generated segment above that so concat() never trips over it.
_MIN_SEGMENT_DURATION = 0.12


def tone(out_path: Path, freq: float, duration: float, decay: float, amp: float = 0.8) -> None:
    duration = max(duration, _MIN_SEGMENT_DURATION)
    expr = f"{amp}*sin(2*PI*{freq}*t)*exp(-{decay}*t)"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"aevalsrc={expr}:s={SR}:d={duration}", str(out_path)],
        check=True,
        capture_output=True,
    )


def silence(out_path: Path, duration: float) -> None:
    duration = max(duration, _MIN_SEGMENT_DURATION)
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono",
            "-t", str(duration), str(out_path),
        ],
        check=True,
        capture_output=True,
    )


def concat(parts: list[Path], out_path: Path) -> Path:
    from moviepy import AudioFileClip, concatenate_audioclips

    clips = [AudioFileClip(str(p)) for p in parts]
    final = concatenate_audioclips(clips)
    final.write_audiofile(str(out_path), fps=SR, logger=None)
    for c in clips:
        c.close()
    final.close()
    return out_path
