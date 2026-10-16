import json
import os

from openreel.config import Settings
from openreel.repair import repair_scene, load_manifest
from openreel.voice.base import VoiceResult, WordBoundary


def _manifest(tmp_path):
    workdir = str(tmp_path / "job")
    os.makedirs(os.path.join(workdir, "audio"))
    os.makedirs(os.path.join(workdir, "visuals"))
    words = [{"text": "hello", "start": 0.0, "end": 1.0},
             {"text": "world", "start": 1.0, "end": 2.0}]
    m = {
        "version": 2, "topic": "t", "voice": "v", "aspect": "16:9", "fps": 30,
        "filter_preset": "none", "visual_mode": "ai",
        "workdir": workdir, "ass_path": os.path.join(workdir, "c.ass"),
        "srt_path": os.path.join(workdir, "c.srt"),
        "output": os.path.join(workdir, "out.mp4"),
        "scenes": [
            {"index": 0, "text": "hello world", "words": words,
             "audio_path": os.path.join(workdir, "audio", "scene_00.mp3"),
             "audio_duration": 2.0,
             "visual": {"path": "/tmp/v0.png", "kind": "image", "source": "x"},
             "start": 0.0, "end": 2.0},
            {"index": 1, "text": "second scene here", "words": words,
             "audio_path": os.path.join(workdir, "audio", "scene_01.mp3"),
             "audio_duration": 2.0,
             "visual": None, "start": 2.0, "end": 4.0},
        ],
    }
    mp = os.path.join(workdir, "manifest.json")
    with open(mp, "w") as fh:
        json.dump(m, fh)
    return mp


def test_repair_scene_revoice(monkeypatch, tmp_path):
    import openreel.repair as rmod

    class FakeTTS:
        def synthesize(self, text, dest):
            wb = [WordBoundary(w, i * 0.5, (i + 1) * 0.5) for i, w in enumerate(text.split())]
            return VoiceResult(dest, wb, len(wb) * 0.5)

    rendered = {}

    def fake_render(segments, settings, out, **kw):
        rendered["n"] = len(segments)
        rendered["starts"] = [s.start for s in segments]
        open(out, "w").write("fake")
        return out

    monkeypatch.setattr(rmod, "get_tts_provider", lambda s: FakeTTS())
    monkeypatch.setattr(rmod, "render_video", fake_render)
    mp = _manifest(tmp_path)
    out = repair_scene(mp, 0, Settings(), new_text="brand new narration here now",
                       progress=lambda m: None)
    assert rendered["n"] == 2
    # scene 0 now 5 words * 0.5 = 2.5s, scene 1 starts at 2.5
    assert rendered["starts"][1] == 2.5
    m2 = load_manifest(mp)
    assert m2["scenes"][0]["text"] == "brand new narration here now"
    assert m2["scenes"][1]["start"] == 2.5  # downstream offsets re-stamped
    assert os.path.exists(out)


def test_repair_scene_out_of_range(tmp_path):
    import pytest
    mp = _manifest(tmp_path)
    with pytest.raises(ValueError):
        repair_scene(mp, 9, Settings())
