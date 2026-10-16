"""Visual selection strategy with graceful fallbacks.

Modes:
  auto  - stock video (Pexels -> Pixabay) if keys exist, else AI image, else Wikimedia
  stock - only stock video providers (needs at least one key)
  ai    - only Pollinations AI images (always free, no key)
  mix   - alternate: stock video on even scenes, AI image on odd scenes
"""
from __future__ import annotations

import os

from ..config import Settings
from ..scriptgen.splitter import Scene
from .base import VisualAsset
from .pexels import PexelsProvider
from .pixabay import PixabayProvider
from .pollinations_img import PollinationsImageProvider
from .wikimedia import WikimediaProvider


def _stock_chain(settings: Settings):
    return [PexelsProvider(settings), PixabayProvider(settings)]


def _image_chain(settings: Settings):
    return [PollinationsImageProvider(settings), WikimediaProvider(settings)]


def _try_chain(chain, query: str, dest_dir: str, **kw) -> VisualAsset | None:
    for provider in chain:
        asset = provider.fetch(query, dest_dir, **kw)
        if asset is not None:
            return asset
    return None


def select_visuals(scenes: list[Scene], settings: Settings, dest_dir: str,
                   mode: str | None = None) -> list[VisualAsset | None]:
    mode = (mode or settings.visual_mode).lower()
    os.makedirs(dest_dir, exist_ok=True)
    orientation = "portrait" if settings.aspect == "9:16" else "landscape"
    width, height = settings.width, settings.height

    assets: list[VisualAsset | None] = []
    for i, scene in enumerate(scenes):
        query = " ".join(scene.keywords) or scene.text[:60]
        kw = {"orientation": orientation, "width": width, "height": height}
        asset: VisualAsset | None = None
        if mode == "stock":
            asset = _try_chain(_stock_chain(settings), query, dest_dir, **kw)
        elif mode == "ai":
            asset = _try_chain(_image_chain(settings), query, dest_dir, **kw)
        elif mode == "mix":
            chain = _stock_chain(settings) if i % 2 == 0 else _image_chain(settings)
            asset = _try_chain(chain, query, dest_dir, **kw) or \
                _try_chain(_image_chain(settings), query, dest_dir, **kw)
        else:  # auto
            asset = _try_chain(_stock_chain(settings), query, dest_dir, **kw)
            if asset is None:
                asset = _try_chain(_image_chain(settings), query, dest_dir, **kw)
        assets.append(asset)
    return assets
