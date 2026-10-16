"""Ollama — fully local, free forever (needs `ollama serve` running)."""
from __future__ import annotations

import requests

from .base import LLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"

    def complete(self, prompt: str) -> str:
        resp = requests.post(
            f"{self.settings.ollama_host}/api/generate",
            json={"model": self.settings.ollama_model, "prompt": prompt, "stream": False},
            timeout=self.settings.http_timeout * 5,
        )
        resp.raise_for_status()
        return resp.json()["response"]
