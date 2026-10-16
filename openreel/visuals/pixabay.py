"""Pixabay video search — free API key (generous free tier)."""
from __future__ import annotations

import os

import requests

from .base import VisualAsset, VisualProvider, download

API_URL = "https://pixabay.com/api/videos/"


class PixabayProvider(VisualProvider):
    name = "pixabay"

    def fetch(self, query: str, dest_dir: str, **kwargs) -> VisualAsset | None:
        key = self.settings.pixabay_api_key
        if not key:
            return None
        try:
            resp = requests.get(
                API_URL,
                params={"key": key, "q": query, "per_page": 5, "video_type": "all"},
                timeout=self.settings.http_timeout,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
            for hit in hits:
                videos = hit.get("videos", {})
                # prefer medium, fall back to large/small
                for quality in ("medium", "large", "small", "tiny"):
                    v = videos.get(quality)
                    if v and v.get("url"):
                        dest = os.path.join(dest_dir, f"pixabay_{hit['id']}.mp4")
                        download(v["url"], dest, timeout=self.settings.http_timeout)
                        return VisualAsset(kind="video", path=dest, source=self.name,
                                           width=v.get("width", 0),
                                           height=v.get("height", 0),
                                           duration=hit.get("duration", 0))
            return None
        except Exception:  # noqa: BLE001 - fall through to next provider
            return None
