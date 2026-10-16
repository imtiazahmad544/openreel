"""Pexels video search — free API key (generous free tier)."""
from __future__ import annotations

import os

import requests

from .base import VisualAsset, VisualProvider, download

API_URL = "https://api.pexels.com/videos/search"


class PexelsProvider(VisualProvider):
    name = "pexels"

    def fetch(self, query: str, dest_dir: str, orientation: str = "landscape",
              **kwargs) -> VisualAsset | None:
        key = self.settings.pexels_api_key
        if not key:
            return None
        try:
            resp = requests.get(
                API_URL,
                headers={"Authorization": key},
                params={"query": query, "per_page": 5, "orientation": orientation,
                        "size": "medium"},
                timeout=self.settings.http_timeout,
            )
            resp.raise_for_status()
            videos = resp.json().get("videos", [])
            if not videos:
                return None
            # Pick the smallest file that is at least 720p to keep downloads light.
            best = None
            for video in videos:
                for f in video.get("video_files", []):
                    if f.get("height", 0) >= 700 and f.get("link"):
                        if best is None or f["height"] < best["height"]:
                            best = f
                if best:
                    break
            if not best:
                return None
            dest = os.path.join(dest_dir, f"pexels_{videos[0]['id']}.mp4")
            download(best["link"], dest, timeout=self.settings.http_timeout)
            return VisualAsset(kind="video", path=dest, source=self.name,
                               width=best.get("width", 0), height=best.get("height", 0),
                               duration=videos[0].get("duration", 0))
        except Exception:  # noqa: BLE001 - fall through to next provider
            return None
