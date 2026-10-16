"""Pipeline orchestrator: script -> scenes -> voice -> visuals -> captions -> MP4."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

from .captions.builder import build_lines, write_ass, write_srt
from .config import Settings
from .edit import assemble_segments, render_video
from .scriptgen import generate_script, split_script
from .visuals import select_visuals
from .voice.base import get_tts_provider


@dataclass
class PipelineResult:
    video_path: str
    srt_path: str
    script_path: str
    manifest_path: str
    duration: float
    scenes: int


def _log(msg: str, cb=None):
    if cb:
        cb(msg)
    else:
        print(msg, flush=True)


def run_pipeline(settings: Settings, out_path: str, *,
                 topic: str | None = None,
                 script_text: str | None = None,
                 script_file: str | None = None,
                 duration_minutes: float = 3.0,
                 style: str = "documentary",
                 visual_mode: str | None = None,
                 filter_preset: str = "cinematic",
                 voice: str | None = None,
                 music_path: str | None = None,
                 render_speed: str = "fast",
                 encoder: str = "auto",
                 progress=None) -> PipelineResult:
    t0 = time.time()
    if voice:
        settings.voice = voice
    workdir = os.path.join(settings.workdir, f"job_{int(t0)}")
    os.makedirs(workdir, exist_ok=True)
    audio_dir = os.path.join(workdir, "audio")
    visual_dir = os.path.join(workdir, "visuals")
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(visual_dir, exist_ok=True)

    # 1. script
    if script_file:
        with open(script_file, encoding="utf-8") as fh:
            script = fh.read()
        _log(f"Loaded script from {script_file} ({len(script.split())} words)", progress)
    elif script_text:
        script = script_text
        _log(f"Using pasted script ({len(script.split())} words)", progress)
    elif topic:
        _log(f"Generating script for topic: {topic!r} (~{duration_minutes} min)...", progress)
        script = generate_script(topic, duration_minutes, settings, style)
    else:
        raise ValueError("need one of: topic, script_text, script_file")
    script_path = os.path.join(workdir, "script.txt")
    with open(script_path, "w", encoding="utf-8") as fh:
        fh.write(script)

    # 2. scenes
    scenes = split_script(script)
    _log(f"Split into {len(scenes)} scenes", progress)

    # 3. voiceover per scene (word timestamps drive captions + timing)
    tts = get_tts_provider(settings)
    voices = []
    for i, scene in enumerate(scenes):
        dest = os.path.join(audio_dir, f"scene_{i:02d}.mp3")
        _log(f"[{i + 1}/{len(scenes)}] voiceover...", progress)
        voices.append(tts.synthesize(scene.text, dest))

    # 4. visuals per scene (stock -> AI -> fallback chain)
    _log("Finding visuals (stock -> AI -> fallback)...", progress)
    visuals = select_visuals(scenes, settings, visual_dir, mode=visual_mode)
    found = sum(1 for v in visuals if v is not None)
    _log(f"Visuals ready: {found}/{len(scenes)} scenes", progress)

    # 5. captions from word timestamps
    caption_groups = [build_lines(v.words) for v in voices]

    # 6. assemble + render
    segments = assemble_segments([s.text for s in scenes], voices, visuals, caption_groups)
    ass_path = os.path.join(workdir, "captions.ass")
    srt_path = os.path.splitext(out_path)[0] + ".srt"
    all_lines = [l for seg in segments for l in seg.captions]
    write_ass(all_lines, ass_path)
    write_srt(all_lines, srt_path)
    _log("Rendering video with ffmpeg (align + cut + captions + filters)...", progress)
    render_video(segments, settings, out_path, ass_path=ass_path,
                 filter_preset=filter_preset, music_path=music_path,
                 speed=render_speed, encoder=encoder)

    duration = segments[-1].end if segments else 0.0
    manifest = {
        "version": 2,
        "topic": topic, "duration_minutes": duration_minutes, "style": style,
        "voice": settings.voice, "aspect": settings.aspect, "fps": settings.fps,
        "filter_preset": filter_preset, "visual_mode": visual_mode,
        "workdir": workdir, "ass_path": ass_path, "srt_path": srt_path,
        "scenes": [{"index": s.index, "text": s.text,
                    "words": [{"text": w.text, "start": w.start, "end": w.end}
                              for w in s.audio.words],
                    "audio_path": s.audio.audio_path,
                    "audio_duration": s.audio.duration,
                    "visual": ({"path": s.visual.path, "kind": s.visual.kind,
                                "source": s.visual.source} if s.visual else None),
                    "start": round(s.start, 2), "end": round(s.end, 2)}
                   for s in segments],
        "output": out_path, "total_seconds": round(duration, 2),
        "elapsed_seconds": round(time.time() - t0, 1),
    }
    manifest_path = os.path.join(workdir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    _log(f"Done in {time.time() - t0:.0f}s -> {out_path} ({duration:.0f}s video)", progress)
    return PipelineResult(video_path=out_path, srt_path=srt_path,
                          script_path=script_path, manifest_path=manifest_path,
                          duration=duration, scenes=len(scenes))
