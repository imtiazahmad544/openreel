"""Wikimedia Commons — keyless fallback for stills (CC-licensed)."""
from __future__ import annotations

import os

import requests

from .base import VisualAsset, VisualProvider, download

API_URL = "https://commons.wikimedia.org/w/api.php"


class WikimediaProvider(VisualProvider):
    name = "wikimedia"

    def fetch(self, query: str, dest_dir: str, width: int = 1280, **kwargs) -> VisualAsset | None:
        try:
            resp = requests.get(
                API_URL,
                params={
                    "action": "query", "format": "json",
                    "generator": "search", "gsrsearch": query,
                    "gsrnamespace": 6, "gsrlimit": 5,
                    "prop": "imageinfo", "iiprop": "url|size",
                    "iiurlwidth": width,
                },
                timeout=self.settings.http_timeout,
            )
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {}).values()
            for page in pages:
                info = (page.get("imageinfo") or [{}])[0]
                url = info.get("thumburl") or info.get("url")
                if url and not url.lower().endswith(".svg"):
                    dest = os.path.join(dest_dir, f"wiki_{page['pageid']}.jpg")
                    download(url, dest, timeout=self.settings.http_timeout)
                    return VisualAsset(kind="image", path=dest, source=self.name,
                                       width=info.get("thumbwidth", 0),
                                       height=info.get("thumbheight", 0))
            return None
        except Exception:  # noqa: BLE001
            return None
