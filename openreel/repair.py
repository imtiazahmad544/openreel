"""Scene repair: regenerate ONE scene's voice/visual, then rebuild the video.

No full re-run: only the repaired scene's assets are regenerated, everything
else is reused from the manifest. Usage:

    openreel repair .openreel/job_123 --scene 2 --text "New narration..."
    openreel repair .openreel/job_123 --scene 0 --revisualize --visual-mode ai
"""
from __future__ import annotations

import json
import os

from .captions.builder import build_lines, write_ass, write_srt, CaptionLine
from .config import Settings
from .edit import assemble_segments, render_video
from .edit.timeline import Segment
from .visuals.base import VisualAsset
from .visuals.selector import select_visuals
from .scriptgen.splitter import Scene
from .voice.base import get_tts_provider, VoiceResult, WordBoundary


def load_manifest(manifest_path: str) -> dict:
    if os.path.isdir(manifest_path):
        manifest_path = os.path.join(manifest_path, "manifest.json")
    with open(manifest_path, encoding="utf-8") as fh:
        return json.load(fh)


def _scene_to_segment(m: dict, s: dict) -> Segment:
    words = [WordBoundary(w["text"], w["start"], w["end"]) for w in s["words"]]
    voice = VoiceResult(audio_path=s["audio_path"], words=words,
                        duration=s["audio_duration"])
    v = s["visual"]
    visual = VisualAsset(kind=v["kind"], path=v["path"], source=v["source"]) if v else None
    caps = build_lines(words)
    return Segment(index=s["index"], text=s["text"], audio=voice,
                   visual=visual, captions=caps, start=s["start"])


def repair_scene(manifest_path: str, scene_idx: int, settings: Settings,
                 new_text: str | None = None, revisualize: bool = False,
                 visual_mode: str | None = None, progress=None) -> str:
    m = load_manifest(manifest_path)
    scenes = m["scenes"]
    if not 0 <= scene_idx < len(scenes):
        raise ValueError(f"scene {scene_idx} out of range (0..{len(scenes)-1})")
    workdir = m["workdir"]
    s = scenes[scene_idx]
    tts = get_tts_provider(settings)

    if new_text:
        s["text"] = new_text
        dest = os.path.join(workdir, "audio", f"scene_{scene_idx:02d}.mp3")
        if progress: progress(f"Re-synthesizing scene {scene_idx} voiceover...")
        vr = tts.synthesize(new_text, dest)
        s["audio_path"] = vr.audio_path
        s["audio_duration"] = vr.duration
        s["words"] = [{"text": w.text, "start": w.start, "end": w.end} for w in vr.words]

    if revisualize:
        if progress: progress(f"Re-fetching scene {scene_idx} visual...")
        scene_obj = Scene(index=scene_idx, text=s["text"],
                          visual_prompt=s["text"][:200])
        from .scriptgen.splitter import _keywords
        scene_obj.keywords = _keywords(s["text"])
        asset = select_visuals([scene_obj], settings,
                               os.path.join(workdir, "visuals"),
                               mode=visual_mode or m.get("visual_mode"))[0]
        s["visual"] = ({"path": asset.path, "kind": asset.kind, "source": asset.source}
                       if asset else None)

    # rebuild timeline from (possibly updated) manifest
    segments = [_scene_to_segment(m, sc) for sc in scenes]
    # re-stamp absolute offsets (durations may have changed)
    cursor = 0.0
    all_captions: list[CaptionLine] = []
    for seg in segments:
        seg.start = cursor
        seg.captions = [CaptionLine(c.start + cursor, c.end + cursor, c.text)
                        for c in seg.captions]
        all_captions.extend(seg.captions)
        cursor = seg.end
    for seg, sc in zip(segments, scenes):
        sc["start"], sc["end"] = round(seg.start, 2), round(seg.end, 2)

    write_ass(all_captions, m["ass_path"])
    write_srt(all_captions, m["srt_path"])
    if progress: progress("Rebuilding video...")
    out = render_video(segments, settings, m["output"], ass_path=m["ass_path"],
                       filter_preset=m.get("filter_preset", "cinematic"))
    m["total_seconds"] = round(segments[-1].end, 2)
    with open(os.path.join(workdir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=2)
    return out
