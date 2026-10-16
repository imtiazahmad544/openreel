"""Shorts repurposer: cut 9:16 vertical Shorts from a finished video.

Blurred-background fill (no ugly stretch), burnt captions re-timed to the
window, original narration reused — zero new AI cost.
"""
from __future__ import annotations

import os
import subprocess

from .captions.builder import CaptionLine, write_ass
from .config import Settings
from .edit.encode import encoder_video_args, find_ffmpeg, select_encoder
from .edit.render import escape_filter_path, has_subtitles_filter


def pick_windows(total: float, count: int = 3, window: float = 30.0) -> list[tuple[float, float]]:
    """Non-overlapping windows at hook (0%), middle, payoff (75%)."""
    if total <= window:
        return [(0.0, total)]
    anchors = [0.0, 0.4, 0.75][:count]
    out, used = [], []
    for a in anchors:
        start = round(a * (total - window), 1)
        if all(abs(start - u) >= window for u in used):
            out.append((start, window))
            used.append(start)
    return out or [(0.0, min(window, total))]


def make_short(source_mp4: str, start: float, duration: float, out_path: str,
               captions: list[CaptionLine] | None = None,
               settings: Settings | None = None,
               speed: str = "fast", encoder: str = "auto") -> str:
    """Render one vertical Short from a window of the source video."""
    settings = settings or Settings()
    ffmpeg = find_ffmpeg()
    enc = select_encoder(ffmpeg, encoder)
    workdir = os.path.dirname(out_path)
    ass_path = None
    if captions and has_subtitles_filter():
        win = [CaptionLine(c.start - start, c.end - start, c.text)
               for c in captions if c.end > start and c.start < start + duration]
        if win:
            ass_path = os.path.join(workdir, "short_captions.ass")
            write_ass(win, ass_path)

    fc = (
        f"[0:v]trim=start={start}:duration={duration},setpts=PTS-STARTPTS,"
        f"split[a][b];"
        f"[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"gblur=sigma=40[bg];"
        f"[b]scale=1080:-2[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
    )
    if ass_path:
        fc += f",subtitles='{escape_filter_path(ass_path)}'"
    fc += ",format=yuv420p[vout];"
    fc += (f"[0:a]atrim=start={start}:duration={duration},asetpts=PTS-STARTPTS,"
           f"aresample=44100[aout]")

    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", source_mp4,
           "-filter_complex", fc, "-map", "[vout]", "-map", "[aout]"]
    cmd += encoder_video_args(enc, speed)
    cmd += ["-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out_path]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError(f"shorts render failed: {proc.stderr[-1500:]}")
    return out_path
