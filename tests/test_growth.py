import json
import os

from openreel.config import Settings
from openreel.seo import generate_seo_pack, description_with_chapters, _chapters_from_scenes
from openreel.research import ideate_topics
from openreel.shorts import pick_windows
from openreel.thumbnail import make_thumbnail


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload

    def complete_retry(self, prompt):
        return self.payload


SEO_JSON = json.dumps({
    "titles": ["Why The Moon Is Leaving Us", "The Moon Is Drifting Away", "Moon Mystery"],
    "description": "Para one.\n\nPara two.",
    "tags": ["moon", "space"],
    "hashtags": ["#space", "#moon"],
    "pinned_comment": "Did you know the moon drifts 3.8cm a year?",
})

TOPICS_JSON = json.dumps([
    {"topic": "Black holes", "hook": "What if you fell in?", "angle": "survivor POV", "score": 92},
    {"topic": "Quantum cats", "hook": "Dead and alive?", "angle": "myth busting", "score": 71},
])


def _scenes():
    return [{"index": 0, "start": 0, "text": "the quick brown fox jumps high",
             "words": []},
            {"index": 1, "start": 65, "text": "lazy dogs sleep under warm stars",
             "words": []}]


def test_chapters_from_scenes():
    ch = _chapters_from_scenes(_scenes())
    assert ch[0] == ("00:00", "the quick brown fox jumps high")
    assert ch[1] == ("01:05", "lazy dogs sleep under warm stars")


def test_generate_seo_pack_parses(monkeypatch):
    import openreel.seo as seo_mod
    monkeypatch.setattr(seo_mod, "get_provider", lambda s: FakeLLM(SEO_JSON))
    pack = generate_seo_pack("moon", "script text here", _scenes(), Settings())
    assert pack.best_title == "Why The Moon Is Leaving Us"
    assert len(pack.titles) == 3
    assert pack.chapters[1][0] == "01:05"
    full = description_with_chapters(pack)
    assert "Chapters:" in full and "#space" in full


def test_generate_seo_pack_bad_json(monkeypatch):
    import openreel.seo as seo_mod
    monkeypatch.setattr(seo_mod, "get_provider", lambda s: FakeLLM("not json at all"))
    pack = generate_seo_pack("moon", "script", [], Settings())
    assert pack.titles == [] and pack.description == ""


def test_ideate_topics_sorted(monkeypatch):
    import openreel.research as rmod
    monkeypatch.setattr(rmod, "get_provider", lambda s: FakeLLM(TOPICS_JSON))
    ideas = ideate_topics("space", 2, Settings())
    assert [i.score for i in ideas] == [92, 71]
    assert ideas[0].topic == "Black holes"


def test_pick_windows_short_video():
    assert pick_windows(20.0) == [(0.0, 20.0)]


def test_pick_windows_three():
    wins = pick_windows(120.0, count=3, window=30.0)
    assert len(wins) == 3
    assert wins[0][0] == 0.0
    # non-overlapping
    for (s1, d1), (s2, d2) in zip(wins, wins[1:]):
        assert s2 >= s1 + d1


def test_make_thumbnail_no_background(tmp_path):
    out = str(tmp_path / "t.jpg")
    make_thumbnail(None, "I tried this for 30 days", out, style="shock")
    from PIL import Image
    img = Image.open(out)
    assert img.size == (1280, 720)


def test_make_thumbnail_styles(tmp_path):
    from PIL import Image
    for style in ("shock", "minimal", "split"):
        out = str(tmp_path / f"{style}.jpg")
        make_thumbnail(None, "Test title here", out, style=style)
        assert Image.open(out).size == (1280, 720)
