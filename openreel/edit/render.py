"""ffmpeg renderer: Ken Burns, crossfades, caption burn-in, filters, music mix.

Everything is assembled as one filter_complex graph so a scene's video
always matches its narration length exactly (align + sync), stock clips
are cut/looped to fit (cut), and captions/filters apply in a single pass.
"""
from __future__ import annotations

import subprocess

from ..config import Settings
from .encode import encoder_video_args, find_ffmpeg, select_encoder
from .timeline import Segment

FILTER_PRESETS = {
    "none": "",
    "cinematic": "eq=contrast=1.08:saturation=1.18,vignette=PI/4.5",
    "vibrant": "eq=saturation=1.35:contrast=1.05",
    "warm": "colorbalance=rs=0.08:gs=0.03:bs=-0.08,eq=saturation=1.1",
    "bw": "hue=s=0,eq=contrast=1.1",
}

_subtitles_cache: bool | None = None


def has_subtitles_filter() -> bool:
    """True if this ffmpeg build can burn ASS captions (libass)."""
    global _subtitles_cache
    if _subtitles_cache is None:
        try:
            ff = find_ffmpeg()
        except RuntimeError:
            _subtitles_cache = False
            return False
        try:
            out = subprocess.run([ff, "-hide_banner", "-filters"],
                                 capture_output=True, text=True,
                                 timeout=15).stdout
            _subtitles_cache = "subtitles" in out
        except Exception:  # noqa: BLE001
            _subtitles_cache = False
    return bool(_subtitles_cache)


def escape_filter_path(path: str) -> str:
    # the subtitles filter needs : \ ' [ ] , escaped
    return (path.replace("\\", "\\\\").replace(":", "\\:")
                .replace("'", "\\'").replace("[", "\\[").replace("]", "\\]")
                .replace(",", "\\,"))


def build_filtergraph(segments: list[Segment], settings: Settings,
                      ass_path: str | None = None,
                      filter_preset: str = "cinematic",
                      with_music: bool = False) -> tuple[str, float]:
    """Build the filter_complex graph. Pure function — unit testable.

    Segments without a visual use a color source (no ffmpeg input), so
    video input indices are compacted; audio inputs follow all video inputs.
    Returns (filtergraph, total_seconds).
    """
    W, H, fps = settings.width, settings.height, settings.fps
    n = len(segments)
    if n == 0:
        raise ValueError("no segments to render")

    fade = 0.5
    min_dur = min(s.duration for s in segments)
    fade = min(fade, max(min_dur / 3.0, 0.1))

    vinput: list[int | None] = []
    vi = 0
    for seg in segments:
        if seg.visual is None:
            vinput.append(None)
        else:
            vinput.append(vi)
            vi += 1
    ainput = [vi + i for i in range(n)]
    music_idx = vi + n if with_music else None

    parts: list[str] = []
    for i, seg in enumerate(segments):
        dur = seg.duration
        frames = max(int(dur * fps), 2)
        v = seg.visual
        idx = vinput[i]
        if idx is None:
            parts.append(f"color=c=0x101018:s={W}x{H}:r={fps}:d={dur:.3f}[v{i}]")
        elif v is not None and v.kind == "image":
            parts.append(
                f"[{idx}:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},"
                f"zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={fps},"
                f"setpts=PTS-STARTPTS[v{i}]")
        else:  # stock video: cut or loop to the narration length
            parts.append(
                f"[{idx}:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},fps={fps},trim=start=0:end={dur:.3f},"
                f"setpts=PTS-STARTPTS[v{i}]")
        a_in = ainput[i]
        fade_out_start = max(dur - 0.3, 0.05)
        parts.append(
            f"[{a_in}:a]aresample=44100,atrim=start=0:end={dur:.3f},"
            f"asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.15,"
            f"afade=t=out:st={fade_out_start:.3f}:d=0.3[a{i}]")

    # video crossfade chain
    if n == 1:
        vlabel, total = "[v0]", segments[0].duration
    else:
        vlabel, total = "[v0]", segments[0].duration
        for i in range(1, n):
            off = total - fade
            parts.append(f"{vlabel}[v{i}]xfade=transition=fade:"
                         f"duration={fade:.3f}:offset={off:.3f}[x{i}]")
            vlabel = f"[x{i}]"
            total = total + segments[i].duration - fade

    # audio crossfade chain
    if n == 1:
        alabel = "[a0]"
    else:
        alabel = "[a0]"
        for i in range(1, n):
            parts.append(f"{alabel}[a{i}]acrossfade=d={fade:.3f}:c1=tri:c2=tri[ax{i}]")
            alabel = f"[ax{i}]"

    # color filter preset
    preset = FILTER_PRESETS.get(filter_preset, FILTER_PRESETS["cinematic"])
    if preset:
        parts.append(f"{vlabel}{preset}[vf]")
        vlabel = "[vf]"

    # caption burn-in (only if this ffmpeg has libass)
    if ass_path and has_subtitles_filter():
        parts.append(f"{vlabel}subtitles='{escape_filter_path(ass_path)}'[vsub]")
        vlabel = "[vsub]"

    # background music bed
    if with_music and music_idx is not None:
        parts.append(
            f"[{music_idx}:a]aresample=44100,atrim=start=0:end={total:.3f},"
            f"asetpts=PTS-STARTPTS,volume=0.12[mx]")
        parts.append(f"{alabel}[mx]amix=inputs=2:duration=first:"
                     f"dropout_transition=0[aout]")
    else:
        parts.append(f"{alabel}anull[aout]")

    parts.append(f"{vlabel}format=yuv420p[vout]")
    return ";".join(parts), total


def render_video(segments: list[Segment], settings: Settings, output_path: str,
                 ass_path: str | None = None, filter_preset: str = "cinematic",
                 music_path: str | None = None,
                 ffmpeg_bin: str | None = None,
                 speed: str = "fast", encoder: str = "auto") -> str:
    """Run ffmpeg over the assembled timeline. Returns output_path.

    speed: fast (default) | balanced | quality — fast is ~2-3x quicker than
    the old medium default on CPU, more with hardware encoding.
    encoder: auto (default) | nvenc | qsv | videotoolbox | amf | x264.
    """
    ffmpeg_bin = ffmpeg_bin or find_ffmpeg()
    enc = select_encoder(ffmpeg_bin, encoder)

    cmd: list[str] = [ffmpeg_bin, "-y", "-loglevel", "error"]
    for seg in segments:
        v = seg.visual
        if v is None:
            continue  # color source lives in the filtergraph
        if v.kind == "video":
            cmd += ["-stream_loop", "-1", "-i", v.path]
        else:
            cmd += ["-i", v.path]
    for seg in segments:
        cmd += ["-i", seg.audio.audio_path]
    if music_path:
        cmd += ["-i", music_path]

    filtergraph, _total = build_filtergraph(
        segments, settings, ass_path, filter_preset, music_path is not None)
    cmd += ["-filter_complex", filtergraph,
            "-map", "[vout]", "-map", "[aout]"]
    cmd += encoder_video_args(enc, speed)
    cmd += ["-r", str(settings.fps),
            "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", output_path]

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr[-2000:]}")
    return output_path
