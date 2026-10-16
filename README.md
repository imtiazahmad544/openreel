# 🎬 OpenReel 2.1 — 100% Free YouTube Automation Studio

**Topic in, published video out — for $0.** OpenReel is a complete YouTube
automation system: it researches topics, writes duration-sized scripts, creates
AI visuals, finds stock clips, generates neural voiceover, edits everything
(Ken Burns, crossfades, captions, color filters, sync), then packages each video
with SEO metadata, a click-worthy thumbnail, vertical Shorts, and one-command
YouTube upload.

Most automation agents in this space route every stage through paid APIs
(GPT-4, Midjourney/Kling-class image/video, ElevenLabs). OpenReel's entire
pipeline runs on **free tiers, open-source models, and generous free quotas**.
No credit card. Ever.

## What 2.0 adds over a plain video generator

| Capability | How OpenReel does it ($0) |
|---|---|
| Topic research | `topics` — LLM brainstorms niche ideas, scores them 0–100 |
| Script | duration-aware (~150 wpm), or paste/upload your own `.txt` |
| Voiceover | edge-tts neural voices, **word-level timestamps** drive captions |
| Visuals | Pexels/Pixabay stock (free keys) → Pollinations AI images (no key) → Wikimedia → fallback |
| Edit | single ffmpeg pass: align, cut/loop, xfade, burnt captions, filters |
| SEO pack | 3 titles, description + chapters from real scene timings, tags, hashtags, pinned comment |
| Thumbnail | AI/stock background + bold overlay text, 3 styles |
| Shorts | auto-cut 9:16 Shorts (blurred fill, re-timed captions), zero new AI cost |
| Batch | `batch` — N topics → N videos with JSON checkpoints, `--resume` after crashes |
| Scene repair | `repair` — fix one scene's narration/visual, rebuild without re-running |
| Publish | `publish` — YouTube Data API upload (free quota) + thumbnail set |
| UI | Gradio: Create / SEO / Thumbnail / Shorts tabs |
| Cloud | Colab notebook — free runtime, nothing to install but ffmpeg |

## Quickstart

**Easiest: double-click to launch.** `launch.bat` (Windows) or `launch.sh`
(Linux/macOS) — or `python launcher.py`. The launcher checks everything,
installs missing pieces (including ffmpeg itself if you don't have it), and
opens the UI in your browser. No command line needed.

```bash
pip install -r requirements.txt
# ffmpeg required: apt install ffmpeg / brew install ffmpeg / choco install ffmpeg
# (or skip it — the launcher installs a bundled ffmpeg automatically)

# Full video from a topic, with SEO pack + thumbnail
python -m openreel.cli create --topic "How octopuses escape any tank" \
    --duration 3 --out video.mp4 --package

# Your script as a vertical Short
python -m openreel.cli create --script-file myscript.txt --aspect 9:16 --out short.mp4

# Overnight batch: 10 topics, resumable
python -m openreel.cli topics --niche "space" --count 10 --out topics.txt
python -m openreel.cli batch topics.txt --out-dir ./videos --resume

# Repurpose into Shorts / fix a scene / publish
python -m openreel.cli shorts video.mp4 --manifest .openreel/job_1/manifest.json --count 3
python -m openreel.cli repair .openreel/job_1 --scene 2 --text "Better narration here."
python -m openreel.cli publish video.mp4 --title "Why Octopuses Escape" \
    --thumbnail video.thumb.jpg --privacy unlisted
```

Web UI: `pip install gradio && python app.py` → http://127.0.0.1:7860

## Render speed

Rendering auto-selects the fastest working H.264 encoder on your machine:
NVIDIA NVENC → Intel QuickSync → Apple VideoToolbox → AMD AMF → CPU x264.
Hardware encoding is typically 5–10x faster; on CPU-only machines the default
`fast` tier still renders in **under half the time** of the old default
(measured 2.15x on a 2-scene 1080p test: 27.1s → 12.6s, identical duration and
burnt captions). Tiers: `fast` (ultrafast, default) / `balanced` (veryfast) /
`quality` (medium) — via `--render-speed` or the UI. Force a specific encoder
with `--encoder nvenc|qsv|videotoolbox|amf|x264`.

## The $0 stack

| Stage | Default (free, no key) | Optional free upgrades |
|---|---|---|
| Script / SEO / topics | Pollinations text API — free, no signup | Gemini free tier, Ollama (local) |
| Images / thumbnails | Pollinations image API (FLUX-class) — free | — |
| Voice | edge-tts — free, no key, word timestamps | Piper TTS (fully offline) |
| Stock clips | Wikimedia Commons (no key) | Pexels + Pixabay free API keys |
| Captions | from TTS word timestamps | — |
| Editing / Shorts | ffmpeg | — |
| Publishing | YouTube Data API v3 (free quota; OAuth once) | — |

Anonymous Pollinations use is rate-limited (~1 req / 15 s) — the pipeline waits
politely. edge-tts needs a direct connection (some corporate proxies block its
websocket; Colab/Kaggle are fine, Piper is the offline fallback).

## Google Colab / Kaggle (free runtime)

```python
!apt-get update -qq && apt-get install -y -qq ffmpeg
!unzip -q -o openreel-2.1.zip -d /content
%cd /content/openreel
!pip install -q -r requirements.txt
!python -m openreel.cli create --topic "Why the moon is drifting away" --duration 2 --out /content/video.mp4
!python -m openreel.cli shorts /content/video.mp4 --count 3 --out-dir /content/shorts
```
(`notebooks/openreel_colab.ipynb` has the same flow ready to run.)

## CLI reference

```
create    --topic|--script|--script-file  --duration --style --out --aspect
          --visual-mode auto|stock|ai|mix  --filter cinematic|vibrant|warm|bw|none
          --voice  --music  --package
          --render-speed fast|balanced|quality  --encoder auto|nvenc|qsv|videotoolbox|amf|x264
batch     topics.txt --out-dir --resume --duration
shorts    video.mp4 --manifest|--srt --count --window --out-dir
thumbnail --title --background --out --style shock|minimal|split
seo       --manifest --topic --out
publish   video.mp4 --title --description --tags --thumbnail
          --privacy private|unlisted|public
repair    manifest.json --scene N --text --revisualize --visual-mode
topics    --niche --count --out
voices    list English TTS voices
```

## Project layout

```
openreel/
  scriptgen/   LLM providers (pollinations/gemini/ollama/echo) + duration splitter
  visuals/     pollinations / pexels / pixabay / wikimedia + selector
  voice/       edge-tts (word timestamps) + piper offline fallback
  captions/    word timestamps <-> SRT / styled ASS
  edit/        timeline + ffmpeg renderer (Ken Burns, xfade, filters)
  seo.py       titles / description / tags / chapters / pinned comment
  thumbnail.py PIL thumbnail composer
  shorts.py    9:16 repurposer
  research.py  topic ideation + scoring
  batch.py     checkpointed batch runner
  repair.py    single-scene repair + rebuild
  publish.py   YouTube Data API uploader
  pipeline.py  orchestrator    cli.py  subcommand CLI
app.py                 Gradio UI (Create / SEO / Thumbnail / Shorts)
notebooks/             Colab notebook
tests/                 49 pytest tests (offline, fakes)
```

## Honest limits

- AI visuals are generated per scene — great for explainers, not for footage
  that must show specific real people/places (use `--visual-mode stock` then).
- Pollinations is a shared free service; heavy batch use should stay polite
  (delays are built in) or bring your own model.
- edge-tts is unofficial (mirrors Edge Read Aloud); Microsoft could throttle it
  — Piper exists for exactly that reason.
- YouTube publishing needs a free Google Cloud OAuth client (one-time setup);
  uploads consume the free 10k-units/day quota (~6 uploads/day per unit math —
  plenty for automation).

## Contributing

PRs welcome — especially new **free** providers (TTS, image, stock, music).
House rule: if it needs a credit card, it stays optional.

## License

MIT — free for personal and commercial use. If OpenReel helps you start your
channel, a shout-out is appreciated but never required.
