"""Fast encoding: auto-select the fastest available H.264 encoder.

Priority: NVIDIA NVENC > Intel QSV > Apple VideoToolbox > AMD AMF > libx264.
With hardware encoders a render is typically 5-10x faster than libx264/medium.
On CPU-only machines the default 'fast' tier (ultrafast) still renders in
under half the time of the old medium default (measured 2.15x on a 2-scene
1080p test); 'balanced'/'quality' trade speed for compression efficiency.

Speed tiers for libx264: fast=ultrafast, balanced=veryfast, quality=medium.
"""
from __future__ import annotations

import shutil
import subprocess

# (encoder name, ffmpeg -encoders tag, extra speed args)
_CANDIDATES = [
    ("nvenc", "h264_nvenc", ["-preset", "p4"]),
    ("qsv", "h264_qsv", ["-preset", "veryfast"]),
    ("videotoolbox", "h264_videotoolbox", []),
    ("amf", "h264_amf", ["-quality", "speed"]),
    ("x264", "libx264", []),
]

_X264_PRESETS = {"fast": "ultrafast", "balanced": "veryfast", "quality": "medium"}

_encoders_cache: str | None = None
_probe_cache: dict[tuple[str, str], bool] = {}


def _ffmpeg_encoders(ffmpeg_bin: str) -> str:
    global _encoders_cache
    if _encoders_cache is None:
        try:
            out = subprocess.run([ffmpeg_bin, "-hide_banner", "-encoders"],
                                 capture_output=True, text=True, timeout=15).stdout
            _encoders_cache = out
        except Exception:  # noqa: BLE001
            _encoders_cache = ""
    return _encoders_cache


def _probe_encoder(ffmpeg_bin: str, tag: str) -> bool:
    """Encode 5 frames of testsrc: proves the encoder actually works here."""
    key = (ffmpeg_bin, tag)
    if key not in _probe_cache:
        try:
            proc = subprocess.run(
                [ffmpeg_bin, "-y", "-loglevel", "error",
                 "-f", "lavfi", "-i", "testsrc=size=160x90:rate=10:duration=0.5",
                 "-c:v", tag, "-f", "null", "-"],
                capture_output=True, timeout=30)
            _probe_cache[key] = proc.returncode == 0
        except Exception:  # noqa: BLE001
            _probe_cache[key] = False
    return _probe_cache[key]


def select_encoder(ffmpeg_bin: str | None = None, preference: str = "auto") -> str:
    """Return the encoder key to use: nvenc|qsv|videotoolbox|amf|x264.

    Auto mode picks the fastest encoder that is both listed AND proven to
    work (a listed-but-driverless nvenc, for example, is skipped).
    """
    preference = (preference or "auto").lower()
    if preference != "auto":
        if preference not in {c[0] for c in _CANDIDATES}:
            raise ValueError(f"unknown encoder '{preference}'")
        return preference
    ffmpeg_bin = ffmpeg_bin or shutil.which("ffmpeg") or "ffmpeg"
    available = _ffmpeg_encoders(ffmpeg_bin)
    for key, tag, _ in _CANDIDATES:
        if tag in available and _probe_encoder(ffmpeg_bin, tag):
            return key
    return "x264"


def encoder_video_args(encoder: str, speed: str = "fast") -> list[str]:
    """Codec + quality args for the chosen encoder and speed tier."""
    if encoder == "x264":
        preset = _X264_PRESETS.get(speed, "veryfast")
        return ["-c:v", "libx264", "-preset", preset, "-crf", "20"]
    if encoder == "nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "21"]
    if encoder == "qsv":
        return ["-c:v", "h264_qsv", "-preset", "veryfast", "-global_quality", "21"]
    if encoder == "videotoolbox":
        # -q:v 100=best .. 0=worst scale is inverted vs x264; ~60 ~= crf 20
        return ["-c:v", "h264_videotoolbox", "-q:v", "60"]
    if encoder == "amf":
        return ["-c:v", "h264_amf", "-quality", "speed", "-qp_i", "23", "-qp_p", "23"]
    raise ValueError(f"unknown encoder '{encoder}'")


def find_ffmpeg() -> str:
    """ffmpeg binary: system PATH first, else the imageio-ffmpeg bundled binary."""
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg  # pip install imageio-ffmpeg (static binary, free)
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    raise RuntimeError(
        "ffmpeg not found. Install it (apt/brew/choco) or run "
        "`pip install imageio-ffmpeg` for a bundled binary.")
