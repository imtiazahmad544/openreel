"""Visual asset model + provider interface."""
from __future__ import annotations

import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass

from ..config import Settings


@dataclass
class VisualAsset:
    kind: str            # "image" | "video"
    path: str            # local file path (downloaded)
    source: str          # provider name, e.g. "pollinations", "pexels"
    width: int = 0
    height: int = 0
    duration: float = 0  # seconds (video only)


class VisualProvider:
    name = "base"

    def __init__(self, settings: Settings):
        self.settings = settings

    def fetch(self, query: str, dest_dir: str, **kwargs) -> VisualAsset | None:  # pragma: no cover
        raise NotImplementedError


def download(url: str, dest_path: str, timeout: int = 60, retries: int = 3) -> str:
    """Download a URL to dest_path with retries. Returns dest_path."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OpenReel/0.1"})
            with urllib.request.urlopen(req, timeout=timeout) as resp, \
                    open(dest_path, "wb") as fh:
                fh.write(resp.read())
            if os.path.getsize(dest_path) == 0:
                raise IOError("empty download")
            return dest_path
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"download failed: {url}") from last


def slug(query: str) -> str:
    return urllib.parse.quote_plus(query[:60])
