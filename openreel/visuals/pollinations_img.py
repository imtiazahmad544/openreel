"""Pollinations image API — free, no key (FLUX-class models)."""
from __future__ import annotations

import os
import random
import urllib.parse

from .base import VisualAsset, VisualProvider, download


class PollinationsImageProvider(VisualProvider):
    name = "pollinations"

    def fetch(self, query: str, dest_dir: str, width: int = 1280,
              height: int = 720, seed: int | None = None, **kwargs) -> VisualAsset | None:
        seed = seed if seed is not None else random.randint(0, 999999)
        prompt = urllib.parse.quote(query[:400])
        url = (f"https://image.pollinations.ai/prompt/{prompt}"
               f"?width={width}&height={height}&seed={seed}&nologo=true&model=flux")
        dest = os.path.join(dest_dir, f"ai_{seed}.jpg")
        try:
            download(url, dest, timeout=self.settings.http_timeout,
                     retries=self.settings.retries)
        except RuntimeError:
            return None
        return VisualAsset(kind="image", path=dest, source=self.name,
                           width=width, height=height)
