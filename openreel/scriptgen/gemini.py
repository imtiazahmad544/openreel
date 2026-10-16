"""Google Gemini free tier (needs free API key from Google AI Studio)."""
from __future__ import annotations

import requests

from .base import LLMProvider

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


class GeminiProvider(LLMProvider):
    name = "gemini"

    def complete(self, prompt: str) -> str:
        if not self.settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        resp = requests.post(
            API_URL,
            params={"key": self.settings.gemini_api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=self.settings.http_timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
