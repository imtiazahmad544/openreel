"""Provider selection + config tests — all offline with fakes."""
import os

from openreel.config import Settings, FREE_STACK_NOTES
from openreel.visuals.selector import select_visuals
from openreel.scriptgen.splitter import Scene
from openreel.visuals.base import VisualAsset


class FakeImage:
    name = "fakeimg"

    def __init__(self, settings):
        self.settings = settings

    def fetch(self, query, dest_dir, **kw):
        return VisualAsset(kind="image", path=os.path.join(dest_dir, "f.jpg"),
                           source="fakeimg")


def _scenes():
    return [Scene(index=0, text="ocean waves deep blue sea", keywords=["ocean", "waves"]),
            Scene(index=1, text="desert dunes hot sand", keywords=["desert", "dunes"])]


def test_selector_ai_mode_uses_image_chain(monkeypatch, tmp_path):
    import openreel.visuals.selector as sel
    monkeypatch.setattr(sel, "PollinationsImageProvider", FakeImage)
    s = Settings()
    assets = sel.select_visuals(_scenes(), s, str(tmp_path), mode="ai")
    assert len(assets) == 2
    assert all(a is not None and a.kind == "image" for a in assets)


def test_selector_stock_without_keys_returns_none(tmp_path):
    s = Settings()  # no PEXELS/PIXABAY keys in test env
    assets = select_visuals(_scenes(), s, str(tmp_path), mode="stock")
    assert assets == [None, None]


def test_selector_auto_falls_back_when_stock_empty(monkeypatch, tmp_path):
    import openreel.visuals.selector as sel
    monkeypatch.setattr(sel, "PollinationsImageProvider", FakeImage)
    s = Settings()
    assets = sel.select_visuals(_scenes(), s, str(tmp_path), mode="auto")
    assert all(a is not None for a in assets)


def test_settings_aspect_dimensions():
    s = Settings()
    assert (s.width, s.height) == (1920, 1080)
    s.aspect = "9:16"
    assert (s.width, s.height) == (1080, 1920)


def test_free_stack_notes_mentions_zero_cost():
    assert "$0" in FREE_STACK_NOTES and "Pollinations" in FREE_STACK_NOTES


def test_pollinations_image_url_shape():
    from openreel.visuals.pollinations_img import PollinationsImageProvider
    import urllib.parse
    q = urllib.parse.quote("a cat")
    url = f"https://image.pollinations.ai/prompt/{q}?width=1280&height=720&seed=1&nologo=true&model=flux"
    assert url.startswith("https://image.pollinations.ai/prompt/")
