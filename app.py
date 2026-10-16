"""OpenReel web UI (Gradio). Run:  pip install gradio  &&  python app.py"""
from __future__ import annotations

import json
import os
import tempfile

from dotenv import load_dotenv

load_dotenv()

from openreel.config import Settings
from openreel.pipeline import run_pipeline

CURATED_VOICES = [
    "en-US-AndrewMultilingualNeural",
    "en-US-AvaMultilingualNeural",
    "en-US-EmmaMultilingualNeural",
    "en-US-ChristopherNeural",
    "en-GB-ThomasNeural",
    "en-GB-SoniaNeural",
]


def build_video(mode, topic, duration, style, script_text, script_file,
                aspect, visual_mode, filter_preset, voice, package, render_speed):
    settings = Settings()
    settings.aspect = aspect
    out = os.path.join(tempfile.mkdtemp(), "openreel.mp4")
    logs: list[str] = []
    cb = logs.append
    kwargs = dict(duration_minutes=duration, style=style, visual_mode=visual_mode,
                  filter_preset=filter_preset, voice=voice, progress=cb,
                  render_speed=render_speed)
    if mode == "Topic -> AI script":
        result = run_pipeline(settings, out, topic=topic, **kwargs)
    elif mode == "Paste script":
        result = run_pipeline(settings, out, script_text=script_text, **kwargs)
    else:
        path = script_file.name if hasattr(script_file, "name") else script_file
        result = run_pipeline(settings, out, script_file=path, **kwargs)
    extra = []
    if package:
        from openreel.cli import _auto_package
        _auto_package(settings, out)
        base = os.path.splitext(out)[0]
        extra = [base + ".seo.json", base + ".thumb.jpg"]
    return out, result.srt_path, "\n".join(logs), extra


def make_seo(topic, script_text):
    from openreel.seo import generate_seo_pack, description_with_chapters
    settings = Settings()
    pack = generate_seo_pack(topic, script_text, [], settings)
    return (json.dumps({"titles": pack.titles,
                        "description": description_with_chapters(pack),
                        "tags": pack.tags, "hashtags": pack.hashtags,
                        "pinned_comment": pack.pinned_comment}, indent=2),
            pack.best_title)


def make_thumb(title, bg_file, style):
    from openreel.thumbnail import make_thumbnail
    bg = bg_file.name if hasattr(bg_file, "name") else bg_file
    out = os.path.join(tempfile.mkdtemp(), "thumb.jpg")
    return make_thumbnail(bg, title, out, style=style)


def make_shorts(video_file, count):
    from openreel.shorts import pick_windows, make_short
    src = video_file.name if hasattr(video_file, "name") else video_file
    import subprocess
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", src],
        capture_output=True, text=True)
    total = float(probe.stdout.strip())
    outdir = tempfile.mkdtemp()
    outs = []
    for i, (st, du) in enumerate(pick_windows(total, count=int(count), window=30.0)):
        o = os.path.join(outdir, f"short_{i+1}.mp4")
        make_short(src, st, du, o)
        outs.append(o)
    return outs


def ui():
    import gradio as gr

    with gr.Blocks(title="OpenReel 2.0 — free YouTube automation studio") as demo:
        gr.Markdown("# 🎬 OpenReel 2.0\n**100% free** YouTube automation: script → "
                    "voice → visuals → edit → SEO → thumbnails → Shorts → publish.")
        with gr.Tab("Create video"):
            with gr.Row():
                mode = gr.Radio(["Topic -> AI script", "Paste script", "Upload .txt script"],
                                value="Topic -> AI script", label="Input mode")
                aspect = gr.Radio(["16:9", "9:16"], value="16:9", label="Aspect")
            topic = gr.Textbox(label="Topic", placeholder="e.g. How black holes evaporate")
            duration = gr.Slider(0.5, 15, value=3, step=0.5, label="Target duration (minutes)")
            style = gr.Dropdown(["documentary", "storytelling", "motivational",
                                 "educational", "mysterious"], value="documentary")
            script_text = gr.Textbox(label="Your script (paste mode)", lines=8, visible=False)
            script_file = gr.File(label="Upload .txt (upload mode)", file_types=[".txt"],
                                  visible=False)
            mode.change(lambda m: (gr.update(visible=m == "Paste script"),
                                   gr.update(visible=m == "Upload .txt script"),
                                   gr.update(visible=m == "Topic -> AI script")),
                        mode, [script_text, script_file, topic])
            with gr.Row():
                visual_mode = gr.Radio(["auto", "stock", "ai", "mix"], value="auto",
                                       label="Visuals")
                filter_preset = gr.Radio(["cinematic", "vibrant", "warm", "bw", "none"],
                                         value="cinematic", label="Color filter")
                voice = gr.Dropdown(CURATED_VOICES, value=CURATED_VOICES[0], label="Voice")
            package = gr.Checkbox(label="Also generate SEO pack + thumbnail", value=True)
            render_speed = gr.Radio(["fast", "balanced", "quality"], value="fast",
                                    label="Render speed (fast = under half the time)")
            btn = gr.Button("🎥 Create video", variant="primary")
            log = gr.Textbox(label="Progress", lines=8)
            video = gr.Video(label="Result")
            srt = gr.File(label="Captions (.srt)")
            extras = gr.Files(label="SEO + thumbnail")
            btn.click(build_video,
                      [mode, topic, duration, style, script_text, script_file,
                       aspect, visual_mode, filter_preset, voice, package, render_speed],
                      [video, srt, log, extras])

        with gr.Tab("SEO pack"):
            t2 = gr.Textbox(label="Topic")
            s2 = gr.Textbox(label="Script (or excerpt)", lines=8)
            b2 = gr.Button("Generate SEO pack")
            o2 = gr.Code(label="titles / description / tags / chapters", language="json")
            b2.click(make_seo, [t2, s2], [o2, t2])

        with gr.Tab("Thumbnail"):
            tt = gr.Textbox(label="Thumbnail title", placeholder="I TRIED THIS FOR 30 DAYS")
            tb = gr.File(label="Background image (optional)")
            ts = gr.Radio(["shock", "minimal", "split"], value="shock", label="Style")
            bt = gr.Button("Make thumbnail")
            ot = gr.Image(label="Thumbnail")
            bt.click(make_thumb, [tt, tb, ts], ot)

        with gr.Tab("Shorts"):
            sv = gr.File(label="Finished video (.mp4)")
            sc = gr.Slider(1, 5, value=3, step=1, label="Number of Shorts")
            bs = gr.Button("Cut Shorts")
            os_ = gr.Files(label="Vertical Shorts")
            bs.click(make_shorts, [sv, sc], os_)
    return demo


if __name__ == "__main__":
    ui().launch(server_name="0.0.0.0", share=False)
