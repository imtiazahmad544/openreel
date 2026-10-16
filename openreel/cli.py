"""OpenReel CLI — subcommands.

    openreel create --topic "The Roman Empire" --duration 5 --out video.mp4
    openreel batch topics.txt --out-dir ./videos --resume
    openreel shorts video.mp4 --manifest .openreel/job_1/manifest.json --count 3
    openreel thumbnail --title "I Tried This For 30 Days" --out thumb.jpg
    openreel seo --manifest .openreel/job_1/manifest.json
    openreel publish video.mp4 --title "..." --thumbnail thumb.jpg
    openreel repair .openreel/job_1 --scene 2 --text "New narration..."
    openreel topics --niche "space" --count 10
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from .config import FREE_STACK_NOTES, Settings


def _settings_with(args) -> Settings:
    s = Settings()
    if getattr(args, "aspect", None):
        s.aspect = args.aspect
    return s


# ---------------------------------------------------------------- create
def cmd_create(args):
    from .pipeline import run_pipeline
    settings = _settings_with(args)
    run_pipeline(
        settings, args.out,
        topic=args.topic, script_text=args.script, script_file=args.script_file,
        duration_minutes=args.duration, style=args.style,
        visual_mode=args.visual_mode, filter_preset=args.filter,
        voice=args.voice, music_path=args.music,
        render_speed=args.render_speed, encoder=args.encoder)
    # also drop an SEO pack + thumbnail next to the video (20x: packaging included)
    if args.package:
        _auto_package(settings, args.out)
    return 0


def _auto_package(settings: Settings, video_path: str):
    from .seo import generate_seo_pack, description_with_chapters
    from .thumbnail import make_thumbnail
    from .visuals.pollinations_img import PollinationsImageProvider
    base = os.path.splitext(video_path)[0]
    # find latest manifest for this output
    workdir = settings.workdir
    manifests = []
    if os.path.isdir(workdir):
        for job in os.listdir(workdir):
            mp = os.path.join(workdir, job, "manifest.json")
            if os.path.exists(mp):
                with open(mp) as fh:
                    m = json.load(fh)
                if m.get("output") == video_path:
                    manifests.append((os.path.getmtime(mp), m))
    if not manifests:
        print("packaging skipped: no manifest found")
        return
    m = max(manifests)[1]
    with open(m["script_path"] if "script_path" in m else os.path.join(m["workdir"], "script.txt")) as fh:
        script = fh.read()
    pack = generate_seo_pack(m.get("topic") or "video", script, m["scenes"], settings)
    with open(base + ".seo.json", "w") as fh:
        json.dump({"titles": pack.titles, "description": description_with_chapters(pack),
                   "tags": pack.tags, "hashtags": pack.hashtags,
                   "chapters": pack.chapters, "pinned_comment": pack.pinned_comment},
                  fh, indent=2)
    bg = None
    for sc in m["scenes"]:
        v = sc.get("visual")
        if v and v.get("kind") == "image" and os.path.exists(v["path"]):
            bg = v["path"]
            break
    if bg is None:  # generate one free
        prov = PollinationsImageProvider(settings)
        a = prov.fetch(f"{m.get('topic','video')} dramatic", os.path.dirname(base) or ".",
                       width=1280, height=720)
        bg = a.path if a else None
    make_thumbnail(bg, pack.best_title or m.get("topic", "video"), base + ".thumb.jpg")
    print(f"packaged: {base}.seo.json + {base}.thumb.jpg")


# ---------------------------------------------------------------- batch
def cmd_batch(args):
    from .batch import run_batch
    with open(args.topics_file, encoding="utf-8") as fh:
        topics = [l.strip() for l in fh if l.strip() and not l.startswith("#")]
    run_batch(topics, args.out_dir, _settings_with(args),
              resume=args.resume, duration_minutes=args.duration,
              visual_mode=args.visual_mode, filter_preset=args.filter,
              render_speed=args.render_speed)
    return 0


# ---------------------------------------------------------------- shorts
def cmd_shorts(args):
    from .shorts import pick_windows, make_short
    from .captions.builder import parse_srt
    captions = None
    if args.manifest:
        with open(args.manifest) as fh:
            m = json.load(fh)
        from .captions.builder import CaptionLine
        captions = [CaptionLine(w["start"] + sc["start"], w["end"] + sc["start"], w["text"])
                    for sc in m["scenes"] for w in sc["words"]]
    elif args.srt and os.path.exists(args.srt):
        captions = parse_srt(args.srt)
    total = float(args.total or 0)
    if not total:
        import subprocess
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", args.video],
            capture_output=True, text=True)
        total = float(probe.stdout.strip())
    out_dir = args.out_dir or os.path.dirname(args.video) or "."
    os.makedirs(out_dir, exist_ok=True)
    for i, (start, dur) in enumerate(pick_windows(total, count=args.count, window=args.window)):
        out = os.path.join(out_dir, f"short_{i+1}.mp4")
        print(f"short {i+1}: {start:.0f}s -> {dur:.0f}s")
        make_short(args.video, start, dur, out, captions=captions,
                   speed=args.render_speed)
        print(f"  wrote {out}")
    return 0


# ---------------------------------------------------------------- thumbnail
def cmd_thumbnail(args):
    from .thumbnail import make_thumbnail
    make_thumbnail(args.background, args.title, args.out, style=args.style)
    print(f"wrote {args.out}")
    return 0


# ---------------------------------------------------------------- seo
def cmd_seo(args):
    from .seo import generate_seo_pack, description_with_chapters
    settings = _settings_with(args)
    with open(args.manifest) as fh:
        m = json.load(fh)
    with open(os.path.join(m["workdir"], "script.txt"), encoding="utf-8") as fh:
        script = fh.read()
    pack = generate_seo_pack(m.get("topic") or args.topic or "video", script,
                             m["scenes"], settings)
    doc = {"titles": pack.titles, "description": description_with_chapters(pack),
           "tags": pack.tags, "hashtags": pack.hashtags,
           "chapters": pack.chapters, "pinned_comment": pack.pinned_comment}
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(doc, fh, indent=2)
        print(f"wrote {args.out}")
    else:
        print(json.dumps(doc, indent=2)[:2000])
    return 0


# ---------------------------------------------------------------- publish
def cmd_publish(args):
    from .publish import get_service, upload_video
    service = get_service(args.client_secrets, args.token)
    tags = args.tags.split(",") if args.tags else []
    vid = upload_video(service, args.video, args.title, args.description or "",
                       tags=tags, privacy=args.privacy,
                       thumbnail_path=args.thumbnail)
    print(f"published: https://youtu.be/{vid} (privacy={args.privacy})")
    return 0


# ---------------------------------------------------------------- repair
def cmd_repair(args):
    from .repair import repair_scene
    out = repair_scene(args.manifest, args.scene, _settings_with(args),
                       new_text=args.text, revisualize=args.revisualize,
                       visual_mode=args.visual_mode, progress=print)
    print(f"rebuilt: {out}")
    return 0


# ---------------------------------------------------------------- topics
def cmd_topics(args):
    from .research import ideate_topics
    ideas = ideate_topics(args.niche, args.count, _settings_with(args))
    for i in ideas:
        print(f"[{i.score:3d}] {i.topic}\n      hook: {i.hook}\n      angle: {i.angle}\n")
    if args.out:
        with open(args.out, "w") as fh:
            fh.write("\n".join(i.topic for i in ideas))
        print(f"wrote {args.out}")
    return 0


def cmd_voices(_args):
    import edge_tts

    async def _list():
        for v in await edge_tts.list_voices():
            if v["Locale"].startswith("en"):
                print(f'{v["ShortName"]:45s} {v["Gender"]:8s} {v["Locale"]}')

    asyncio.run(_list())
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="openreel",
                                 description="100% free YouTube automation studio")
    sub = ap.add_subparsers(dest="cmd")

    # create (default)
    c = sub.add_parser("create", help="create one video")
    src = c.add_mutually_exclusive_group(required=True)
    src.add_argument("--topic"); src.add_argument("--script"); src.add_argument("--script-file")
    c.add_argument("--duration", type=float, default=3.0)
    c.add_argument("--style", default="documentary")
    c.add_argument("--out", default="openreel.mp4")
    c.add_argument("--aspect", choices=["16:9", "9:16"], default=None)
    c.add_argument("--visual-mode", choices=["auto", "stock", "ai", "mix"], default=None)
    c.add_argument("--filter", default="cinematic",
                   choices=["cinematic", "vibrant", "warm", "bw", "none"])
    c.add_argument("--voice", default=None)
    c.add_argument("--music", default=None)
    c.add_argument("--render-speed", default="fast", choices=["fast", "balanced", "quality"])
    c.add_argument("--encoder", default="auto",
                   choices=["auto", "nvenc", "qsv", "videotoolbox", "amf", "x264"])
    c.add_argument("--package", action="store_true",
                   help="also generate SEO pack + thumbnail next to the video")
    c.set_defaults(func=cmd_create)

    b = sub.add_parser("batch", help="create many videos with checkpoint resume")
    b.add_argument("topics_file")
    b.add_argument("--out-dir", default="./videos")
    b.add_argument("--resume", action="store_true")
    b.add_argument("--duration", type=float, default=3.0)
    b.add_argument("--visual-mode", choices=["auto", "stock", "ai", "mix"], default=None)
    b.add_argument("--filter", default="cinematic",
                   choices=["cinematic", "vibrant", "warm", "bw", "none"])
    b.add_argument("--render-speed", default="fast", choices=["fast", "balanced", "quality"])
    b.set_defaults(func=cmd_batch)

    s = sub.add_parser("shorts", help="repurpose a video into vertical Shorts")
    s.add_argument("video")
    s.add_argument("--manifest", default=None)
    s.add_argument("--srt", default=None)
    s.add_argument("--total", type=float, default=0)
    s.add_argument("--count", type=int, default=3)
    s.add_argument("--window", type=float, default=30.0)
    s.add_argument("--out-dir", default=None)
    s.add_argument("--render-speed", default="fast", choices=["fast", "balanced", "quality"])
    s.set_defaults(func=cmd_shorts)

    t = sub.add_parser("thumbnail", help="make a click-worthy thumbnail")
    t.add_argument("--title", required=True)
    t.add_argument("--background", default=None)
    t.add_argument("--out", default="thumbnail.jpg")
    t.add_argument("--style", default="shock", choices=["shock", "minimal", "split"])
    t.set_defaults(func=cmd_thumbnail)

    e = sub.add_parser("seo", help="generate SEO pack from a manifest")
    e.add_argument("--manifest", required=True)
    e.add_argument("--topic", default=None)
    e.add_argument("--out", default=None)
    e.set_defaults(func=cmd_seo)

    p = sub.add_parser("publish", help="upload to YouTube (free Data API quota)")
    p.add_argument("video")
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--tags", default="")
    p.add_argument("--thumbnail", default=None)
    p.add_argument("--privacy", default="private",
                   choices=["private", "unlisted", "public"])
    p.add_argument("--client-secrets", default="client_secrets.json")
    p.add_argument("--token", default="token.pickle")
    p.set_defaults(func=cmd_publish)

    r = sub.add_parser("repair", help="regenerate one scene and rebuild")
    r.add_argument("manifest", help="manifest.json or its job dir")
    r.add_argument("--scene", type=int, required=True)
    r.add_argument("--text", default=None)
    r.add_argument("--revisualize", action="store_true")
    r.add_argument("--visual-mode", choices=["auto", "stock", "ai", "mix"], default=None)
    r.set_defaults(func=cmd_repair)

    n = sub.add_parser("topics", help="ideate scored topics for a niche")
    n.add_argument("--niche", required=True)
    n.add_argument("--count", type=int, default=10)
    n.add_argument("--out", default=None)
    n.set_defaults(func=cmd_topics)

    v = sub.add_parser("voices", help="list English edge-tts voices")
    v.set_defaults(func=cmd_voices)

    ap.add_argument("--free-stack", action="store_true")
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    argv = sys.argv[1:] if argv is None else list(argv)
    if "--free-stack" in argv:
        print(FREE_STACK_NOTES)
        return 0
    subs = {"create", "batch", "shorts", "thumbnail", "seo", "publish",
            "repair", "topics", "voices"}
    if not argv or argv[0] not in subs:
        argv = ["create"] + argv  # bare flags keep working like v1
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
