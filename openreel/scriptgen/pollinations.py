"""Pollinations text API — free, no key, no signup (default provider)."""
from __future__ import annotations

import time
import urllib.parse

import requests

from .base import LLMProvider

API_URL = "https://text.pollinations.ai/openai"


class PollinationsProvider(LLMProvider):
    name = "pollinations"

    def complete(self, prompt: str) -> str:
        # Anonymous tier is rate-limited (~1 req / 15s); be polite on 429.
        resp = requests.post(
            API_URL,
            json={
                "model": "openai",
                "messages": [{"role": "user", "content": prompt}],
                "private": True,
            },
            timeout=self.settings.http_timeout,
        )
        if resp.status_code == 429:
            time.sleep(16)
            resp = requests.post(
                API_URL,
                json={"model": "openai",
                      "messages": [{"role": "user", "content": prompt}],
                      "private": True},
                timeout=self.settings.http_timeout,
            )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def quote(s: str) -> str:  # helper kept for tests/docs
        return urllib.parse.quote(s)
